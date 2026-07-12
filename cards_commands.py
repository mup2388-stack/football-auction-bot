"""
Discord slash commands + persistent views for Management / Finance cards.

Wire-up in main.py (only this — no need to paste 500 lines into main):

    import cards as Cards
    import cards_commands

    bot = commands.Bot(...)

    # AFTER bot is created:
    cards_commands.setup(bot)

    # In on_ready, after db.init_db():
    try:
        Cards.ensure_schema()
    except Exception as e:
        print(f"[!] cards schema: {e}")

    # In /profile, before followup.send(embed=e):
    for line in Cards.profile_lines(interaction.guild_id, target.id):
        e.add_field(name="\\u200b", value=line, inline=False)

Persistent buttons:
  custom_id = cards:pick:management | cards:pick:finance
  Survives bot restarts. Disabled / removed when day is locked.
"""

from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

import cards as Cards
import economy as E
import players as P
import emojis as EM
from embed_colors import C
from config import is_admin


# ---------------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------------

class CardPickView(discord.ui.View):
    """
    Persistent pick button. custom_id encodes kind so it works after restart.
    """

    def __init__(self, kind: str):
        super().__init__(timeout=None)
        self.kind = kind
        # Rebuild the button with a stable custom_id
        self.clear_items()
        btn = discord.ui.Button(
            label="Pick a Card",
            style=discord.ButtonStyle.primary,
            custom_id=f"cards:pick:{kind}",
            row=0,
        )
        btn.callback = self._pick
        self.add_item(btn)

    async def _pick(self, interaction: discord.Interaction):
        kind = self.kind
        # custom_id fallback if view was reconstructed generically
        cid = getattr(interaction, "data", None) or {}
        if isinstance(cid, dict):
            raw = cid.get("custom_id") or ""
            if raw.startswith("cards:pick:"):
                kind = raw.split(":")[-1]

        day = Cards.get_open_day(interaction.guild_id, kind)
        if not day or day["status"] != "open":
            await interaction.response.send_message(
                "Card picks are closed.", ephemeral=True
            )
            # Try to strip buttons if message still has them
            try:
                await interaction.message.edit(view=None)
            except Exception:
                pass
            return

        await interaction.response.defer(ephemeral=True)
        try:
            a = Cards.draw_card(interaction.guild_id, interaction.user.id, kind)
        except Exception as ex:
            await interaction.followup.send(str(ex), ephemeral=True)
            return

        if kind == "management":
            msg = Cards.dm_card_message("management", a)
        else:
            bal = E.get_balance(interaction.guild_id, interaction.user.id)
            msg = (
                Cards.dm_card_message("finance", a)
                + f"\nNew balance: **{E.money(bal)}**"
            )

        await interaction.followup.send(msg, ephemeral=True)
        try:
            await interaction.user.send(msg)
        except Exception:
            pass

        # Refresh public counter only (never show tasks)
        try:
            await _refresh_pick_message(interaction.message, day, kind)
        except Exception:
            pass


async def _refresh_pick_message(message: discord.Message, day: dict, kind: str):
    assigns = Cards.list_assignments(day["id"])
    managers = Cards.season_manager_ids(day["guild_id"])
    left = len(Cards.remaining_keys(day["id"], kind))
    title = "Management Cards" if kind == "management" else "Finance Cards"
    color = C.AMBER if kind == "management" else C.TEAL
    e = discord.Embed(
        title=title,
        description=(
            f"Managers with a drawn team: press **Pick a Card**.\n"
            f"Cards are unique — no duplicates.\n\n"
            f"**Picked:** {len(assigns)} / {len(managers)}\n"
            f"**Left in deck:** {left}"
        ),
        color=color,
    )
    e.set_footer(text="Task text is private until admin reveals.")
    # Keep button only while open
    view = CardPickView(kind) if day.get("status") == "open" else None
    await message.edit(embed=e, view=view)


