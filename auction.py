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
  - Custom emoji support for SOLD + bid buttons (config.py)
"""
import asyncio
from datetime import datetime, timedelta, timezone

import discord

from config import Config
import economy as E
import players as P
import auction_card as AC
import emojis as EM
from embed_colors import C

ACTIVE: dict = {}
OFFERED: dict = {}


def is_running(guild_id: int) -> bool:
    a = ACTIVE.get(guild_id)
    return a is not None and a.status == "OPEN"


def offered_keys(guild_id: int) -> set:
    return OFFERED.get(guild_id, set())


class CustomBidModal(discord.ui.Modal, title="Place a custom bid"):
    def __init__(self, auction: "Auction"):
        super().__init__()
        self.auction = auction
        nxt = auction.next_min_bid()
        self.amount = discord.ui.TextInput(
            label=f"Min bid: £{nxt:,}",
            placeholder="e.g. 45000000",
            required=True, max_length=12,
        )
        self.add_item(self.amount)

    async def on_submit(self, interaction: discord.Interaction):
        raw = str(self.amount.value).replace(",", "").replace("£", "").strip()
        try:
            bid = int(raw)
        except ValueError:
            await interaction.response.send_message("Invalid number.", ephemeral=True)
            return
        await self.auction.handle_bid(interaction, bid)


class AuctionView(discord.ui.View):
    def __init__(self, auction: "Auction"):
        super().__init__(timeout=None)
        self.auction = auction
        self.refresh_buttons()

    def refresh_buttons(self):
        a = self.auction
        nxt = a.next_min_bid()
        inc = nxt - a.current_bid
        self.min_bid.label = f"Bid £{nxt//1000000}M"
        self.quick_bid.label = f"+£{max(5_000_000, inc)//1000000}M"

    @discord.ui.button(label="Bid", style=discord.ButtonStyle.primary, row=0)
    async def min_bid(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.auction.handle_bid(interaction, self.auction.next_min_bid())

    @discord.ui.button(label="Bid +5M", style=discord.ButtonStyle.success, row=0)
    async def quick_bid(self, interaction: discord.Interaction, button: discord.ui.Button):
        inc = self.auction.next_min_bid() - self.auction.current_bid
        await self.auction.handle_bid(interaction, self.auction.current_bid + max(5_000_000, inc))

    @discord.ui.button(label="Custom", style=discord.ButtonStyle.secondary, row=0)
    async def custom_bid(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.auction.status != "OPEN":
            await interaction.response.send_message("Auction ended.", ephemeral=True)
            return
        await interaction.response.send_modal(CustomBidModal(self.auction))


class Auction:
    def __init__(self, guild_id, channel, player, started_by):
        self.guild_id = guild_id
        self.channel = channel
        self.player = player
        self.started_by = started_by

        self.start_price = P.start_price(player["ovr"], is_icon=P.is_icon(player))
        self.current_bid = self.start_price
        self.highest_bidder = None
        self.bids = 0

        self.end_time = datetime.now(timezone.utc) + timedelta(seconds=Config.AUCTION_DURATION)
        self.status = "OPEN"
        self.message = None
        self.view = AuctionView(self)
        self._task = None
        self._lock = asyncio.Lock()

        self._announced_once = False
        self._announced_twice = False
        self._bids_since_last_card = 0

    def next_min_bid(self):
        inc = max(Config.MIN_BID_INCREMENT_FLAT,
                  round(self.current_bid * Config.MIN_BID_INCREMENT_PCT / 1_000_000) * 1_000_000)
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
        return True, ""

    async def handle_bid(self, interaction, amount):
        ok, err = self._validate_bid(interaction.user, amount)
        if not ok:
            await interaction.response.send_message(err, ephemeral=True)
            return

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
        await interaction.response.send_message(
            f"Bid placed: **£{amount:,}** on {self.player['name']}", ephemeral=True)

        # 2) Public bid announcement message
        p = self.player
        msg = f"**{interaction.user.mention}** bids **£{amount:,}** on **{p['name']}**!"
        if extended:
            msg += "\n**ANTI-SNIPE!** Timer extended!"
        if was_leading and was_leading.id != interaction.user.id:
            msg += f"\n_(overtakes {was_leading.mention} who bid £{prev_bid:,})_"
        try:
            await self.channel.send(msg)
        except discord.HTTPException:
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
        OFFERED.setdefault(self.guild_id, set()).add(self.player["key"])

    async def _build_card_buf(self):
        """Build the compact auction card image."""
        time_left = max(0, int((self.end_time - datetime.now(timezone.utc)).total_seconds()))
        bidder_name = self.highest_bidder.display_name if self.highest_bidder else None
        return AC.render_auction_card(
            self.player, self.current_bid, bidder_name,
            self.next_min_bid(), time_left, self.bids, self.guild_id)

    async def _send_card(self, is_initial=False):
        """Send a fresh auction card message with buttons."""
        buf = await self._build_card_buf()
        file = discord.File(buf, filename="auction.png")
        time_left = max(0, int((self.end_time - datetime.now(timezone.utc)).total_seconds()))
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
        except (discord.NotFound, discord.HTTPException):
            pass
        await self.finalize()

    async def _going_message(self, phase):
        """Send going once/twice + resend the card."""
        p = self.player
        bidder = self.highest_bidder
        price = f"£{self.current_bid:,}"

        text = "GOING ONCE" if phase == "once" else "GOING TWICE"

        if bidder:
            msg = (f"**{text}!** {p['name']} -> **{bidder.mention}** @ **{price}**\n"
                   f"Bid above or miss out!")
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

        if winner:
            self.status = "SOLD"
            E.adjust_balance(self.guild_id, winner.id, -price)
            E.add_player(self.guild_id, winner.id, self.player, price)
            E.log_auction(self.guild_id, self.player, winner.id, price, status="sold")
        else:
            self.status = "VOID"
            E.log_unsold(self.guild_id, self.player)
            # Remove from OFFERED so they can be re-auctioned later
            offered = OFFERED.get(self.guild_id, set())
            offered.discard(self.player["key"])

        try:
            await self.message.edit(view=None)
        except (discord.NotFound, discord.HTTPException):
            pass

        # SOLD / NOT SOLD announcement
        p = self.player
        sold_emoji = Config.EMOJI_SOLD + " " if Config.EMOJI_SOLD else ""

        # Player face thumbnail (SoFIFA CDN URL — Discord fetches directly)
        face_url = E.get_face_url(p["key"])

        if winner:
            remaining = E.get_balance(self.guild_id, winner.id)
            mv = P.market_value(p["ovr"], is_icon=P.is_icon(p))
            ratio = price / mv if mv else 1
            if ratio < 0.50:
                deal, deal_emoji = "STEAL", "🔥"
            elif ratio < 0.80:
                deal, deal_emoji = "Great value", EM.e("check")
            elif ratio < 1.05:
                deal, deal_emoji = "Fair price", EM.e("check")
            elif ratio < 1.25:
                deal, deal_emoji = "Slight overpay", "⚠️"
            else:
                deal, deal_emoji = "OVERPAY", "💸"

            # winner's team name + club emoji
            team_name = E.get_team_name(self.guild_id, winner.id) or winner.display_name
            team_tag = EM.club_tag(team_name)

            e = discord.Embed(
                title=f"{sold_emoji}SOLD! {p['name']}",
                description=(
                    f"{EM.e('money')} **{E.money(price)}** → {team_tag}\n"
                    f"{p.get('position', '')} · {p.get('country', '')} · {p.get('club', '')}"
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
                    f"No bids were placed.\n"
                    f"{p.get('position', '')} · {p.get('country', '')} · {p.get('club', '')}"
                ),
                color=C.SLATE,
                timestamp=datetime.now(timezone.utc),
            )
            if face_url:
                e.set_thumbnail(url=face_url)
            e.add_field(name="OVR", value=str(p["ovr"]), inline=True)
            e.add_field(name="Market Value", value=E.money(mv), inline=True)
            e.set_footer(text="Use /drop to re-auction later")

        try:
            await self.channel.send(embed=e)
        except discord.HTTPException:
            pass

        ACTIVE.pop(self.guild_id, None)
