"""
The live auction engine — v3.

Features:
  - Compact auction card image (regenerated on resends, not every bid)
  - Separate bid announcement messages (kept)
  - Ephemeral bid confirmation
  - Auction card RESENT on every 3rd bid + going once + going twice
  - Going once at 10s, going twice at 5s
  - Anti-snipe extends timer
  - Admin nomination is ephemeral
  - Admin-only SKIP button → force NOT SOLD / UNSOLD (no waiting on the timer)
  - Custom emoji support for SOLD + bid buttons (config.py)
"""

import asyncio
from datetime import datetime, timedelta, timezone

import discord

from config import Config, is_admin
import economy as E
import players as P
import auction_card as AC
import emojis as EM
from embed_colors import C
import cards as Cards


ACTIVE: dict = {}
OFFERED: dict = {}


def is_running(guild_id: int) -> bool:
    a = ACTIVE.get(guild_id)
    return a is not None and a.status == "OPEN"


def offered_keys(guild_id: int) -> set:
    return OFFERED.get(guild_id, set())


class AuctionView(discord.ui.View):
    def __init__(self, auction: "Auction"):
        super().__init__(timeout=None)
        self.auction = auction
        self.refresh_buttons()

    def refresh_buttons(self):
        a = self.auction
        nxt = a.next_min_bid()
        inc = nxt - a.current_bid
        self.min_bid.label = f"Bid £{nxt // 1_000_000}M"
        self.quick_bid.label = f"+£{max(5_000_000, inc) // 1_000_000}M"

    @discord.ui.button(label="Bid", style=discord.ButtonStyle.primary, row=0)
    async def min_bid(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.auction.handle_bid(interaction, self.auction.next_min_bid())

    @discord.ui.button(label="Bid +5M", style=discord.ButtonStyle.success, row=0)
    async def quick_bid(self, interaction: discord.Interaction, button: discord.ui.Button):
        inc = self.auction.next_min_bid() - self.auction.current_bid
        await self.auction.handle_bid(
            interaction, self.auction.current_bid + max(5_000_000, inc)
        )

    # Custom bid button intentionally removed — managers were jumping prices
    # with typed amounts and others hit Bid/+ without noticing the new floor.

    @discord.ui.button(label="Skip (Admin)", style=discord.ButtonStyle.danger, row=1)
    async def skip_auction(self, interaction: discord.Interaction, button: discord.ui.Button):
        """
        Admin-only: end the auction immediately as NOT SOLD / UNSOLD.
        Player goes to the unsold list (re-auctionable via /phase UNSOLD).
        No money is taken (bids only settle on a real sale).
        """
        if not is_admin(interaction.user.id):
            await interaction.response.send_message(
                f"{EM.e('x')} Admins only.", ephemeral=True
            )
            return
        if self.auction.status != "OPEN":
            await interaction.response.send_message(
                "This auction is already over.", ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)
        await self.auction.skip(skipped_by=interaction.user)
        await interaction.followup.send(
            f"{EM.e('check')} Skipped **{self.auction.player['name']}** → UNSOLD.",
            ephemeral=True,
        )


class Auction:
    def __init__(self, guild_id, channel, player, started_by, test_mode: bool = False,
                 fast_mode: bool = False, blitz_mode: bool = False):
        self.guild_id = guild_id
        self.channel = channel
        self.player = player
        self.started_by = started_by
        # Test auctions: full UI/bidding, but NO money, squad, history, queue, or card progress
        self.test_mode = bool(test_mode)
        self.fast_mode = bool(fast_mode)
        self.blitz_mode = bool(blitz_mode)

        # Blitz: everyone starts at 5M. Fast: non-icons at 10M, icons at 25M. Normal: default.
        if self.blitz_mode:
            self.start_price = 5_000_000
        elif self.fast_mode and not P.is_icon(player):
            self.start_price = 10_000_000
        elif self.fast_mode and P.is_icon(player):
            self.start_price = 25_000_000
        else:
            self.start_price = P.start_price(player["ovr"], is_icon=P.is_icon(player))

        self.current_bid = self.start_price
        self.highest_bidder = None
        self.bids = 0

        # Fast/Blitz: 30 second timer. Normal: 60.
        duration = 30 if (self.fast_mode or self.blitz_mode) else Config.AUCTION_DURATION
        self.end_time = datetime.now(timezone.utc) + timedelta(seconds=duration)
        self.status = "OPEN"
        self.message = None
        self.view = AuctionView(self)
        self._task = None
        self._lock = asyncio.Lock()

        self._announced_once = False
        self._announced_twice = False
        self._bids_since_last_card = 0

    def next_min_bid(self):
        inc = max(
            Config.MIN_BID_INCREMENT_FLAT,
            round(self.current_bid * Config.MIN_BID_INCREMENT_PCT / 1_000_000) * 1_000_000,
        )
        return self.current_bid + inc

    def _validate_bid(self, member, amount):
        if self.status != "OPEN":
            return False, "Auction ended."
        nxt = self.next_min_bid()
        if amount < nxt:
            return False, f"Too low! Min bid is **£{nxt:,}**."
        if self.highest_bidder and member.id == self.highest_bidder.id:
            return False, "You're already the highest bidder."
        if not E.can_afford(self.guild_id, member.id, amount):
            bal = E.get_balance(self.guild_id, member.id)
            return False, f"Can't afford that. Balance: **£{bal:,}**."

        # Max squad size cap (15 players)
        MAX_SQUAD_SIZE = 15
        current_size = E.squad_count(self.guild_id, member.id)
        if current_size >= MAX_SQUAD_SIZE:
            return False, (
                f"Your squad is full (**{MAX_SQUAD_SIZE}/15**). "
                f"You can't buy more players. Use `/dump` or `/trade` to make room."
            )

        # Squad-needs max bid - now position-aware
        try:
            player_group = self.player.get("group", "")
            bid_info = E.auction_max_bid(self.guild_id, member.id, player_group=player_group)
            cap = int(bid_info["cap"])
            floor = int(bid_info["floor"])
            if amount > cap:
                if bid_info.get("total_needed", 0) > 0:
                    pos_note = ""
                    if bid_info.get("position_needed"):
                        pos_note = " You're bidding on a position you need."
                    elif bid_info.get("position_needed") is False:
                        pos_note = " You already have enough of this position."
                    return False, (
                        f"Max bid **{E.money(cap)}** "
                        f"({E.money(floor)} reserve + £10M buffer). "
                        f"Still need **{bid_info['total_needed']}** slot(s).{pos_note}"
                    )
                return False, (
                    f"Max bid **{E.money(cap)}** "
                    f"(budget reserve + £10M buffer). Check `/needs`."
                )
        except Exception as ex:
            print(f"[!] auction_max_bid check failed: {ex}")

        # Season + management card + restriction rules
        ok, err = Cards.can_bid(self.guild_id, member.id, self.player, amount)
        if not ok:
            return False, err
        return True, ""

    async def handle_bid(self, interaction, amount):
        # Track whether they already had a management card (for late-join notice)
        had_card = False
        day = Cards.get_open_day(self.guild_id, "management")
        if day:
            had_card = Cards.get_assignment(day["id"], interaction.user.id) is not None

        ok, err = self._validate_bid(interaction.user, amount)
        if not ok:
            await interaction.response.send_message(err, ephemeral=True)
            return

        # After can_bid, late arrivals may have been auto-assigned
        late_assign = None
        if day and not had_card:
            late_assign = Cards.get_assignment(day["id"], interaction.user.id)

        was_leading = self.highest_bidder
        prev_bid = self.current_bid

        self.current_bid = amount
        self.highest_bidder = interaction.user
        self.bids += 1
        self._bids_since_last_card += 1

        # Anti-snipe
        now = datetime.now(timezone.utc)
        extended = False
        if (self.end_time - now) < timedelta(seconds=Config.ANTI_SNIPE_WINDOW):
            self.end_time = now + timedelta(seconds=Config.ANTI_SNIPE_EXTEND)
            self._announced_once = False
            self._announced_twice = False
            extended = True

        self.view.refresh_buttons()

        # 1) Ephemeral confirmation to bidder
        conf = f"Bid placed: **£{amount:,}** on {self.player['name']}"
        if late_assign:
            conf += f"\n\n**Management card assigned:** {late_assign['card_text']}"
        await interaction.response.send_message(conf, ephemeral=True)

        # 2) Public bid announcement message
        p = self.player
        msg = f"**{interaction.user.mention}** bids **£{amount:,}** on **{p['name']}**!"
        if extended:
            msg += "\n**ANTI-SNIPE!** Timer extended!"
        if was_leading and was_leading.id != interaction.user.id:
            msg += f"\n_(overtakes {was_leading.mention} who bid £{prev_bid:,})_"
        if late_assign:
            msg += (
                f"\n{EM.e('clipboard') or '📋'} **Late join** — "
                f"{interaction.user.mention} just got a management card."
            )
        try:
            await self.channel.send(msg)
        except discord.HTTPException:
            pass

        # DM late card privately
        if late_assign:
            try:
                await interaction.user.send(
                    f"**Management card (auto-assigned on bid)**\n"
                    f"{late_assign['card_text']}"
                )
            except Exception:
                pass

        # 3) EDIT the auction card message (update image in place)
        await self._edit_card()

        # 4) Resend auction card on every 3rd bid
        if self._bids_since_last_card >= 3:
            self._bids_since_last_card = 0
            await self._resend_card()

    async def start(self):
        await self._send_card(is_initial=True)
        self._task = asyncio.create_task(self._loop())
        ACTIVE[self.guild_id] = self
        # Don't mark test players as offered — queue / pool stay clean
        if not self.test_mode:
            OFFERED.setdefault(self.guild_id, set()).add(self.player["key"])

    async def skip(self, skipped_by=None):
        """
        Admin force-end: treat as NOT SOLD / UNSOLD immediately.
        Safe to call only while status == OPEN (caller checks).
        """
        async with self._lock:
            if self.status != "OPEN":
                return

            # Mark closed first so the timer loop / further bids stop
            self.status = "SKIPPED"
            self.highest_bidder = None  # never sell on a skip

            if self._task and not self._task.done():
                self._task.cancel()
                try:
                    await self._task
                except (asyncio.CancelledError, Exception):
                    pass

            if not self.test_mode:
                E.log_unsold(self.guild_id, self.player)
                offered = OFFERED.get(self.guild_id, set())
                offered.discard(self.player["key"])

            try:
                if self.message:
                    await self.message.edit(view=None)
            except (discord.NotFound, discord.HTTPException):
                pass

            p = self.player
            face_url = E.get_face_url(p["key"])
            mv = P.market_value(p["ovr"], is_icon=P.is_icon(p))
            club_line = EM.club_tag(p.get("club", "") or "")

            title = f"TEST SKIP — {p['name']}" if self.test_mode else f"NOT SOLD — {p['name']}"
            desc = f"{p.get('position', '')} · {p.get('country', '')} · {club_line}"
            if self.test_mode:
                desc = f"**TEST MODE** — nothing saved.\n{desc}"

            e = discord.Embed(
                title=title,
                description=desc,
                color=C.SLATE,
                timestamp=datetime.now(timezone.utc),
            )
            if face_url:
                e.set_thumbnail(url=face_url)
            e.add_field(name="OVR", value=str(p["ovr"]), inline=True)
            e.add_field(name="Market Value", value=E.money(mv), inline=True)
            if skipped_by:
                e.set_footer(text=f"Skipped by {skipped_by.display_name}")
            elif self.test_mode:
                e.set_footer(text="Test auction — no money, no squad, no history")

            try:
                await self.channel.send(embed=e)
            except discord.HTTPException:
                pass

            # Test auctions must NOT advance management round bans / counters
            if not self.test_mode:
                try:
                    Cards.on_auction_finished(
                        self.guild_id, player_key=self.player.get("key")
                    )
                except Exception as ex:
                    print(f"[!] cards.on_auction_finished failed: {ex}")

            ACTIVE.pop(self.guild_id, None)

    async def _build_card_buf(self):
        """Build the compact auction card image."""
        time_left = max(0, int((self.end_time - datetime.now(timezone.utc)).total_seconds()))
        bidder_name = self.highest_bidder.display_name if self.highest_bidder else None
        return AC.render_auction_card(
            self.player, self.current_bid, bidder_name,
            self.next_min_bid(), time_left, self.bids, self.guild_id,
        )

    async def _send_card(self, is_initial=False):
        """Send a fresh auction card message with buttons."""
        buf = await self._build_card_buf()
        file = discord.File(buf, filename="auction.png")
        time_left = max(0, int((self.end_time - datetime.now(timezone.utc)).total_seconds()))
        if self.test_mode:
            content = (
                f"🧪 **TEST AUCTION** — **{self.player['name']}** on the block! "
                f"{time_left}s remaining · *no money / no sale*"
            )
        else:
            content = f"**{self.player['name']}** on the block! {time_left}s remaining"
        self.message = await self.channel.send(content=content, file=file, view=self.view)
        self._bids_since_last_card = 0

    async def _edit_card(self):
        """Edit the existing auction card message with updated bid info."""
        if not self.message:
            return
        try:
            buf = await self._build_card_buf()
            file = discord.File(buf, filename="auction.png")
            time_left = max(0, int((self.end_time - datetime.now(timezone.utc)).total_seconds()))
            content = f"**{self.player['name']}** - {time_left}s remaining"
            await self.message.edit(content=content, attachments=[file], view=self.view)
        except (discord.NotFound, discord.HTTPException):
            await self._resend_card()

    async def _resend_card(self):
        """Resend the auction card (new message at bottom of chat)."""
        await self._send_card(is_initial=False)

    async def _loop(self):
        last_edit = 0
        try:
            while self.status == "OPEN":
                await asyncio.sleep(2)
                now = datetime.now(timezone.utc)
                remaining = int((self.end_time - now).total_seconds())

                if remaining <= 0:
                    break

                if remaining <= 10 and remaining > 5 and not self._announced_once:
                    self._announced_once = True
                    await self._going_message("once")

                if remaining <= 5 and not self._announced_twice:
                    self._announced_twice = True
                    await self._going_message("twice")

                if last_edit == 0 or (last_edit - remaining) >= 8:
                    last_edit = remaining
                    await self._edit_card()
        except asyncio.CancelledError:
            # Admin skip (or cancel) stopped the loop — do not finalize as a sale
            return
        except (discord.NotFound, discord.HTTPException):
            pass

        # Only natural timer expiry reaches here while still OPEN
        if self.status == "OPEN":
            await self.finalize()

    async def _going_message(self, phase):
        """Send going once/twice + resend the card."""
        p = self.player
        bidder = self.highest_bidder
        price = f"£{self.current_bid:,}"

        text = "GOING ONCE" if phase == "once" else "GOING TWICE"

        if bidder:
            msg = (
                f"**{text}!** {p['name']} -> **{bidder.mention}** @ **{price}**\n"
                f"Bid above or miss out!"
            )
        else:
            msg = f"**{text}!** {p['name']} - no bids yet!"

        try:
            await self.channel.send(msg)
        except discord.HTTPException:
            pass

        await self._resend_card()

    async def finalize(self):
        if self.status != "OPEN":
            return

        winner = self.highest_bidder
        price = self.current_bid

        task_done = None
        if self.test_mode:
            # Pure dry-run: no balance, squad, history, task progress, or round counters
            self.status = "TEST_DONE"
        elif winner:
            self.status = "SOLD"
            E.adjust_balance(self.guild_id, winner.id, -price)
            E.add_player(self.guild_id, winner.id, self.player, price)
            E.log_auction(self.guild_id, self.player, winner.id, price, status="sold")
            try:
                task_done = Cards.on_player_bought(
                    self.guild_id, winner.id, self.player, price
                )
            except Exception as ex:
                print(f"[!] cards.on_player_bought failed: {ex}")
        else:
            self.status = "VOID"
            E.log_unsold(self.guild_id, self.player)
            # Remove from OFFERED so they can be re-auctioned later
            offered = OFFERED.get(self.guild_id, set())
            offered.discard(self.player["key"])

        try:
            if self.message:
                await self.message.edit(view=None)
        except (discord.NotFound, discord.HTTPException):
            pass

        # SOLD / NOT SOLD / TEST announcement
        p = self.player
        sold_emoji = Config.EMOJI_SOLD + " " if Config.EMOJI_SOLD else ""

        face_url = E.get_face_url(p["key"])

        club_line = EM.club_tag(p.get("club", "") or "")

        if self.test_mode:
            mv = P.market_value(p["ovr"], is_icon=P.is_icon(p))
            if winner:
                team_name = E.get_team_name(self.guild_id, winner.id) or winner.display_name
                team_tag = EM.club_tag(team_name)
                e = discord.Embed(
                    title=f"🧪 TEST SOLD — {p['name']}",
                    description=(
                        f"**Nothing was saved.** No money taken, no squad change.\n"
                        f"{EM.e('money')} Would have been **{E.money(price)}** → {team_tag}\n"
                        f"{p.get('position', '')} · {p.get('country', '')} · {club_line}"
                    ),
                    color=C.AMBER,
                    timestamp=datetime.now(timezone.utc),
                )
                e.add_field(name="High bidder", value=winner.mention, inline=True)
            else:
                e = discord.Embed(
                    title=f"🧪 TEST END — {p['name']}",
                    description=(
                        f"**Nothing was saved.** No unsold log, queue untouched.\n"
                        f"{p.get('position', '')} · {p.get('country', '')} · {club_line}"
                    ),
                    color=C.SLATE,
                    timestamp=datetime.now(timezone.utc),
                )
            if face_url:
                e.set_thumbnail(url=face_url)
            e.add_field(name="OVR", value=str(p["ovr"]), inline=True)
            e.add_field(name="Market Value", value=E.money(mv), inline=True)
            e.set_footer(text="Test auction complete")
        elif winner:
            remaining = E.get_balance(self.guild_id, winner.id)
            mv = P.market_value(p["ovr"], is_icon=P.is_icon(p))
            ratio = price / mv if mv else 1
            if ratio < 0.50:
                deal, deal_emoji = "STEAL", EM.e("fire") or "🔥"
            elif ratio < 0.80:
                deal, deal_emoji = "Great value", EM.e("check")
            elif ratio < 1.05:
                deal, deal_emoji = "Fair price", EM.e("check")
            elif ratio < 1.25:
                deal, deal_emoji = "Slight overpay", EM.e("warning") or "⚠️"
            else:
                deal, deal_emoji = "OVERPAY", EM.e("money_wings") or "💸"

            team_name = E.get_team_name(self.guild_id, winner.id) or winner.display_name
            team_tag = EM.club_tag(team_name)

            e = discord.Embed(
                title=f"{sold_emoji}SOLD! {p['name']}",
                description=(
                    f"{EM.e('money')} **{E.money(price)}** → {team_tag}\n"
                    f"{p.get('position', '')} · {p.get('country', '')} · {club_line}"
                ),
                color=C.EMERALD,
                timestamp=datetime.now(timezone.utc),
            )
            if face_url:
                e.set_thumbnail(url=face_url)
            e.add_field(name="OVR", value=str(p["ovr"]), inline=True)
            e.add_field(name="Market Value", value=E.money(mv), inline=True)
            e.add_field(name=f"{deal_emoji} Verdict", value=deal, inline=True)
            e.add_field(
                name="Budget Remaining",
                value=f"{winner.mention}: **{E.money(remaining)}**",
                inline=False,
            )
            e.set_footer(text=f"Signed by {winner.display_name}")
        else:
            mv = P.market_value(p["ovr"], is_icon=P.is_icon(p))
            e = discord.Embed(
                title=f"NOT SOLD — {p['name']}",
                description=(
                    f"{p.get('position', '')} · {p.get('country', '')} · {club_line}"
                ),
                color=C.SLATE,
                timestamp=datetime.now(timezone.utc),
            )
            if face_url:
                e.set_thumbnail(url=face_url)
            e.add_field(name="OVR", value=str(p["ovr"]), inline=True)
            e.add_field(name="Market Value", value=E.money(mv), inline=True)

        try:
            await self.channel.send(embed=e)
        except discord.HTTPException:
            pass

        # Management task completion ping (same channel as sold)
        if task_done and winner and not self.test_mode:
            try:
                await self.channel.send(
                    f"{EM.e('check')} {winner.mention} completed their task: "
                    f"**{task_done['card_text']}**"
                )
            except discord.HTTPException:
                pass

        # Advance auction round counter (for ban_first_n / temp bans)
        # Pass player_key so delayed peek bans activate AFTER this auction
        # Skip entirely for test auctions
        if not self.test_mode:
            try:
                Cards.on_auction_finished(
                    self.guild_id, player_key=self.player.get("key")
                )
            except Exception as ex:
                print(f"[!] cards.on_auction_finished failed: {ex}")

        ACTIVE.pop(self.guild_id, None)