async def _strip_pick_button(guild: discord.Guild, day: dict, kind: str, reveal_embed: discord.Embed):
    """Edit the original pick message: remove button + show reveal (or locked)."""
    ch_id = day.get("channel_id")
    msg_id = day.get("message_id")
    if not ch_id or not msg_id or not guild:
        return
    channel = guild.get_channel(int(ch_id))
    if channel is None:
        try:
            channel = await guild.fetch_channel(int(ch_id))
        except Exception:
            return
    try:
        msg = await channel.fetch_message(int(msg_id))
        await msg.edit(embed=reveal_embed, view=None)
    except Exception as ex:
        print(f"[!] could not strip pick button: {ex}")


def _assignments_reveal_embed(guild_id: int, day: dict, kind: str) -> discord.Embed:
    assigns = Cards.list_assignments(day["id"])
    title = (
        "Management Cards — Locked"
        if kind == "management"
        else "Finance Cards — Reveal"
    )
    e = discord.Embed(title=title, color=C.OBSIDIAN)
    if kind == "management":
        e.description = (
            "Picks closed. Button removed.\n"
            "Anyone who didn't pick gets a leftover card on their **first bid**."
        )
    else:
        e.description = (
            "Picks closed. Button removed.\n"
            "Everyone with a drawn team got a finance card "
            "(auto-dealt if they didn't click). Balances already applied."
        )

    if not assigns:
        e.add_field(name="Results", value="Nobody picked a card.", inline=False)
        return e

    lines = []
    for a in assigns:
        # e.g. <:realmadrid:> Real Madrid (<@123>) — Buy 1 World Cup winner
        who = Cards.manager_line(guild_id, a["user_id"])
        if kind == "management":
            mark = EM.e("check") if a["status"] == "completed" else EM.e("x")
            lines.append(f"{mark} **{who}** — {a['card_text']}")
        else:
            lines.append(f"**{who}** — {a['card_text']}")

    chunk, size, field_i = [], 0, 1
    for line in lines:
        if size + len(line) + 1 > 1000 or len(chunk) >= 12:
            e.add_field(name=f"Results {field_i}", value="\n".join(chunk), inline=False)
            field_i += 1
            chunk, size = [], 0
        chunk.append(line)
        size += len(line) + 1
    if chunk:
        e.add_field(name=f"Results {field_i}", value="\n".join(chunk), inline=False)
    e.set_footer(text=f"{len(assigns)} manager(s)")
    return e


# ---------------------------------------------------------------------------
# Slash commands
# ---------------------------------------------------------------------------

def setup(bot: commands.Bot):
    """Register /cards commands. Persistent views attach in on_ready (needs event loop)."""

    cards_group = app_commands.Group(
        name="cards", description="Management & finance cards"
    )

    @cards_group.command(
        name="management",
        description="[Admin] Start / lock / end management cards",
    )
    @app_commands.describe(action="What to do")
    @app_commands.choices(action=[
        app_commands.Choice(name="Start (post pick button)", value="start"),
        app_commands.Choice(name="Lock picks + reveal (remove button)", value="lock"),
        app_commands.Choice(name="End day (£50M penalties)", value="end"),
        app_commands.Choice(name="Status", value="status"),
    ])
    async def cards_management(
        interaction: discord.Interaction,
        action: app_commands.Choice[str],
    ):
        if not is_admin(interaction.user.id):
            await interaction.response.send_message(
                f"{EM.e('x')} Admins only.", ephemeral=True
            )
            return
        await interaction.response.defer()
        act = action.value
        gid = interaction.guild_id

        if act == "start":
            try:
                day = Cards.start_day(
                    gid, "management", channel_id=interaction.channel.id
                )
            except Exception as ex:
                await interaction.followup.send(str(ex), ephemeral=True)
                return
            managers = Cards.season_manager_ids(gid)
            if not managers:
                await interaction.followup.send(
                    "No drawn teams in the active season. Run `/season draw` first.",
                    ephemeral=True,
                )
                return
            e = discord.Embed(
                title="Management Cards",
                description=(
                    f"Managers with a drawn team: press **Pick a Card**.\n"
                    f"Your task is private (ephemeral + DM).\n\n"
                    f"**Managers:** {len(managers)}\n"
                    f"**Picked:** 0 / {len(managers)}\n"
                    f"**Left in deck:** 32"
                ),
                color=C.AMBER,
            )
            e.set_footer(text="Admin: /cards management lock when ready")
            view = CardPickView("management")
            msg = await interaction.followup.send(embed=e, view=view)
            try:
                # followup may return WebhookMessage with .id
                mid = getattr(msg, "id", None)
                if mid:
                    Cards.set_day_message(day["id"], interaction.channel.id, mid)
            except Exception:
                pass
            return

        if act == "lock":
            day = Cards.get_open_day(gid, "management")
            if not day:
                await interaction.followup.send(
                    "No open management day.", ephemeral=True
                )
                return
            Cards.lock_day(day["id"])
            day = Cards.get_day(day["id"])
            e = _assignments_reveal_embed(gid, day, "management")
            # Remove button on original message
            await _strip_pick_button(interaction.guild, day, "management", e)
            # Also post a fresh reveal in-channel (in case old message missing)
            await interaction.followup.send(embed=e)
            return

        if act == "end":
            day = Cards.get_open_day(gid, "management")
            if not day:
                await interaction.followup.send(
                    "No open/locked management day.", ephemeral=True
                )
                return
            # Ensure button is gone even if they skipped lock
            try:
                Cards.lock_day(day["id"])
            except Exception:
                pass
            day = Cards.get_day(day["id"])
            try:
                e_lock = _assignments_reveal_embed(gid, day, "management")
                await _strip_pick_button(interaction.guild, day, "management", e_lock)
            except Exception:
                pass

            penalties = Cards.end_management_day(gid, day["id"])
            e = discord.Embed(
                title="Management Day Ended",
                description="Incomplete goals: **£50M** penalty each.",
                color=C.CRIMSON if penalties else C.EMERALD,
            )
            if penalties:
                lines = []
                for p in penalties:
                    who = Cards.manager_line(gid, p["user_id"])
                    lines.append(
                        f"{EM.e('x')} **{who}** — {E.money(p['penalty'])} "
                        f"(now {E.money(p['balance'])})\n_{p['card_text']}_"
                    )
                e.add_field(
                    name="Penalties",
                    value="\n".join(lines)[:1000],
                    inline=False,
                )
            else:
                e.add_field(
                    name="Penalties", value="None. Clean board.", inline=False
                )
            await interaction.followup.send(embed=e)
            return

        if act == "status":
            day = Cards.get_open_day(gid, "management")
            if not day:
                await interaction.followup.send(
                    "No active management day.", ephemeral=True
                )
                return
            assigns = Cards.list_assignments(day["id"])
            managers = Cards.season_manager_ids(gid)
            left = len(Cards.remaining_keys(day["id"], "management"))
            e = discord.Embed(
                title="Management Day Status",
                description=(
                    f"**Status:** {day['status']}\n"
                    f"**Picked:** {len(assigns)} / {len(managers)}\n"
                    f"**Deck left:** {left}\n"
                    f"**Auction round index:** {Cards.get_auction_round(gid)}"
                ),
                color=C.OBSIDIAN,
            )
            await interaction.followup.send(embed=e)

    @cards_group.command(
        name="finance",
        description="[Admin] Start / lock finance cards",
    )
    @app_commands.describe(action="What to do")
    @app_commands.choices(action=[
        app_commands.Choice(name="Start (post pick button)", value="start"),
        app_commands.Choice(name="Lock + reveal (remove button)", value="lock"),
        app_commands.Choice(name="Status", value="status"),
    ])
    async def cards_finance(
        interaction: discord.Interaction,
        action: app_commands.Choice[str],
    ):
        if not is_admin(interaction.user.id):
            await interaction.response.send_message(
                f"{EM.e('x')} Admins only.", ephemeral=True
            )
            return
        await interaction.response.defer()
        act = action.value
        gid = interaction.guild_id

        if act == "start":
            try:
                day = Cards.start_day(
                    gid, "finance", channel_id=interaction.channel.id
                )
            except Exception as ex:
                await interaction.followup.send(str(ex), ephemeral=True)
                return
            managers = Cards.season_manager_ids(gid)
            e = discord.Embed(
                title="Finance Cards",
                description=(
                    f"Press **Pick a Card**. Balance updates instantly.\n\n"
                    f"**Managers:** {len(managers)}\n"
                    f"**Picked:** 0 / {len(managers)}\n"
                    f"**Left in deck:** 32"
                ),
                color=C.TEAL,
            )
            e.set_footer(text="Admin: /cards finance lock when ready")
            view = CardPickView("finance")
            msg = await interaction.followup.send(embed=e, view=view)
            try:
                mid = getattr(msg, "id", None)
                if mid:
                    Cards.set_day_message(day["id"], interaction.channel.id, mid)
            except Exception:
                pass
            return

        if act == "lock":
            day = Cards.get_open_day(gid, "finance")
            if not day:
                await interaction.followup.send(
                    "No open finance day.", ephemeral=True
                )
                return

            # Auto-deal leftover finance cards to every drawn manager
            # who didn't click Pick a Card (balance applied immediately)
            try:
                summary = Cards.auto_assign_finance_on_lock(gid, day["id"])
            except Exception as ex:
                await interaction.followup.send(
                    f"{EM.e('x')} Auto-assign failed: {ex}", ephemeral=True
                )
                return

            Cards.lock_day(day["id"])
            # Finance finished after reveal
            import database as _db
            with _db.cursor() as c:
                c.execute(
                    "UPDATE card_days SET status='ended', ended_at=datetime('now') "
                    "WHERE id=?",
                    (day["id"],),
                )
            day = Cards.get_day(day["id"]) or day
            e = _assignments_reveal_embed(gid, day, "finance")
            auto_n = summary.get("assigned_count", 0)
            if auto_n:
                e.set_footer(
                    text=(
                        f"{len(Cards.list_assignments(day['id']))} manager(s) · "
                        f"{auto_n} auto-dealt on lock"
                    )
                )
            await _strip_pick_button(interaction.guild, day, "finance", e)
            await interaction.followup.send(embed=e)

            # Best-effort DM for people who were auto-dealt
            for a in summary.get("assigned") or []:
                uid = a.get("user_id")
                member = interaction.guild.get_member(int(uid)) if uid else None
                if not member:
                    continue
                try:
                    bal = E.get_balance(gid, int(uid))
                    await member.send(
                        Cards.dm_card_message("finance", a)
                        + f"\n_(auto-assigned on lock)_\n"
                        f"New balance: **{E.money(bal)}**"
                    )
                except Exception:
                    pass
            return

        if act == "status":
            day = Cards.get_open_day(gid, "finance")
            if not day:
                await interaction.followup.send(
                    "No active finance day.", ephemeral=True
                )
                return
            assigns = Cards.list_assignments(day["id"])
            e = discord.Embed(
                title="Finance Day Status",
                description=(
                    f"**Status:** {day['status']} · **Picked:** {len(assigns)}"
                ),
                color=C.TEAL,
            )
            await interaction.followup.send(embed=e)

    @cards_group.command(
        name="complete",
        description="[Admin] Mark a manager's manual management goal complete",
    )
    @app_commands.describe(user="Manager who completed a manual task")
    async def cards_complete(
        interaction: discord.Interaction, user: discord.Member
    ):
        if not is_admin(interaction.user.id):
            await interaction.response.send_message(
                f"{EM.e('x')} Admins only.", ephemeral=True
            )
            return
        await interaction.response.defer()
        a = Cards.admin_complete(interaction.guild_id, user.id)
        if not a:
            await interaction.followup.send(
                "No active management card for that user.", ephemeral=True
            )
            return
        await interaction.followup.send(
            f"{EM.e('check')} Marked complete for {user.mention}: "
            f"**{a['card_text']}**"
        )

    @cards_group.command(
        name="set",
        description="[Admin] Change a manager's management card / spend caps",
    )
    @app_commands.describe(
        user="Manager whose card to change",
        max_spend_millions="Total spend cap tonight in millions (e.g. 250 = £250M). Leave empty to keep.",
        max_bid_millions="Max bid on ONE player in millions (e.g. 90). Leave empty to keep.",
        custom_text="Optional full replacement task text",
        preset="Optional: switch to a predefined card type",
    )
    @app_commands.choices(preset=[
        app_commands.Choice(name="Keep current card (only edit caps/text)", value="keep"),
        app_commands.Choice(name="No task (free pass)", value="no_task_ggs"),
        app_commands.Choice(name="Spend cap £100M night", value="spend_cap_100m_night"),
        app_commands.Choice(name="Max £90M per player", value="max_per_player_90m"),
        app_commands.Choice(name="Max £70M per player", value="max_per_player_70m"),
        app_commands.Choice(name="Can't bid first 3 rounds", value="no_bid_first_3_a"),
        app_commands.Choice(name="Buy 1 icon", value="buy_icon"),
        app_commands.Choice(name="Buy at least 2 players", value="buy_two_players"),
        app_commands.Choice(name="Max 1 icon tonight", value="max_one_icon"),
        app_commands.Choice(name="No defenders", value="no_defenders"),
    ])
    async def cards_set(
        interaction: discord.Interaction,
        user: discord.Member,
        max_spend_millions: int = None,
        max_bid_millions: int = None,
        custom_text: str = None,
        preset: app_commands.Choice[str] = None,
    ):
        if not is_admin(interaction.user.id):
            await interaction.response.send_message(
                f"{EM.e('x')} Admins only.", ephemeral=True
            )
            return
        await interaction.response.defer()

        if (
            max_spend_millions is None
            and max_bid_millions is None
            and not (custom_text and custom_text.strip())
            and (preset is None or preset.value == "keep")
        ):
            await interaction.followup.send(
                "Nothing to change. Set a preset, custom text, and/or a spend/bid cap.",
                ephemeral=True,
            )
            return

        card_key = None
        if preset and preset.value != "keep":
            card_key = preset.value

        max_night = (
            int(max_spend_millions) * 1_000_000
            if max_spend_millions is not None
            else None
        )
        max_bid = (
            int(max_bid_millions) * 1_000_000
            if max_bid_millions is not None
            else None
        )

        try:
            a = Cards.admin_set_management_card(
                interaction.guild_id,
                user.id,
                card_key=card_key,
                custom_text=custom_text,
                max_night_spend=max_night,
                max_bid=max_bid,
            )
        except Exception as ex:
            await interaction.followup.send(f"{EM.e('x')} {ex}", ephemeral=True)
            return

        who = Cards.manager_line(interaction.guild_id, user.id)
        await interaction.followup.send(
            f"{EM.e('check')} Updated card for **{who}**\n"
            f"**New task:** {a['card_text']}"
        )
        try:
            await user.send(
                f"**Your management card was updated by admin.**\n"
                f"{a['card_text']}\n\n"
                f"Check `/profile` anytime."
            )
        except Exception:
            pass

    @cards_group.command(
        name="steal",
        description="[Admin] Resolve steal power: move player thief ← victim",
    )
    @app_commands.describe(
        thief="Manager using the steal card",
        victim="Manager losing the player",
        player="Player name",
    )
    async def cards_steal(
        interaction: discord.Interaction,
        thief: discord.Member,
        victim: discord.Member,
        player: str,
    ):
        if not is_admin(interaction.user.id):
            await interaction.response.send_message(
                f"{EM.e('x')} Admins only.", ephemeral=True
            )
            return
        await interaction.response.defer()
        p = P.get(player)
        if not p:
            results = P.search(player, limit=1)
            p = results[0] if results else None
        if not p:
            await interaction.followup.send("Player not found.", ephemeral=True)
            return
        try:
            res = Cards.use_power_steal(
                interaction.guild_id, thief.id, victim.id, p["key"]
            )
        except Exception as ex:
            await interaction.followup.send(str(ex), ephemeral=True)
            return
        await interaction.followup.send(
            f"{EM.e('check')} **Steal complete**\n"
            f"{P.flag(res['player']['country'])} **{res['player']['name']}** "
            f"→ {thief.mention} for **{E.money(res['price'])}** "
            f"(paid to {victim.mention}).\n"
            f"{thief.mention} can't bid for the next **{res['ban']}** auctions."
        )

    @cards_group.command(
        name="swap",
        description="[Admin] Resolve swap power: half-price cash + player trade",
    )
    @app_commands.describe(
        taker="Manager using the swap card (pays half + gives a player)",
        giver="Manager losing the target player",
        take="Player taker wants (from giver's squad)",
        give="Player taker offers (must be 80+ OVR)",
    )
    async def cards_swap(
        interaction: discord.Interaction,
        taker: discord.Member,
        giver: discord.Member,
        take: str,
        give: str,
    ):
        if not is_admin(interaction.user.id):
            await interaction.response.send_message(
                f"{EM.e('x')} Admins only.", ephemeral=True
            )
            return
        await interaction.response.defer()

        take_p = P.get(take) or (P.search(take, limit=1) or [None])[0]
        give_p = P.get(give) or (P.search(give, limit=1) or [None])[0]
        if not take_p or not give_p:
            await interaction.followup.send("Player not found.", ephemeral=True)
            return
        try:
            res = Cards.use_power_swap(
                interaction.guild_id,
                taker.id,
                giver.id,
                take_p["key"],
                give_p["key"],
            )
        except Exception as ex:
            await interaction.followup.send(f"{EM.e('x')} {ex}", ephemeral=True)
            return

        tp, gp = res["take_player"], res["give_player"]
        await interaction.followup.send(
            f"{EM.e('check')} **Swap complete**\n"
            f"{taker.mention} gets {P.flag(tp['country'])} **{tp['name']}** "
            f"(was {E.money(res['take_price'])})\n"
            f"{giver.mention} gets {P.flag(gp['country'])} **{gp['name']}** "
            f"+ **{E.money(res['cash'])}** cash (half price)\n"
            f"Swap card marked complete."
        )

    @cards_group.command(
        name="peek",
        description="[Admin] Reveal next queue player to a manager (peek power)",
    )
    @app_commands.describe(user="Manager using peek power")
    async def cards_peek(
        interaction: discord.Interaction, user: discord.Member
    ):
        if not is_admin(interaction.user.id):
            await interaction.response.send_message(
                f"{EM.e('x')} Admins only.", ephemeral=True
            )
            return
        await interaction.response.defer(ephemeral=True)
        try:
            res = Cards.use_power_peek(interaction.guild_id, user.id)
        except Exception as ex:
            await interaction.followup.send(str(ex), ephemeral=True)
            return
        p = res["player"]
        text = (
            f"**Next in queue:** {P.flag(p['country'])} **{p['name']}** "
            f"— {p['position']} — **{p['ovr']}** OVR — {p.get('club', '')}\n\n"
            f"You **can bid** on **{p['name']}**.\n"
            f"After their auction ends, you can't bid for the next "
            f"**{res['ban']}** auctions."
        )
        try:
            await user.send(text)
            dm_ok = True
        except Exception:
            dm_ok = False
        await interaction.followup.send(
            f"{EM.e('check')} Peek used for {user.mention}. "
            f"{'DM sent.' if dm_ok else 'Could not DM — show them privately:'}\n"
            f"{text}",
            ephemeral=True,
        )
        await interaction.channel.send(
            f"{user.mention} used **peek** on the next player. "
            f"They can bid on that one; after it sells/ends they sit out "
            f"**{res['ban']}** auctions."
        )

    # Register group
    try:
        bot.tree.add_command(cards_group)
    except discord.app_commands.errors.CommandAlreadyRegistered:
        pass

    # Persistent views need a running loop — register once the bot is ready
    @bot.listen("on_ready")
    async def _cards_register_persistent_views():
        # Only register once per process
        if getattr(bot, "_cards_views_registered", False):
            return
        bot.add_view(CardPickView("management"))
        bot.add_view(CardPickView("finance"))
        bot._cards_views_registered = True  # type: ignore[attr-defined]
        print("[✓] cards: persistent Pick a Card views registered")

    print("[✓] cards_commands.setup() — /cards commands registered")
