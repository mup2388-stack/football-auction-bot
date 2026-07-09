"""
Football Auction management bot — entry point.

Designed for running real auction drafts for a football league simulation
(e.g. Football Life 26). The admin controls the cadence: drop one player,
let managers bid, it sells, the bot WAITS, then the admin drops the next one.

Run:
    python main.py
"""
import os
# Allow OAuth over HTTP for localhost — MUST be before any oauthlib imports
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

import random

import discord
from discord import app_commands
from discord.ext import commands

from config import Config, is_admin
import database as db
import economy as E
import players as P
import auction as A
import display as D
import squad_card as SC
import player_card as PC
import bench_card as BC
import compare_card as CC
import league as L
import emojis as EM
from embed_colors import C


# --------------------------------------------------------------------------
# Bot setup
# --------------------------------------------------------------------------
intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix=Config.PREFIX, intents=intents)


@bot.event
async def on_ready():
    db.init_db()
    L.init()
    # Start the website dashboard (background thread, same process)
    if Config.WEB_ENABLED:
        try:
            from website.app import run_in_thread
            run_in_thread(port=Config.WEB_PORT)
        except ImportError:
            print("[!] Flask not installed — website disabled. Run: pip install flask")
        except Exception as e:
            print(f"[!] Website failed to start: {e}")
    try:
        guild_id = os.getenv("GUILD_ID")
        if guild_id:
            guild = discord.Object(id=int(guild_id))
            synced = await bot.tree.sync(guild=guild)
            print(f"[✓] Synced {len(synced)} commands to guild {guild_id} (instant).")
        else:
            synced = await bot.tree.sync()
            print(f"[✓] Synced {len(synced)} commands globally (may take up to 1 hour).")
    except Exception as e:
        print(f"[!] Command sync issue: {e}")
    print(f"[✓] Logged in as {bot.user} ({bot.user.id})")
    print(f"[✓] {len(P.all_players())} players loaded.")
    # Set bot activity status - shows under the bot name in the member list
    try:
        await bot.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="FL26 auctions"
            )
        )
    except Exception:
        pass


# --------------------------------------------------------------------------
# Autocomplete
# --------------------------------------------------------------------------
async def player_autocomplete(interaction: discord.Interaction, current: str):
    """Suggest players from the QUEUE (not yet sold) for /drop."""
    queued = E.queue_list(interaction.guild_id)
    if not queued:
        return []
    sold = E.sold_player_keys(interaction.guild_id)
    choices = []
    q_lower = current.lower().strip() if current else ""
    for key in queued:
        if key in sold:
            continue
        p = P.get(key)
        if not p:
            continue
        if q_lower and q_lower not in p["name"].lower():
            continue
        choices.append(app_commands.Choice(
            name=f"{p['name']} ({p['ovr']} OVR) {p['group']}",
            value=p["key"]))
        if len(choices) >= 25:
            break
    return choices


async def all_player_autocomplete(interaction: discord.Interaction, current: str):
    """Suggest ALL players (including sold ones) — for /setface etc."""
    if current:
        matches = P.search(current)
    else:
        matches = sorted(P.all_players(), key=lambda p: p["ovr"], reverse=True)
    choices = []
    for p in matches:
        sold = E.is_sold(interaction.guild_id, p["key"])
        tag = " [SOLD]" if sold else ""
        choices.append(app_commands.Choice(
            name=f"{p['name']} — {p.get('club','')} ({p['ovr']} OVR){tag}",
            value=p["key"]))
        if len(choices) >= 25:
            break
    return choices


PHASE_CHOICES = [
    app_commands.Choice(name="All positions", value="ALL"),
    app_commands.Choice(name="Goalkeepers (GK)", value="GK"),
    app_commands.Choice(name="Defenders (DEF)", value="DEF"),
    app_commands.Choice(name="Midfielders (MID)", value="MID"),
    app_commands.Choice(name="Forwards (FWD)", value="FWD"),
    app_commands.Choice(name="Unsold players", value="UNSOLD"),
]


# ==========================================================================
#  Helper to start an auction from a player
# ==========================================================================
async def _start_auction(interaction: discord.Interaction, player: dict, starter_msg: str):
    # Caller has ALREADY deferred. Don't defer again.
    if A.is_running(interaction.guild_id):
        await interaction.followup.send(
            "An auction is already running.", ephemeral=True)
        return
    if E.is_sold(interaction.guild_id, player["key"]):
        await interaction.followup.send(
            f"{EM.e('x')} {player['name']} has already been sold.", ephemeral=True)
        return
    E.queue_consume(interaction.guild_id, player["key"])
    await interaction.followup.send(starter_msg, ephemeral=True)
    a = A.Auction(interaction.guild_id, interaction.channel, player, interaction.user)
    await a.start()
    # Ping watchers
    watchers = E.watch_watchers(interaction.guild_id, player["key"])
    if watchers:
        mentions = " ".join(f"<@{uid}>" for uid in watchers)
        try:
            await interaction.channel.send(
                f"**WATCH ALERT!** {mentions} — **{player['name']}** is now on the block!")
        except discord.HTTPException:
            pass


# ==========================================================================
#  MANAGER COMMANDS
# ==========================================================================
@bot.tree.command(description="Check your budget (or someone else's).")
@app_commands.describe(user="Whose budget to check (defaults to you).")
async def balance(interaction: discord.Interaction, user: discord.Member = None):
    await interaction.response.defer()
    target = user or interaction.user
    bal = E.get_balance(interaction.guild_id, target.id)
    squad = E.get_squad(interaction.guild_id, target.id)
    sv = E.squad_value(squad)
    net = bal + sv
    spent = Config.STARTING_BALANCE - bal
    pct = round(spent / Config.STARTING_BALANCE * 100) if Config.STARTING_BALANCE else 0
    team_name = E.get_team_name(interaction.guild_id, target.id) or target.display_name
    team_tag = EM.club_tag(team_name)

    e = discord.Embed(
        title=f"{EM.e('manager')} {team_tag}",
        description=f"{EM.e('money')} **{E.money(bal)}** available to spend.",
        color=C.AMBER,
    )
    e.set_thumbnail(url=target.display_avatar.url)
    e.add_field(name="Squad Value", value=E.money(sv), inline=True)
    e.add_field(name="Net Worth", value=f"**{E.money(net)}**", inline=True)
    e.add_field(name="Squad Size", value=f"{len(squad)}", inline=True)
    if spent > 0:
        e.add_field(name="Spent", value=f"{E.money(spent)} ({pct}%)", inline=True)
    e.set_footer(text=f"{target.display_name}")
    await interaction.followup.send(embed=e)


@bot.tree.command(description="View a manager's net worth, budget and top players.")
@app_commands.describe(user="Whose profile to view (defaults to you).")
async def profile(interaction: discord.Interaction, user: discord.Member = None):
    await interaction.response.defer()
    target = user or interaction.user
    squad = E.get_squad(interaction.guild_id, target.id)
    bal = E.get_balance(interaction.guild_id, target.id)
    sv = E.squad_value(squad)
    top = sorted(squad, key=lambda p: p["ovr"], reverse=True)[:3]
    stars = "\n".join(f"{P.flag(p['country'])} {p['name']} — {p['ovr']} OVR"
                      for p in top) or "_(no players yet)_"

    e = discord.Embed(title=f"{EM.e('manager')} {target.display_name}", color=C.SLATE)
    e.add_field(name="Budget", value=E.money(bal), inline=True)
    e.add_field(name="Squad Value", value=E.money(sv), inline=True)
    e.add_field(name="Net Worth", value=f"**{E.money(bal + sv)}**", inline=True)
    e.add_field(name="Top Players", value=stars, inline=False)
    e.add_field(name="Squad Size", value=f"{len(squad)} player(s)", inline=True)
    e.set_thumbnail(url=target.display_avatar.url)
    await interaction.followup.send(embed=e)


class BenchButton(discord.ui.View):
    """View with a button to see the bench."""
    def __init__(self, guild_id, target_id, squad):
        super().__init__(timeout=300)
        self.guild_id = guild_id
        self.target_id = target_id
        self.squad = squad

    @discord.ui.button(label="View Bench", style=discord.ButtonStyle.secondary, row=0)
    async def view_bench(self, interaction: discord.Interaction, button: discord.ui.Button):
        lineup, _ = E.get_lineup(self.guild_id, self.target_id)
        xi_keys = {p["key"] for _, p in lineup if p}
        team_name = E.get_team_name(self.guild_id, self.target_id)
        if not team_name:
            m = interaction.guild.get_member(self.target_id)
            team_name = m.display_name if m else "Unknown"
        try:
            buf = BC.render_bench_card(self.guild_id, team_name, self.target_id, self.squad, xi_keys)
            file = discord.File(buf, filename="bench.png")
            await interaction.response.send_message(content=f"**{team_name}** — Bench", file=file)
        except Exception as e:
            await interaction.response.send_message(f"Error: {e}", ephemeral=True)


@bot.tree.command(description="View a manager's best XI as a tactics-board image + bench button.")
@app_commands.describe(user="Whose team to view (defaults to you).")
async def team(interaction: discord.Interaction, user: discord.Member = None):
    await interaction.response.defer(thinking=True)
    target = user or interaction.user
    E.ensure_user(interaction.guild_id, target.id)
    squad = E.get_squad(interaction.guild_id, target.id)
    if not squad:
        await interaction.followup.send(
            f"{target.mention} has no players yet.", ephemeral=True)
        return
    try:
        buf = SC.render_squad_card(interaction.guild_id, target.display_name,
                                   target.id, squad,
                                   avatar_url=target.display_avatar.url)
        file = discord.File(buf, filename="squad.png")
        view = BenchButton(interaction.guild_id, target.id, squad)
        await interaction.followup.send(
            content=f"**{target.display_name}** — Starting XI", file=file, view=view)
    except Exception as e:
        await interaction.followup.send(
            f"Couldn't render ({e}). Text version:",
            embed=D.build_team_embed(interaction.guild_id, target))


@bot.tree.command(description="View a manager's squad with player stats and season info.")
@app_commands.describe(user="Whose squad to view (defaults to you).")
async def squad(interaction: discord.Interaction, user: discord.Member = None):
    await interaction.response.defer()
    target = user or interaction.user
    guild_id = interaction.guild_id
    E.ensure_user(guild_id, target.id)
    squad = E.get_squad(guild_id, target.id)
    if not squad:
        await interaction.followup.send(
            f"{target.mention} has no players yet.", ephemeral=True)
        return

    team_name = E.get_team_name(guild_id, target.id) or target.display_name
    bal = E.get_balance(guild_id, target.id)
    sv = E.squad_value(squad)

    # Build the embed
    pr = E.power_rating(interaction.guild_id, target.id)
    e = discord.Embed(
        title=f"{EM.e('manager')} {team_name} - Squad Overview",
        description=f"**{len(squad)} players** - **{E.money(sv)}** value - **{E.money(bal)}** budget left - **Power Rating: {pr}/100**",
        color=C.TEAL,
    )

    # Season stats (if an active season exists)
    season = L.active_season(guild_id)
    if season:
        s_id = season["id"]
        tms = L.teams(s_id)
        if any(t["user_id"] == target.id for t in tms):
            if any(t.get("group_label") for t in tms):
                rows = L.standings(s_id, group=None, stage="group")
            else:
                rows = L.standings(s_id, stage="league")
            # find this team's row
            team_row = next((r for r in rows if r["user_id"] == target.id), None)
            if team_row and team_row["P"] > 0:
                pos = rows.index(team_row) + 1
                e.add_field(name="Season", value=(
                    f"Position: **{pos}/{len(rows)}**\n"
                    f"P{team_row['P']} W{team_row['W']} D{team_row['D']} L{team_row['L']} - **{team_row['Pts']}pts**\n"
                    f"GF {team_row['GF']} GA {team_row['GA']} GD {team_row['GD']:+d}"
                ), inline=False)

    # Squad match stats aggregate (per active season)
    _s = L.active_season(guild_id)
    _sid = _s["id"] if _s else None
    squad_stats = E.get_squad_match_stats(guild_id, target.id, season_id=_sid)
    if squad_stats["goals"] > 0 or squad_stats["matches"] > 0:
        e.add_field(name="Team Stats", value=(
            f"{EM.e('stat_appearances')} Apps **{squad_stats['matches']}**  "
            f"{EM.e('stat_goals')} Goals **{squad_stats['goals']}**  "
            f"{EM.e('stat_assists')} Assists **{squad_stats['assists']}**\n"
            f"{EM.e('stat_motm')} MOTM **{squad_stats['motm']}**  "
            f"{EM.e('stat_yellow')} Yellows **{squad_stats['yellow_cards']}**  "
            f"{EM.e('stat_red')} Reds **{squad_stats['red_cards']}**"
        ), inline=False)

    # Players by group with match stats
    groups = {"GK": [], "DEF": [], "MID": [], "FWD": []}
    for p in squad:
        groups.setdefault(p["group"], []).append(p)
    group_labels = {"GK": "Goalkeepers", "DEF": "Defenders",
                    "MID": "Midfielders", "FWD": "Forwards"}
    for gkey in P.PHASE_ORDER:
        players = sorted(groups.get(gkey, []), key=lambda p: p["ovr"], reverse=True)
        if not players:
            continue
        lines = []
        for p in players[:8]:
            ps = E.get_player_stats(guild_id, p["key"], season_id=_sid)
            stat_bits = []
            if ps["goals"]: stat_bits.append(f"{EM.e('stat_goals')}{ps['goals']}")
            if ps["assists"]: stat_bits.append(f"{EM.e('stat_assists')}{ps['assists']}")
            if ps["motm"]: stat_bits.append(f"{EM.e('stat_motm')}{ps['motm']}")
            stat_str = f" ({'  '.join(stat_bits)})" if stat_bits else ""
            lines.append(
                f"{P.flag(p['country'])} **{p['name']}** {p['position']} **{p['ovr']}**{stat_str}"
            )
        e.add_field(name=f"{group_labels[gkey]} ({len(players)})",
                    value="\n".join(lines), inline=False)

    e.set_thumbnail(url=target.display_avatar.url)
    await interaction.followup.send(embed=e)


@bot.tree.command(description="View a player's FULL detailed card (all stats, skills, positions).")
@app_commands.describe(name="Player to look up.")
@app_commands.autocomplete(name=all_player_autocomplete)
async def player(interaction: discord.Interaction, name: str):
    await interaction.response.defer(thinking=True)
    p = P.get(name)
    if not p:
        await interaction.followup.send(f"{EM.e('x')} Player not found.", ephemeral=True)
        return
    try:
        buf = PC.render_player_card(p, guild_id=interaction.guild_id)
        file = discord.File(buf, filename="player.png")
        await interaction.followup.send(
            content=f"**{P.flag(p['country'])} {p['name']}** ({p['ovr']} OVR)", file=file)
    except Exception as e:
        await interaction.followup.send(
            f"Couldn't render ({e}). Text version:",
            embed=D.build_player_embed(p))


# ==========================================================================
#  PLAYER MATCH STATS
# ==========================================================================
@bot.tree.command(description="View a player's match stats (goals, assists, MOTM, cards).")
@app_commands.describe(name="Player to view stats for.")
@app_commands.autocomplete(name=all_player_autocomplete)
async def playerstats(interaction: discord.Interaction, name: str):
    await interaction.response.defer()
    p = P.get(name)
    if not p:
        await interaction.followup.send("Player not found.", ephemeral=True)
        return
    _s = L.active_season(interaction.guild_id)
    _sid = _s["id"] if _s else None
    stats = E.get_player_stats(interaction.guild_id, name, season_id=_sid)

    if stats["matches"] == 0:
        owner = E.get_player_owner(interaction.guild_id, name)
        team = owner[1] if owner and owner[1] else p.get("club", "")
        await interaction.followup.send(
            f"**{p['name']}** ({team}) has no match stats yet.", ephemeral=True)
        return

    owner = E.get_player_owner(interaction.guild_id, name)
    team = owner[1] if owner and owner[1] else p.get("club", "")

    e = discord.Embed(
        title=f"{P.flag(p['country'])} {p['name']} - Match Stats",
        description=f"**{p['position']}** - {p['ovr']} OVR - {team}",
        color=C.AMBER,
    )
    e.add_field(name=f"{EM.e('stat_appearances')} Apps", value=str(stats["matches"]))
    e.add_field(name=f"{EM.e('stat_goals')} Goals", value=str(stats["goals"]))
    e.add_field(name=f"{EM.e('stat_assists')} Assists", value=str(stats["assists"]))
    e.add_field(name=f"{EM.e('stat_motm')} MOTM", value=str(stats["motm"]))
    e.add_field(name=f"{EM.e('stat_tackles')} Tackles", value=str(stats["tackles"]))
    e.add_field(name=f"{EM.e('stat_saves')} Saves", value=str(stats["saves"]))
    e.add_field(name=f"{EM.e('stat_yellow')} Yellow", value=str(stats["yellow_cards"]))
    e.add_field(name=f"{EM.e('stat_red')} Red", value=str(stats["red_cards"]))

    # Goal contributions per 90 (if matches > 0)
    if stats["matches"] > 0:
        gc = stats["goals"] + stats["assists"]
        gp90 = round(gc / stats["matches"], 2)
        e.set_footer(text=f"Goal contributions: {gc} ({gp90}/match)")

    await interaction.followup.send(embed=e)


# ==========================================================================
#  COMPARISON  (/compare + /matchup)
# ==========================================================================
@bot.tree.command(description="Compare two players head-to-head (stats duel).")
@app_commands.describe(
    player1="First player (the BLUE side).",
    player2="Second player (the CORAL side).")
@app_commands.autocomplete(player1=all_player_autocomplete)
@app_commands.autocomplete(player2=all_player_autocomplete)
async def compare(interaction: discord.Interaction, player1: str, player2: str):
    await interaction.response.defer(thinking=True)
    a = P.get(player1)
    b = P.get(player2)
    if not a:
        await interaction.followup.send(f"{EM.e('x')} First player not found.", ephemeral=True)
        return
    if not b:
        await interaction.followup.send(f"{EM.e('x')} Second player not found.", ephemeral=True)
        return
    if a["key"] == b["key"]:
        await interaction.followup.send(f"{EM.e('x')} Pick two *different* players to compare.", ephemeral=True)
        return
    try:
        buf = CC.render_player_duel(a, b, guild_id=interaction.guild_id)
        file = discord.File(buf, filename="compare.png")
        await interaction.followup.send(
            content=f"**{P.flag(a['country'])} {a['name']}** vs **{P.flag(b['country'])} {b['name']}**",
            file=file)
    except Exception as e:
        await interaction.followup.send(f"Couldn't render the duel ({e}).", ephemeral=True)


@bot.tree.command(description="Position-by-position matchup: your team vs another manager.")
@app_commands.describe(user="The manager to face off against (defaults to a random rival).")
async def matchup(interaction: discord.Interaction, user: discord.Member = None):
    await interaction.response.defer(thinking=True)
    me = interaction.user
    them = user
    if them and them.id == me.id:
        await interaction.followup.send(f"{EM.e('x')} You can't match up against yourself. Pick a rival!", ephemeral=True)
        return
    if them is None:
        with db.cursor() as c:
            rows = c.execute(
                "SELECT DISTINCT user_id FROM squads WHERE guild_id=? AND user_id!=?",
                (interaction.guild_id, me.id)).fetchall()
        owners = {r["user_id"] for r in rows}
        if not owners:
            await interaction.followup.send(
                f"{EM.e('x')} No rival managers with players yet. Try `/matchup @someone`.", ephemeral=True)
            return
        import random as _r
        them_id = _r.choice(list(owners))
        member = interaction.guild.get_member(them_id)
        them = member
        if them is None:
            await interaction.followup.send(
                f"{EM.e('x')} Couldn't resolve that manager. Try `/matchup @someone`.", ephemeral=True)
            return

    me_count = E.squad_count(interaction.guild_id, me.id)
    them_count = E.squad_count(interaction.guild_id, them.id)
    if me_count == 0:
        await interaction.followup.send(f"{EM.e('x')} You have no players yet. Win some auctions first!", ephemeral=True)
        return
    if them_count == 0:
        await interaction.followup.send(f"{EM.e('x')} **{them.display_name}** has no players yet.", ephemeral=True)
        return

    try:
        me_name = E.get_team_name(interaction.guild_id, me.id) or me.display_name
        them_name = E.get_team_name(interaction.guild_id, them.id) or them.display_name
        me_logo = E.get_team_logo(interaction.guild_id, me.id) or str(me.display_avatar.url)
        them_logo = E.get_team_logo(interaction.guild_id, them.id) or str(them.display_avatar.url)
        buf = CC.render_team_matchup(
            interaction.guild_id, me.id, them.id, me_name, them_name,
            logo_a=me_logo, logo_b=them_logo,
            avatar_a=str(me.display_avatar.url), avatar_b=str(them.display_avatar.url))
        file = discord.File(buf, filename="matchup.png")
        await interaction.followup.send(
            content=f"**{me_name}** vs **{them_name}** — position by position",
            file=file)
    except Exception as e:
        await interaction.followup.send(f"Couldn't render the matchup ({e}).", ephemeral=True)


@bot.tree.command(description="Richest managers (budget + squad value).")
async def leaderboard(interaction: discord.Interaction):
    await interaction.response.defer()
    entries = E.leaderboard(interaction.guild_id, 10)
    if not entries:
        await interaction.followup.send("No data yet.", ephemeral=True)
        return
    medals = [EM.e("gold"), EM.e("silver"), EM.e("bronze")] + ["•"] * 7
    # top 3 get thumbnail (the leader)
    top = entries[0]
    top_member = interaction.guild.get_member(top["user_id"])
    lines = []
    for i, en in enumerate(entries):
        member = interaction.guild.get_member(en["user_id"])
        name = member.display_name if member else f"<@{en['user_id']}>"
        team_name = E.get_team_name(interaction.guild_id, en["user_id"]) or name
        team_tag = EM.club_tag(team_name)
        bold = "**" if i < 3 else ""
        lines.append(
            f"{medals[i]} {bold}{team_tag}{bold} — {E.money(en['net_worth'])}"
        )
        if i < 3:
            lines.append(
                f"      _budget {E.money(en['balance'])} · squad {E.money(en['squad_value'])}_"
            )
        if i == 2:
            lines.append("")
    e = discord.Embed(title=f"{EM.e('manager')} Manager Leaderboard",
                      description="\n".join(lines), color=C.AMBER)
    if top_member:
        e.set_thumbnail(url=top_member.display_avatar.url)
    e.set_footer(text="Net Worth = Budget + Squad Value")
    await interaction.followup.send(embed=e)


# ==========================================================================
#  AUCTION CONTROL (admin cadence)
# ==========================================================================
@bot.tree.command(description="[Admin] Set or view the current auction phase (position group).")
@app_commands.describe(group="Which position group to auction now. Omit to just view.")
@app_commands.choices(group=PHASE_CHOICES)
async def phase(interaction: discord.Interaction,
                group: app_commands.Choice[str] = None):
    await interaction.response.defer()
    if not is_admin(interaction.user.id):
        await interaction.followup.send(f"{EM.e('x')} Admins only.", ephemeral=True)
        return
    counts = E.phase_counts(interaction.guild_id)
    if group is None:
        current = db.get_phase(interaction.guild_id)
        lines = [f"**Current phase:** {current}"]
        lines.append("")
        lines.append("**Players still available:**")
        for g in ["ALL"] + P.PHASE_ORDER:
            label = {"ALL": "All", "GK": "GK", "DEF": "DEF", "MID": "MID", "FWD": "FWD", "UNSOLD": "Unsold"}[g]
            lines.append(f"{label}: **{counts[g]}**")
        e = discord.Embed(title="Auction Phase",
                          description="\n".join(lines), color=C.OBSIDIAN)
        await interaction.followup.send(embed=e)
        return

    db.set_phase(interaction.guild_id, group.value)
    avail = counts.get(group.value, 0)
    e = discord.Embed(
        title=f"{EM.e('check')} Phase set",
        description=(f"Auction phase is now **{group.value}**.\n"
                     f"{avail} player(s) available in this phase.\n"
                     f"Use `/next` to drop the top available player, "
                     f"or `/drop` to nominate a specific one."),
        color=C.EMERALD,
    )
    await interaction.followup.send(embed=e)


@bot.tree.command(name="next", description="[Admin] Drop the next player (from the queue if set, else top available).")
async def next_cmd(interaction: discord.Interaction):
    if not is_admin(interaction.user.id):
        await interaction.response.send_message(f"{EM.e('x')} Admins only.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)

    qkey, qcount = E.queue_next(interaction.guild_id)
    if qkey:
        p = P.get(qkey)
        if not p or E.is_sold(interaction.guild_id, qkey):
            E.queue_consume(interaction.guild_id, qkey)
            qkey, qcount = E.queue_next(interaction.guild_id)
            p = P.get(qkey) if qkey else None
        if p:
            remaining = qcount - 1
            await _start_auction(
                interaction, p,
                f"{interaction.user.mention} drops "
                f"**{P.flag(p['country'])} {p['name']}** for auction!  "
                f"_(queued - {remaining} left after this)_"
            )
            return

    # No queue - tell admin to load one
    await interaction.followup.send(
        "No players in the queue. Use `/queue bulk` to add players, "
        "or `/queue load_phase` to load by position.", ephemeral=True)


@bot.tree.command(description="[Admin] Nominate a specific player for auction.")
@app_commands.describe(name="Player to auction (autocompletes, excludes already-sold).")
@app_commands.autocomplete(name=player_autocomplete)
async def drop(interaction: discord.Interaction, name: str):
    if not is_admin(interaction.user.id):
        await interaction.response.send_message(f"{EM.e('x')} Admins only.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    p = P.get(name)
    if not p:
        await interaction.followup.send(f"{EM.e('x')} Player not found.", ephemeral=True)
        return
    await _start_auction(
        interaction, p,
        f"{interaction.user.mention} nominates "
        f"**{P.flag(p['country'])} {p['name']}** for auction!"
    )


@bot.tree.command(description="Browse players still available & drop one from the list.")
async def pool(interaction: discord.Interaction):
    await interaction.response.defer()
    view = PoolView(interaction.guild_id, interaction.channel, interaction.user)
    if not view.players:
        await interaction.followup.send(
            "No players in the queue. Use `/queue bulk` or `/queue load_phase` first.",
            ephemeral=True)
        return
    await interaction.followup.send(embed=view.build_embed(), view=view)


# ==========================================================================
#  Pool browser view
# ==========================================================================
class PoolView(discord.ui.View):
    def __init__(self, guild_id, channel, starter):
        super().__init__(timeout=None)
        self.guild_id = guild_id
        self.channel = channel
        self.starter = starter
        self.page = 0
        self.per_page = 10
        self.phase = "Queue"
        self.players = E.queued_pool(guild_id)
        self.players.sort(key=lambda p: p["ovr"], reverse=True)
        if self.players:
            self.refresh()

    @property
    def pages(self):
        return max(1, (len(self.players) + self.per_page - 1) // self.per_page)

    def page_players(self):
        start = self.page * self.per_page
        return self.players[start:start + self.per_page]

    def refresh(self):
        self.select_auction.options = []
        for p in self.page_players():
            self.select_auction.options.append(discord.SelectOption(
                label=f"{p['name']} ({p.get('club','')})",
                description=f"{p['position']} • {p['ovr']} OVR • {E.money(p['value'])}",
                value=p["key"],
                emoji=P.flag(p["country"]),
            ))

    def build_embed(self):
        if not self.players:
            return discord.Embed(title="Queue empty",
                                 description="No players in the queue.",
                                 color=C.SLATE)
        lines = []
        for i, p in enumerate(self.page_players()):
            rank = self.page * self.per_page + i + 1
            lines.append(
                f"`#{rank:3}` {P.flag(p['country'])} **{p['name']}** "
                f"- {p['position']} - **{p['ovr']}** - {E.money(p['value'])}"
            )
        e = discord.Embed(
            title=f"Auction Pool ({len(self.players)} players)",
            description="\n".join(lines), color=C.OBSIDIAN)
        e.set_footer(text=f"Page {self.page + 1}/{self.pages} - sorted by OVR")
        return e

    @discord.ui.select(placeholder="Pick a player to auction...", row=0)
    async def select_auction(self, interaction: discord.Interaction,
                             select: discord.ui.Select):
        if not is_admin(interaction.user.id):
            await interaction.response.send_message(
                f"{EM.e('x')} Only admins can start auctions.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        if A.is_running(self.guild_id):
            await interaction.followup.send(
                "An auction is already running!", ephemeral=True)
            return
        key = select.values[0]
        p = P.get(key)
        if E.is_sold(self.guild_id, key):
            await interaction.followup.send(
                f"{EM.e('x')} That player has already been sold.", ephemeral=True)
            return
        await interaction.followup.send(
            f"{self.starter.mention} nominates "
            f"**{P.flag(p['country'])} {p['name']}** for auction!")
        a = A.Auction(self.guild_id, interaction.channel, p, self.starter)
        await a.start()

    @discord.ui.button(label="◀ Prev", style=discord.ButtonStyle.secondary, row=1)
    async def prev(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.page > 0:
            self.page -= 1
            self.refresh()
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    @discord.ui.button(label="Next ▶", style=discord.ButtonStyle.secondary, row=1)
    async def next_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.page < self.pages - 1:
            self.page += 1
            self.refresh()
        await interaction.response.edit_message(embed=self.build_embed(), view=self)


# ==========================================================================
#  SALES LOG
# ==========================================================================
@bot.tree.command(description="See the most recent sales in this server.")
async def sold(interaction: discord.Interaction):
    await interaction.response.defer()
    sales = E.recent_sales(interaction.guild_id, 10)
    if not sales:
        await interaction.followup.send("No sales yet.", ephemeral=True)
        return
    lines = []
    for s in sales:
        member = interaction.guild.get_member(s["winner_id"])
        name = member.display_name if member else f"<@{s['winner_id']}>"
        team_name = E.get_team_name(interaction.guild_id, s["winner_id"]) or name
        team_tag = EM.club_tag(team_name)
        lines.append(
            f"{P.flag(s['country'])} **{s['name']}** ({s['ovr']}) → {team_tag} · "
            f"**{E.money(s['price'])}**"
        )
    e = discord.Embed(title="Recent Sales",
                      description="\n".join(lines), color=C.AMBER)
    await interaction.followup.send(embed=e)


# ==========================================================================
#  PLAYER FACES (SoFIFA)
# ==========================================================================
@bot.tree.command(description="[Admin] Set a player's face from a SoFIFA image URL.")
@app_commands.describe(
    name="Player to set the face for.",
    url="SoFIFA image URL, e.g. https://cdn.sofifa.net/players/266/245/26_240.png",
)
@app_commands.autocomplete(name=all_player_autocomplete)
async def setface(interaction: discord.Interaction, name: str, url: str):
    await interaction.response.defer()
    if not is_admin(interaction.user.id):
        await interaction.followup.send(f"{EM.e('x')} Admins only.", ephemeral=True)
        return
    p = P.get(name)
    if not p:
        await interaction.followup.send(f"{EM.e('x')} Player not found.", ephemeral=True)
        return
    if "sofifa.net" not in url and not url.startswith("http"):
        await interaction.followup.send(
            f"{EM.e('x')} That doesn't look like a valid image URL.", ephemeral=True)
        return
    E.set_face_url(name, url)
    await interaction.followup.send(
        f"{EM.e('check')} Face set for **{P.flag(p['country'])} {p['name']}**. "
        f"Use `/team` to see the rendered squad card.")


# ==========================================================================
#  MATCH STATS
# ==========================================================================
@bot.tree.command(description="[Admin] Add match stats to a player (cumulative).")
@app_commands.describe(
    player="Player to update.",
    goals="Goals scored this match.",
    assists="Assists this match.",
    tackles="Tackles this match.",
    saves="Saves this match (GK).",
    motm="Man of the Match? (1=yes, 0=no).",
    yellow="Yellow cards this match.",
    red="Red cards this match.",
)
@app_commands.autocomplete(player=all_player_autocomplete)
async def updatestats(interaction: discord.Interaction, player: str,
                      goals: int = 0, assists: int = 0, tackles: int = 0,
                      saves: int = 0, motm: int = 0, yellow: int = 0, red: int = 0):
    await interaction.response.defer()
    if not is_admin(interaction.user.id):
        await interaction.followup.send("Admins only.", ephemeral=True)
        return
    p = P.get(player)
    if not p:
        await interaction.followup.send("Player not found.", ephemeral=True)
        return
    _s = L.active_season(interaction.guild_id)
    _sid = _s["id"] if _s else None
    E.add_player_stats(interaction.guild_id, player,
                       goals=goals, assists=assists, tackles=tackles,
                       saves=saves, motm=motm, yellow=yellow, red=red,
                       season_id=_sid)
    stat_str = []
    if goals: stat_str.append(f"{EM.e('stat_goals')}{goals}")
    if assists: stat_str.append(f"{EM.e('stat_assists')}{assists}")
    if tackles: stat_str.append(f"{EM.e('stat_tackles')}{tackles}")
    if saves: stat_str.append(f"{EM.e('stat_saves')}{saves}")
    if motm: stat_str.append(f"{EM.e('stat_motm')}MOTM")
    if yellow: stat_str.append(f"{EM.e('stat_yellow')}{yellow}")
    if red: stat_str.append(f"{EM.e('stat_red')}{red}")
    summary = "  ".join(stat_str) if stat_str else "1 appearance"
    total = E.get_player_stats(interaction.guild_id, player, season_id=_sid)
    await interaction.followup.send(
        f"**{p['name']}**  {summary}\n"
        f"Season totals: {EM.e('stat_goals')}{total['goals']} {EM.e('stat_assists')}{total['assists']} "
        f"{EM.e('stat_motm')}{total['motm']} {EM.e('stat_appearances')}{total['matches']} apps")


@bot.tree.command(description="Top scorers and assist leaders across the league.")
async def topscorers(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)
    s = L.active_season(interaction.guild_id)
    sid = s["id"] if s else None
    scorers = E.get_top_scorers(interaction.guild_id, 10, season_id=sid)
    if not scorers:
        await interaction.followup.send("No goals recorded yet.", ephemeral=True)
        return
    try:
        import scorers_card as SCard
        s = L.active_season(interaction.guild_id)
        sub = f"Season {s['number']}" if s else "All Time"
        buf = SCard.render_top_scorers(interaction.guild_id, scorers, subtitle=sub)
        if buf:
            file = discord.File(buf, filename="topscorers.png")
            await interaction.followup.send(
                content="**Golden Boot Race**", file=file)
            return
    except Exception as e:
        print(f"[!] topscorers card render failed: {e}")
    # text fallback
    medals = {1: EM.e("gold"), 2: EM.e("silver"), 3: EM.e("bronze")}
    lines = []
    for i, s in enumerate(scorers, 1):
        p = P.get(s["player_key"])
        if not p:
            continue
        owner = E.get_player_owner(interaction.guild_id, s["player_key"])
        team = owner[1] if owner and owner[1] else p.get("club", "")
        rank = medals.get(i, f"`#{i}`")
        lines.append(
            f"{rank} {P.flag(p['country'])} **{p['name']}** ({team}) "
            f"— **{s['goals']}G** {s['assists']}A {s['motm']}MOTM")
    await interaction.followup.send(
        embed=discord.Embed(title="Top Scorers",
                            description="\n".join(lines), color=C.AMBER))


@bot.tree.command(description="[Admin] Reset all player match stats (new season).")
async def resetstats(interaction: discord.Interaction):
    await interaction.response.defer()
    if not is_admin(interaction.user.id):
        await interaction.followup.send("Admins only.", ephemeral=True)
        return
    E.reset_all_stats(interaction.guild_id)
    await interaction.followup.send("All player match stats have been reset.")


# ==========================================================================
#  Autocomplete helpers
# ==========================================================================
async def my_squad_autocomplete(interaction: discord.Interaction, current: str):
    """Autocomplete: players in the user's OWN squad."""
    squad = E.get_squad(interaction.guild_id, interaction.user.id)
    q = P.slug(current)
    choices = []
    for p in squad:
        if q in p["key"] or not current:
            choices.append(app_commands.Choice(
                name=f"{p['name']} ({p['position']}/{p['ovr']})", value=p["key"]))
        if len(choices) >= 25:
            break
    return choices


@bot.tree.command(description="View a manager's bench players.")
@app_commands.describe(user="Whose bench to view (defaults to you).")
async def bench(interaction: discord.Interaction, user: discord.Member = None):
    await interaction.response.defer(thinking=True)
    target = user or interaction.user
    squad = E.get_squad(interaction.guild_id, target.id)
    if not squad:
        await interaction.followup.send(f"No players yet.", ephemeral=True)
        return
    lineup, _ = E.get_lineup(interaction.guild_id, target.id)
    xi_keys = {p["key"] for _, p in lineup if p}
    team_name = E.get_team_name(interaction.guild_id, target.id) or target.display_name
    try:
        buf = BC.render_bench_card(interaction.guild_id, team_name, target.id, squad, xi_keys)
        file = discord.File(buf, filename="bench.png")
        await interaction.followup.send(content=f"**{team_name}** — Bench", file=file)
    except Exception as e:
        await interaction.followup.send(f"Error: {e}")


# ==========================================================================
#  BUDGET TRACKING & TRADE SYSTEM
# ==========================================================================
@bot.tree.command(description="Shows what positions you still need + budget analysis.")
@app_commands.describe(user="Whose needs to check (defaults to you).")
async def needs(interaction: discord.Interaction, user: discord.Member = None):
    target = user or interaction.user
    data = E.get_needs(interaction.guild_id, target.id)

    await interaction.response.defer()

    labels = {"GK": "GK", "DEF": "DEF", "MID": "MID", "FWD": "FWD"}
    lines = []
    all_complete = True
    for g in P.PHASE_ORDER:
        have = data["counts"][g]
        need = E.REQUIREMENTS[g]
        remaining = data["needed"][g]
        mark = EM.e("check") if remaining == 0 else EM.e("x")
        if remaining > 0:
            all_complete = False
        lines.append(f"{mark} {labels[g]}: **{have}** / {need}"
                     + (f" ({remaining} needed)" if remaining > 0 else ""))

    lines.append("")
    lines.append(f"**Budget:** {E.money(data['budget'])}")
    lines.append(f"**Squad size:** {data['squad_size']} / {E.MIN_SQUAD_SIZE}")

    if data["total_needed"] > 0:
        lines.append("")
        lines.append(f"**Remaining slots:** {data['total_needed']}")
        lines.append(f"**Min cost to fill:** {E.money(data['min_cost'])}")
        if data["max_bid"] < 0:
            lines.append(f"**WARNING:** You don't have enough budget to fill your squad!")
            lines.append(f"   Shortfall: {E.money(abs(data['max_bid']))}")
        else:
            lines.append(f"**Max you can bid next:** {E.money(data['max_bid'])}")
    else:
        lines.append("")
        lines.append(f"{EM.e('check')} **Squad complete!** All position requirements met.")

    color = C.EMERALD if all_complete else C.CRIMSON
    e = discord.Embed(
        title=f"{EM.e('manager')} {target.display_name}'s Needs",
        description="\n".join(lines),
        color=color,
    )
    await interaction.followup.send(embed=e)


@bot.tree.command(description="Offer a trade to another manager.")
@app_commands.describe(
    user="Who you're offering the trade to.",
    give="Player YOU are offering (from your squad).",
    want="Player you WANT from them.",
)
@app_commands.autocomplete(give=my_squad_autocomplete)
@app_commands.autocomplete(want=my_squad_autocomplete)
async def trade(interaction: discord.Interaction, user: discord.Member,
                give: str, want: str):
    await interaction.response.defer()
    if not db.trades_enabled(interaction.guild_id):
        await interaction.followup.send("Trades are currently disabled by the admin.", ephemeral=True)
        return
    if user.id == interaction.user.id:
        await interaction.followup.send(f"{EM.e('x')} Can't trade with yourself.", ephemeral=True)
        return

    if not E.owns(interaction.guild_id, interaction.user.id, give):
        await interaction.followup.send(f"{EM.e('x')} You don't own that player.", ephemeral=True)
        return
    if not E.owns(interaction.guild_id, user.id, want):
        await interaction.followup.send(f"{EM.e('x')} {user.display_name} doesn't own that player.", ephemeral=True)
        return

    p_give = P.get(give)
    p_want = P.get(want)

    trade_id = E.create_trade(interaction.guild_id, interaction.user.id, user.id, [give], [want])
    await interaction.followup.send(
        f"**Trade offer #{trade_id}** sent to {user.mention}!\n\n"
        f"**You offer:** {p_give['name']} ({p_give['ovr']}) -> {p_give['position']}\n"
        f"**You want:** {p_want['name']} ({p_want['ovr']}) -> {p_want['position']}\n\n"
        f"{user.mention}, use `/accepttrade {trade_id}` or `/rejecttrade {trade_id}`"
    )


@bot.tree.command(description="Accept a trade offer.")
@app_commands.describe(trade_id="The trade offer ID to accept.")
async def accepttrade(interaction: discord.Interaction, trade_id: int):
    trade = E.get_trade(interaction.guild_id, trade_id)
    await interaction.response.defer()
    if not trade:
        await interaction.followup.send(f"{EM.e('x')} Trade not found.", ephemeral=True)
        return
    if trade["to_user"] != interaction.user.id:
        await interaction.followup.send(f"{EM.e('x')} This trade isn't for you.", ephemeral=True)
        return
    if trade["status"] != "pending":
        await interaction.followup.send(f"{EM.e('x')} This trade is no longer pending.", ephemeral=True)
        return

    give_keys = [k for k in trade["offering"].split(",") if k]
    want_keys = [k for k in trade["requesting"].split(",") if k]

    for key in give_keys:
        if not E.owns(interaction.guild_id, trade["from_user"], key):
            await interaction.followup.send(f"{EM.e('x')} Offered player no longer owned by sender.", ephemeral=True)
            return
    for key in want_keys:
        if not E.owns(interaction.guild_id, trade["to_user"], key):
            await interaction.followup.send(f"{EM.e('x')} Requested player no longer owned by you.", ephemeral=True)
            return

    success = E.execute_trade(interaction.guild_id, trade_id)
    if success:
        from_member = interaction.guild.get_member(trade["from_user"])
        from_name = from_member.display_name if from_member else f"<@{trade['from_user']}>"
        give_names = [P.get(k)["name"] if P.get(k) else k for k in give_keys]
        want_names = [P.get(k)["name"] if P.get(k) else k for k in want_keys]
        await interaction.followup.send(
            f"{EM.e('check')} **Trade #{trade_id} accepted!**\n\n"
            f"{from_name} -> {interaction.user.mention}: {', '.join(want_names)}\n"
            f"{interaction.user.mention} -> {from_name}: {', '.join(give_names)}"
        )
    else:
        await interaction.followup.send(f"{EM.e('x')} Trade execution failed.", ephemeral=True)


@bot.tree.command(description="Reject a trade offer.")
@app_commands.describe(trade_id="The trade offer ID to reject.")
async def rejecttrade(interaction: discord.Interaction, trade_id: int):
    trade = E.get_trade(interaction.guild_id, trade_id)
    await interaction.response.defer()
    if not trade:
        await interaction.followup.send(f"{EM.e('x')} Trade not found.", ephemeral=True)
        return
    if trade["to_user"] != interaction.user.id:
        await interaction.followup.send(f"{EM.e('x')} This trade isn't for you.", ephemeral=True)
        return
    E.update_trade_status(interaction.guild_id, trade_id, "rejected")
    await interaction.followup.send(f"Trade #{trade_id} rejected.")


@bot.tree.command(description="[Admin] Enable or disable player trades.")
@app_commands.describe(enabled="True to allow trades, False to block them.")
async def toggletrades(interaction: discord.Interaction, enabled: bool):
    await interaction.response.defer()
    if not is_admin(interaction.user.id):
        await interaction.followup.send("Admins only.", ephemeral=True)
        return
    db.set_trades_enabled(interaction.guild_id, enabled)
    status = "enabled" if enabled else "disabled"
    await interaction.followup.send(f"Trades are now **{status}**.")


@bot.tree.command(description="See your pending trade offers.")
async def trades(interaction: discord.Interaction):
    pending = E.get_pending_trades(interaction.guild_id, interaction.user.id)
    await interaction.response.defer()
    if not pending:
        await interaction.followup.send("No pending trade offers.", ephemeral=True)
        return
    lines = []
    for t in pending:
        from_member = interaction.guild.get_member(t["from_user"])
        from_name = from_member.display_name if from_member else f"<@{t['from_user']}>"
        from_team = E.get_team_name(interaction.guild_id, t["from_user"]) or from_name
        from_tag = EM.club_tag(from_team)
        give_keys = [k for k in t["offering"].split(",") if k]
        want_keys = [k for k in t["requesting"].split(",") if k]
        give_str = ", ".join(
            f"**{P.get(k)['ovr']}** {P.get(k)['name']}"
            if P.get(k) else k for k in give_keys
        )
        want_str = ", ".join(
            f"**{P.get(k)['ovr']}** {P.get(k)['name']}"
            if P.get(k) else k for k in want_keys
        )
        lines.append(
            f"**Trade #{t['id']}** from {from_tag}\n"
            f"  Offers: {give_str}\n"
            f"  Wants: {want_str}\n"
            f"  `/accepttrade {t['id']}` · `/rejecttrade {t['id']}`"
        )
    e = discord.Embed(title=f"Pending Trades ({len(pending)})",
                      description="\n".join(lines), color=C.AMBER)
    await interaction.followup.send(embed=e, ephemeral=True)


@bot.tree.command(description="[Admin] Export FL26 setup guide with all teams, rosters & lineups.")
async def exportfl26(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)
    if not is_admin(interaction.user.id):
        await interaction.followup.send(f"{EM.e('x')} Admins only.", ephemeral=True)
        return
    try:
        guide_text = E.export_fl26_guide(interaction.guild_id)
        import io
        buf = io.BytesIO(guide_text.encode("utf-8"))
        file = discord.File(buf, filename="fl26_setup_guide.csv")
        await interaction.followup.send(
            "**FL26 Setup Guide**\n\n"
            "This file contains:\n"
            "- All custom teams to create (names, formations)\n"
            "- Player assignments (PES IDs -> team slots)\n"
            "- Starting lineups for each team\n\n"
            "**How to use it in FL26:**\n"
            "1. Edit Mode -> Create custom teams\n"
            "2. Transfer players to the custom teams\n"
            "3. Set formations and starting lineups\n"
            "4. Save and start your sim!",
            file=file)
    except Exception as e:
        await interaction.followup.send(f"{EM.e('x')} Export failed: {e}", ephemeral=True)


# ==========================================================================
#  FORMATIONS & LINEUP
# ==========================================================================
import formations as FM

FORMATION_CHOICES = [
    app_commands.Choice(name=f"{f} — {FM.FORMATIONS[f]['desc']}", value=f)
    for f in FM.FORMATION_NAMES
]


@bot.tree.command(description="Set your formation (4-3-3, 4-4-2, 3-5-2, etc.)")
@app_commands.describe(formation="Pick a formation.")
@app_commands.choices(formation=FORMATION_CHOICES)
async def formation(interaction: discord.Interaction,
                    formation: app_commands.Choice[str]):
    await interaction.response.defer()
    E.set_formation(interaction.guild_id, interaction.user.id, formation.value)
    fmt = FM.get_formation(formation.value)
    n_slots = sum(len(r["slots"]) for r in fmt["rows"])
    await interaction.followup.send(
        f"{EM.e('check')} Formation set to **{formation.value}** ({n_slots} slots).\n"
        f"_{fmt['desc']}_\n"
        f"Use `/lineup` to view or `/setpos` to manually assign players to slots.",
    )



async def slot_autocomplete(interaction: discord.Interaction, current: str):
    fmt_name = E.get_formation(interaction.guild_id, interaction.user.id)
    fmt = FM.get_formation(fmt_name)
    slots = FM.all_slots(fmt)
    choices = []
    for s in slots:
        label = f"Slot {s['index']}: {s['pos']} ({s['group']})"
        if current.lower() in label.lower() or not current:
            choices.append(app_commands.Choice(name=label, value=str(s["index"])))
        if len(choices) >= 25:
            break
    return choices


@bot.tree.command(description="Manually assign a player to a formation slot.")
@app_commands.describe(
    slot="Which slot to fill (use /lineup to see slot numbers).",
    player_name="Which of YOUR players to put there.",
)
@app_commands.autocomplete(slot=slot_autocomplete)
@app_commands.autocomplete(player_name=my_squad_autocomplete)
async def setpos(interaction: discord.Interaction, slot: str, player_name: str):
    try:
        await interaction.response.defer()
        slot_idx = int(slot)
    except ValueError:
        await interaction.followup.send(f"{EM.e('x')} Invalid slot number.", ephemeral=True)
        return

    if not E.owns(interaction.guild_id, interaction.user.id, player_name):
        await interaction.followup.send(f"{EM.e('x')} You don't own that player.", ephemeral=True)
        return

    p = P.get(player_name)
    if not p:
        await interaction.followup.send(f"{EM.e('x')} Player not found.", ephemeral=True)
        return

    E.set_lineup_slot(interaction.guild_id, interaction.user.id, slot_idx, player_name)
    await interaction.followup.send(
        f"{EM.e('check')} **{P.flag(p['country'])} {p['name']}** ({p['position']}/{p['ovr']}) "
        f"assigned to slot {slot_idx}.\n"
        f"Use `/team` to see the rendered card.")


@bot.tree.command(description="Reset a slot to auto-assignment.")
@app_commands.describe(slot="Which slot to reset to auto.")
@app_commands.autocomplete(slot=slot_autocomplete)
async def clearpos(interaction: discord.Interaction, slot: str):
    try:
        await interaction.response.defer()
        slot_idx = int(slot)
    except ValueError:
        await interaction.followup.send(f"{EM.e('x')} Invalid slot number.", ephemeral=True)
        return
    E.clear_lineup_slot(interaction.guild_id, interaction.user.id, slot_idx)
    await interaction.followup.send(
        f"{EM.e('check')} Slot {slot_idx} reset to auto-assignment.")


@bot.tree.command(description="Reset all lineup overrides to auto.")
async def resetlineup(interaction: discord.Interaction):
    E.clear_all_overrides(interaction.guild_id, interaction.user.id)
    await interaction.response.defer()
    await interaction.followup.send(
        f"{EM.e('check')} All positions reset to auto-assignment.")


# ==========================================================================
#  TACTICS  (/tactics) — FL26 attacking/defensive/advanced instructions
# ==========================================================================
import tactics as T

@bot.tree.command(description="View or set your FL26 match tactics.")
@app_commands.describe(user="Whose tactics to view (defaults to you).")
async def tactics(interaction: discord.Interaction, user: discord.Member = None):
    target = user or interaction.user
    await interaction.response.defer()
    t = E.get_tactics(interaction.guild_id, target.id)
    fmt_name = E.get_formation(interaction.guild_id, target.id)
    fmt_label = FM.formation_label(fmt_name)

    e = discord.Embed(
        title=f"{EM.e('manager')} {target.display_name} — Tactics",
        description=f"Formation: **{fmt_label}**",
        color=C.OBSIDIAN,
    )

    # Attacking
    e.add_field(name="ATTACKING", value=(
        f"Style: **{T.label(T.ATTACK_STYLE, t['attacking_style'])}**\n"
        f"Build-up: **{T.label(T.BUILD_UP, t['build_up'])}**\n"
        f"Attacking Area: **{T.label(T.ATTACK_AREA, t['attacking_area'])}**\n"
        f"Positioning: **{T.label(T.POSITIONING, t['positioning'])}**\n"
        f"Support Range: **{t['support_range']}/10**"
    ), inline=True)

    # Defensive
    e.add_field(name="DEFENSIVE", value=(
        f"Style: **{T.label(T.DEFENSIVE_STYLE, t['defensive_style'])}**\n"
        f"Containment: **{T.label(T.CONTAINMENT_AREA, t['containment_area'])}**\n"
        f"Pressuring: **{T.label(T.PRESSURING, t['pressuring'])}**\n"
        f"Defensive Line: **{t['defensive_line']}/10**\n"
        f"Compactness: **{t['compactness']}/10**"
    ), inline=True)

    # Advanced
    adv_lines = []
    for slot, group, label_prefix in [
        ("adv_attack_1", T.ADV_ATTACK, "Attacking 1"),
        ("adv_attack_2", T.ADV_ATTACK, "Attacking 2"),
        ("adv_defence_1", T.ADV_DEFENCE, "Defence 1"),
        ("adv_defence_2", T.ADV_DEFENCE, "Defence 2"),
    ]:
        val = t[slot]
        if val == "off":
            adv_lines.append(f"{label_prefix}: _Off_")
        else:
            adv_lines.append(f"{label_prefix}: **{T.label(group, val)}**")
    e.add_field(name="ADVANCED", value="\n".join(adv_lines), inline=False)

    e.set_footer(text="Set your full tactics on the website dashboard → your squad page.")
    e.set_thumbnail(url=target.display_avatar.url)
    await interaction.followup.send(embed=e)


# ==========================================================================
#  ADMIN
# ==========================================================================
@bot.tree.command(description="[Admin] Give coins to a user.")
@app_commands.describe(user="Recipient", amount="Amount in coins")
async def give(interaction: discord.Interaction, user: discord.Member, amount: int):
    await interaction.response.defer()
    if not is_admin(interaction.user.id):
        await interaction.followup.send(f"{EM.e('x')} Admins only.", ephemeral=True)
        return
    E.adjust_balance(interaction.guild_id, user.id, amount)
    await interaction.followup.send(
        f"{EM.e('check')} Gave {E.money(amount)} to {user.mention}. "
        f"New budget: {E.money(E.get_balance(interaction.guild_id, user.id))}")


@bot.tree.command(description="[Admin] Reset a user's budget & squad.")
@app_commands.describe(user="User to reset")
async def reset(interaction: discord.Interaction, user: discord.Member):
    await interaction.response.defer()
    if not is_admin(interaction.user.id):
        await interaction.followup.send(f"{EM.e('x')} Admins only.", ephemeral=True)
        return
    with db.cursor() as c:
        c.execute("DELETE FROM squads WHERE guild_id=? AND user_id=?",
                  (interaction.guild_id, user.id))
        c.execute("DELETE FROM users WHERE guild_id=? AND user_id=?",
                  (interaction.guild_id, user.id))
    E.ensure_user(interaction.guild_id, user.id)
    await interaction.followup.send(
        f"Reset {user.mention}. Budget: {E.money(Config.STARTING_BALANCE)}.")


@bot.tree.command(description="[Admin] Reset ALL managers' budgets, squads, and lineups.")
async def resetall(interaction: discord.Interaction):
    await interaction.response.defer()
    if not is_admin(interaction.user.id):
        await interaction.followup.send(f"{EM.e('x')} Admins only.", ephemeral=True)
        return
    with db.cursor() as c:
        c.execute("DELETE FROM squads WHERE guild_id=?", (interaction.guild_id,))
        c.execute("DELETE FROM users WHERE guild_id=?", (interaction.guild_id,))
        c.execute("DELETE FROM lineup_overrides WHERE guild_id=?", (interaction.guild_id,))
        c.execute("DELETE FROM formations WHERE guild_id=?", (interaction.guild_id,))
    await interaction.followup.send(
        f"{EM.e('check')} **All managers reset.** Everyone's budget, squad, formation, and lineup have been cleared. "
        f"All players are back in the pool.")


@bot.tree.command(description="[Admin] Cancel the auction currently running.")
async def cancel(interaction: discord.Interaction):
    await interaction.response.defer()
    if not is_admin(interaction.user.id):
        await interaction.followup.send(f"{EM.e('x')} Admins only.", ephemeral=True)
        return
    a = A.ACTIVE.get(interaction.guild_id)
    if not a:
        await interaction.followup.send("No active auction.", ephemeral=True)
        return
    a.status = "VOID"
    if a._task:
        a._task.cancel()
    A.ACTIVE.pop(interaction.guild_id, None)
    await interaction.followup.send("Auction cancelled.")


# ==========================================================================
#  SCRIPTED DRAFT QUEUE
# ==========================================================================
@bot.tree.command(description="[Admin] Build a scripted auction queue (auto-drops from this list).")
@app_commands.describe(
    action="What to do with the queue.",
    name="Player name (for 'add') OR comma-separated names (for 'bulk').",
    phase="Phase to load (for 'load phase').",
)
@app_commands.choices(action=[
    app_commands.Choice(name="List the queue", value="list"),
    app_commands.Choice(name="Add a player", value="add"),
    app_commands.Choice(name="Add bulk (paste comma-separated names)", value="bulk"),
    app_commands.Choice(name="Shuffle the queue (randomize order)", value="shuffle"),
    app_commands.Choice(name="Clear the queue", value="clear"),
    app_commands.Choice(name="Load phase into queue", value="load_phase"),
])
@app_commands.choices(phase=[
    app_commands.Choice(name="All positions", value="ALL"),
    app_commands.Choice(name="Goalkeepers", value="GK"),
    app_commands.Choice(name="Defenders", value="DEF"),
    app_commands.Choice(name="Midfielders", value="MID"),
    app_commands.Choice(name="Forwards", value="FWD"),
])
async def queue(interaction: discord.Interaction,
                action: app_commands.Choice[str],
                name: str = None,
                phase: app_commands.Choice[str] = None):
    if not is_admin(interaction.user.id):
        await interaction.response.send_message(f"{EM.e('x')} Admins only.", ephemeral=True)
        return
    await interaction.response.defer()
    act = action.value

    if act == "list":
        keys = E.queue_list(interaction.guild_id)
        if not keys:
            await interaction.followup.send(
                "The queue is empty. Use `/queue add <player>` or "
                "`/queue load_current_phase`.", ephemeral=True)
            return
        lines = []
        for i, k in enumerate(keys, 1):
            p = P.get(k)
            tag = " _(SOLD)_" if p and E.is_sold(interaction.guild_id, k) else ""
            lines.append(f"`{i:2}` {P.flag(p['country'])} {p['name']} ({p['ovr']}){tag}"
                         if p else f"`{i:2}` {k} _(unknown)_")
        e = discord.Embed(title="Scripted Auction Queue",
                          description="\n".join(lines), color=C.SLATE)
        e.set_footer(text=f"{len(keys)} players queued • `/next` drops #1")
        await interaction.followup.send(embed=e)
        return

    if act == "add":
        if not name:
            await interaction.followup.send("Specify a player to add.", ephemeral=True)
            return
        results = P.search(name, limit=1)
        if not results:
            await interaction.followup.send(f"{EM.e('x')} Player not found.", ephemeral=True)
            return
        p = results[0]
        if E.is_sold(interaction.guild_id, p["key"]):
            await interaction.followup.send(
                f"{EM.e('x')} {p['name']} is already sold.", ephemeral=True)
            return
        pos = E.queue_add(interaction.guild_id, p["key"])
        await interaction.followup.send(
            f"{EM.e('check')} Added **{P.flag(p['country'])} {p['name']}** to the queue (position #{pos}).")
        return

    if act == "clear":
        E.queue_clear(interaction.guild_id)
        await interaction.followup.send("Queue cleared.")
        return

    if act == "bulk":
        if not name:
            await interaction.followup.send(
                "Enter player names separated by commas.", ephemeral=True)
            return
        names = [n.strip() for n in name.split(",") if n.strip()]
        added_keys = []
        not_found = []
        for n in names:
            results = P.search(n, limit=1)
            if results and not E.is_sold(interaction.guild_id, results[0]["key"]):
                added_keys.append(results[0]["key"])
            else:
                not_found.append(n)
        count = E.queue_add_many(interaction.guild_id, added_keys)
        msg = f"Added **{count}** players to the queue."
        if not_found:
            msg += f"\nCouldn't find: {', '.join(not_found[:10])}"
            if len(not_found) > 10:
                msg += f" (+{len(not_found)-10} more)"
        await interaction.followup.send(msg)
        return

    if act == "shuffle":
        count = E.queue_shuffle(interaction.guild_id)
        if count:
            await interaction.followup.send(
                f"Shuffled **{count}** players in the queue. Use `/next` to drop them in random order.")
        else:
            await interaction.followup.send(
                "Queue is empty or has only 1 player.", ephemeral=True)
        return

    if act == "load_phase":
        # Use the phase dropdown if provided, else fall back to the global phase
        load_phase_val = phase.value if phase else db.get_phase(interaction.guild_id)
        offered = A.offered_keys(interaction.guild_id)
        pool = E.remaining_pool(interaction.guild_id, phase=load_phase_val, exclude=offered)
        added = E.queue_add_many(interaction.guild_id, [p["key"] for p in pool])
        await interaction.followup.send(
            f"{EM.e('check')} Loaded **{added}** available **{load_phase_val}** players "
            f"into the queue.\nUse `/next` to drop them in order, or `/queue shuffle` to randomize.")
        return


@bot.tree.command(name="queueorder", description="[Admin] View the exact drop order of the queue (private).")
async def queueorder(interaction: discord.Interaction):
    if not is_admin(interaction.user.id):
        await interaction.response.send_message(f"{EM.e('x')} Admins only.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    qpool = E.queued_pool(interaction.guild_id)
    if not qpool:
        await interaction.followup.send("Queue is empty.", ephemeral=True)
        return
    lines = []
    for i, p in enumerate(qpool, 1):
        lines.append(f"`#{i:3}` {P.flag(p['country'])} **{p['name']}** - {p['position']} - **{p['ovr']}**")
    # chunk into embeds (max ~30 per embed field)
    per = 30
    e = discord.Embed(title="Drop Order (Private)", color=C.OBSIDIAN)
    for start in range(0, len(lines), per):
        chunk = lines[start:start+per]
        e.add_field(name=f"#{start+1}-{start+len(chunk)}", value="\n".join(chunk), inline=False)
    e.set_footer(text=f"{len(qpool)} players in queue - only you can see this")
    await interaction.followup.send(embed=e, ephemeral=True)


# ==========================================================================
#  CSV EXPORT
# ==========================================================================
@bot.tree.command(description="[Admin] Export all squads as a CSV file (for Football Life etc.).")
async def export(interaction: discord.Interaction):
    await interaction.response.defer()
    if not is_admin(interaction.user.id):
        await interaction.followup.send(f"{EM.e('x')} Admins only.", ephemeral=True)
        return
    csv_text = E.export_csv(interaction.guild_id)
    if csv_text.strip().count("\n") < 1:
        await interaction.followup.send("No squads to export yet.", ephemeral=True)
        return
    import io
    buf = io.BytesIO(csv_text.encode("utf-8"))
    file = discord.File(buf, filename="squads.csv")
    await interaction.followup.send(
        "Here's the full squad export (one row per player).", file=file)


# ==========================================================================
#  SQUAD REQUIREMENTS
# ==========================================================================
REQUIREMENTS = {"GK": 2, "DEF": 5, "MID": 5, "FWD": 3}
MIN_SQUAD_SIZE = sum(REQUIREMENTS.values())  # 15


def _requirements_lines(guild_id: int, user_id: int):
    squad = E.get_squad(guild_id, user_id)
    counts = {"GK": 0, "DEF": 0, "MID": 0, "FWD": 0}
    for p in squad:
        counts[p["group"]] += 1
    labels = {"GK": "GK", "DEF": "DEF", "MID": "MID", "FWD": "FWD"}
    lines, all_ok = [], True
    for g in P.PHASE_ORDER:
        have, need = counts[g], REQUIREMENTS[g]
        ok = have >= need
        all_ok = all_ok and ok
        mark = EM.e("check") if ok else EM.e("x")
        lines.append(f"{mark} {labels[g]}: **{have}** / {need} required")
    size_ok = len(squad) >= MIN_SQUAD_SIZE
    all_ok = all_ok and size_ok
    _mark = EM.e("check") if size_ok else EM.e("x")
    lines.append(f"{_mark} Total: **{len(squad)}** / {MIN_SQUAD_SIZE}")
    return lines, all_ok, len(squad)


@bot.tree.command(description="Check if a squad meets the minimum requirements.")
@app_commands.describe(user="Whose squad to check (defaults to you).")
async def check(interaction: discord.Interaction, user: discord.Member = None):
    target = user or interaction.user
    lines, all_ok, size = _requirements_lines(interaction.guild_id, target.id)
    await interaction.response.defer()
    color = C.EMERALD if all_ok else C.CRIMSON
    _ctitle = EM.e("check") + " Squad complete!" if all_ok else "Squad incomplete"
    title = f"{_ctitle} — {target.display_name}"
    e = discord.Embed(title=title, description="\n".join(lines), color=color)
    bal = E.get_balance(interaction.guild_id, target.id)
    e.add_field(name="Budget left", value=E.money(bal), inline=True)
    e.set_footer(text="Requirements are configurable — see REQUIREMENTS in the code.")
    await interaction.followup.send(embed=e)


# ==========================================================================
#  LEAGUE / SEASON  (/season + /fixtures + /result + /table + /bracket)
# ==========================================================================
LEAGUE_FORMAT_CHOICES = [
    app_commands.Choice(name="Single Round-Robin (everyone once)", value="round_robin"),
    app_commands.Choice(name="Double Round-Robin (home & away)", value="double_rr"),
    app_commands.Choice(name="Groups + Knockout (World Cup style)", value="groups_ko"),
    app_commands.Choice(name="League + Playoffs (top N into brackets)", value="league_playoff"),
    app_commands.Choice(name="Pure Knockout (single-elimination bracket)", value="knockout"),
]


def _team_name(season_id: int, user_id: int, member=None) -> str:
    tn = L.team_name_of(season_id, user_id)
    if tn:
        return tn
    if member:
        return member.display_name
    if user_id >= 900_000_000:
        return f"Test Team {user_id - 899_999_999}"
    return f"<@{user_id}>"


def _team_tag(season_id: int, user_id: int, member=None) -> str:
    """Team name + club emoji (for embeds that show fixture teams)."""
    return EM.club_tag(_team_name(season_id, user_id, member))


# ==========================================================================
#  SEASON COMMAND — subcommands: /season setup, /season add, etc.
#  Each subcommand shows ONLY its relevant parameters (no clutter).
# ==========================================================================
season_group = app_commands.Group(name="season", description="Manage the league season")

# Explicitly register with the command tree so it's synced
# (standalone Groups may not be auto-detected by copy_global_to)
try:
    bot.tree.add_command(season_group)
except discord.app_commands.errors.CommandAlreadyRegistered:
    pass  # already registered, that's fine


@season_group.command(name="setup", description="Create a new season")
@app_commands.choices(fmt=LEAGUE_FORMAT_CHOICES)
@app_commands.describe(fmt="Competition format for this season")
async def season_setup(interaction: discord.Interaction,
                       fmt: app_commands.Choice[str]):
    await interaction.response.defer(ephemeral=True)
    if not is_admin(interaction.user.id):
        await interaction.followup.send(f"{EM.e('x')} Admins only.", ephemeral=True)
        return
    guild_id = interaction.guild_id
    existing = L.active_season(guild_id)
    if existing and existing["status"] == "active":
        await interaction.followup.send(
            f"{EM.e('x')} Season #{existing['number']} is already active. End it first with `/season end`.",
            ephemeral=True)
        return
    num = L.next_season_number(guild_id)
    sid = L.create_season(guild_id, fmt.value, number=num)
    await interaction.followup.send(
        f"**Season {num}** created ({fmt.value}).\n"
        f"Status: **setup**. Now add teams with `/season add`.\n"
        f"When ready, `/season start` generates all fixtures.", ephemeral=True)


@season_group.command(name="add", description="Add a manager to the season (team assigned in the draw)")
@app_commands.describe(user="The manager to add")
async def season_add(interaction: discord.Interaction,
                     user: discord.Member):
    await interaction.response.defer()
    if not is_admin(interaction.user.id):
        await interaction.followup.send(f"{EM.e('x')} Admins only.", ephemeral=True)
        return
    guild_id = interaction.guild_id
    s = L.active_season(guild_id)
    if not s:
        await interaction.followup.send(
            f"{EM.e('x')} No active season. Create one first with `/season setup`.",
            ephemeral=True)
        return
    E.ensure_user(guild_id, user.id)
    seed = L.add_team_auto_seed(s["id"], user.id, team_name=None)
    n = len(L.teams(s["id"]))
    await interaction.followup.send(
        f"{user.mention} added to Season {s['number']} as seed #{seed}.\n"
        f"{n} manager(s) registered. Team will be assigned in the draw (`/season draw`).")


@season_group.command(name="remove", description="Remove a team from the season")
@app_commands.describe(user="The manager to remove")
async def season_remove(interaction: discord.Interaction,
                        user: discord.Member):
    await interaction.response.defer()
    if not is_admin(interaction.user.id):
        await interaction.followup.send(f"{EM.e('x')} Admins only.", ephemeral=True)
        return
    guild_id = interaction.guild_id
    s = L.active_season(guild_id)
    if not s:
        await interaction.followup.send(f"{EM.e('x')} No active season.", ephemeral=True)
        return
    L.remove_team(s["id"], user.id)
    n = len(L.teams(s["id"]))
    await interaction.followup.send(
        f"Removed {user.mention} from Season {s['number']}. {n} team(s) remain.")


@season_group.command(name="signup", description="Add managers who reacted to a message (gives role + adds to season)")
@app_commands.describe(
    message_id="The message ID to check reactions on",
    emoji="The emoji to look for (type it or paste the custom emoji)",
    role="The role to give everyone who reacted",
    channel="Channel containing the message (defaults to this channel)",
)
async def season_signup(interaction: discord.Interaction,
                        message_id: str,
                        emoji: str,
                        role: discord.Role,
                        channel: discord.TextChannel = None):
    await interaction.response.defer()
    if not is_admin(interaction.user.id):
        await interaction.followup.send(f"{EM.e('x')} Admins only.", ephemeral=True)
        return

    guild_id = interaction.guild_id
    s = L.active_season(guild_id)
    if not s:
        await interaction.followup.send(
            f"{EM.e('x')} No active season. Create one first with `/season setup`.",
            ephemeral=True)
        return

    # Resolve the target channel
    target_channel = channel or interaction.channel

    # Parse message ID
    try:
        msg_id = int(message_id)
    except ValueError:
        await interaction.followup.send(f"{EM.e('x')} Invalid message ID.", ephemeral=True)
        return

    # Fetch the message
    try:
        message = await target_channel.fetch_message(msg_id)
    except discord.NotFound:
        await interaction.followup.send(
            f"{EM.e('x')} Message not found in {target_channel.mention}.",
            ephemeral=True)
        return
    except discord.Forbidden:
        await interaction.followup.send(
            f"{EM.e('x')} I can't read messages there. Give me Read Message History permission.",
            ephemeral=True)
        return

    # Find the reaction matching the emoji
    target_reaction = None
    for reaction in message.reactions:
        re_str = str(reaction.emoji)
        # Match: exact unicode, custom emoji ID match, or substring
        if re_str == emoji or emoji in re_str or emoji.endswith(str(reaction.emoji.id if hasattr(reaction.emoji, 'id') and reaction.emoji.id else '')):
            target_reaction = reaction
            break

    if not target_reaction:
        await interaction.followup.send(
            f"{EM.e('x')} No reaction with {emoji} found on that message. "
            f"Available: {', '.join(str(r.emoji) for r in message.reactions[:10])}",
            ephemeral=True)
        return

    # Get all users who reacted
    try:
        users = [u async for u in target_reaction.users()]
    except Exception as ex:
        await interaction.followup.send(f"{EM.e('x')} Couldn't fetch reaction users: {ex}", ephemeral=True)
        return

    # Filter out bots
    users = [u for u in users if not u.bot]

    if not users:
        await interaction.followup.send(
            f"{EM.e('x')} No real users reacted with {emoji}.",
            ephemeral=True)
        return

    # Assign role + add to season
    role_failures = 0
    added_to_season = 0
    already_in_season = 0
    existing_teams = {t["user_id"] for t in L.teams(s["id"])}

    for user in users:
        # Get member object
        member = interaction.guild.get_member(user.id)
        if not member:
            try:
                member = await interaction.guild.fetch_member(user.id)
            except Exception:
                continue

        # Add role
        try:
            if role not in member.roles:
                await member.add_roles(role, reason="Season signup reaction")
        except discord.Forbidden:
            role_failures += 1
        except Exception:
            role_failures += 1

        # Add to season
        E.ensure_user(guild_id, user.id)
        if user.id in existing_teams:
            already_in_season += 1
            continue
        L.add_team_auto_seed(s["id"], user.id, team_name=None)
        existing_teams.add(user.id)
        added_to_season += 1

    total_managers = len(L.teams(s["id"]))
    lines = [
        f"{EM.e('check')} **Reaction signup done!**",
        f"Found **{len(users)}** user(s) who reacted with {emoji}",
        f"Role **{role.name}** assigned" + (f" ({role_failures} failed - check my permissions)" if role_failures else ""),
        f"**{added_to_season}** new manager(s) added to Season {s['number']}",
    ]
    if already_in_season:
        lines.append(f"({already_in_season} were already in)")
    lines.append(f"**{total_managers}** manager(s) total now - run `/season draw` to assign teams")

    await interaction.followup.send("\n".join(lines))


@season_group.command(name="teams", description="List all teams in the season")
async def season_teams(interaction: discord.Interaction):
    await interaction.response.defer()
    if not is_admin(interaction.user.id):
        await interaction.followup.send(f"{EM.e('x')} Admins only.", ephemeral=True)
        return
    s = L.active_season(interaction.guild_id)
    if not s:
        await interaction.followup.send(f"{EM.e('x')} No active season.", ephemeral=True)
        return
    tms = L.teams(s["id"])
    if not tms:
        await interaction.followup.send("No teams yet. Use `/season add`.", ephemeral=True)
        return
    lines = []
    for t in tms:
        member = interaction.guild.get_member(t["user_id"])
        mname = member.display_name if member else f"<@{t['user_id']}>"
        grp = f" [Group {t['group_label']}]" if t["group_label"] else ""
        tname = EM.club_tag(t["team_name"] or mname)
        lines.append(f"`#{t['seed']:2}` {tname} ({mname}){grp}")
    e = discord.Embed(
        title=f"Season {s['number']} — Teams ({len(tms)})",
        description="\n".join(lines),
        color=C.OBSIDIAN)
    e.set_footer(text=f"Format: {s['format']} . Status: {s['status']}")
    await interaction.followup.send(embed=e)


# ==========================================================================
#  DRAW CEREMONY (/season draw)
# ==========================================================================

# The pool of clubs that get randomly assigned. Edit this list freely.
DRAW_CLUBS = [
    "Real Madrid", "Manchester City", "Bayern Munich", "Liverpool",
    "Barcelona", "Inter Milan", "Atletico Madrid", "AC Milan",
    "Chelsea", "Arsenal", "Juventus", "Napoli",
    "Tottenham Hotspur", "Manchester United", "Borussia Dortmund", "Paris Saint-Germain",
    "Atalanta", "AS Roma", "Bayer Leverkusen", "Sevilla",
    "RB Leipzig", "Lazio", "Benfica", "Porto",
    "Ajax", "PSV Eindhoven", "Sporting CP", "Olympiacos",
    "Shakhtar Donetsk", "Celtic", "Rangers", "Galatasaray",
]


class DrawView(discord.ui.View):
    """Interactive team draw. Each button click reveals one manager's team."""

    def __init__(self, guild_id, season_id, season_number, guild=None):
        super().__init__(timeout=600)
        self.guild_id = guild_id
        self.season_id = season_id
        self.season_number = season_number
        # store the guild object for member lookups during _build_embed
        self._guild = guild

    def _build_embed(self):
        tms = L.teams(self.season_id)
        undrawn_ids = {m["user_id"] for m in L.undrawn_managers(self.season_id)}
        drawn_count = len(tms) - len(undrawn_ids)
        clubs_left = len(DRAW_CLUBS) - drawn_count

        e = discord.Embed(
            title=f"Season {self.season_number} - Draw Ceremony",
            color=C.AMBER,
        )

        lines = []
        for t in tms:
            member = self._member(t["user_id"])
            if t["team_name"]:
                tag = EM.club_tag(t["team_name"])
                lines.append(f"{member} - **{tag}**")
            else:
                lines.append(f"{member} - _Not Drawn_")
        e.description = "\n".join(lines)

        if undrawn_ids:
            e.set_footer(text=f"{len(undrawn_ids)} waiting - {clubs_left} clubs left - click Draw Next")
        else:
            e.set_footer(text="Draw complete! Use /season start to generate fixtures.")
        return e

    def _member(self, uid):
        """Best-effort member mention. Returns a raw mention string or fallback."""
        guild = self._guild
        if guild:
            m = guild.get_member(uid)
            if m:
                return m.mention
        return f"<@{uid}>"

    @discord.ui.button(label="Draw Next Team", style=discord.ButtonStyle.primary, row=0)
    async def draw_next(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_admin(interaction.user.id):
            await interaction.response.send_message(
                f"{EM.e('x')} Only admins can draw.", ephemeral=True)
            return

        undrawn = L.undrawn_managers(self.season_id)
        if not undrawn:
            await interaction.response.edit_message(embed=self._build_embed(), view=None)
            return

        already_taken = set(L.drawn_teams(self.season_id))
        pool = [c for c in DRAW_CLUBS if c not in already_taken]

        if not pool:
            await interaction.response.send_message(
                "No more clubs left in the pot.", ephemeral=True)
            return

        manager = undrawn[0]
        club = random.choice(pool)

        L.set_team_name(self.season_id, manager["user_id"], club)
        E.set_team_name(self.guild_id, manager["user_id"], club)

        # ping the drawn manager in the message content
        member = interaction.guild.get_member(manager["user_id"])
        ping = member.mention if member else f"<@{manager['user_id']}>"

        undrawn_left = len(undrawn) - 1
        # just keep editing the same growing list - no separate "Team Drawn" embed
        if undrawn_left > 0:
            await interaction.response.edit_message(content=ping, embed=self._build_embed(), view=self)
        else:
            await interaction.response.edit_message(content=ping, embed=self._build_embed(), view=None)

    @discord.ui.button(label="Draw All (Instant)", style=discord.ButtonStyle.secondary, row=0)
    async def draw_all(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_admin(interaction.user.id):
            await interaction.response.send_message(
                f"{EM.e('x')} Only admins can draw.", ephemeral=True)
            return

        undrawn = L.undrawn_managers(self.season_id)
        already_taken = set(L.drawn_teams(self.season_id))
        pool = [c for c in DRAW_CLUBS if c not in already_taken]
        random.shuffle(pool)

        assigned = 0
        for m in undrawn:
            if not pool:
                break
            club = pool.pop(0)
            L.set_team_name(self.season_id, m["user_id"], club)
            E.set_team_name(self.guild_id, m["user_id"], club)
            assigned += 1

        e = discord.Embed(
            title=f"{EM.e('check')} Draw Complete!",
            description=f"**{assigned}** teams assigned.",
            color=C.EMERALD,
        )
        e.set_footer(text="Use /season start to generate fixtures.")
        await interaction.response.edit_message(embed=e, view=None)
        await interaction.followup.send(embed=self._build_embed())


@season_group.command(name="draw", description="Run the team draw ceremony (randomly assigns clubs to managers)")
async def season_draw(interaction: discord.Interaction):
    await interaction.response.defer()
    if not is_admin(interaction.user.id):
        await interaction.followup.send(f"{EM.e('x')} Admins only.", ephemeral=True)
        return
    guild_id = interaction.guild_id
    s = L.active_season(guild_id)
    if not s:
        await interaction.followup.send(f"{EM.e('x')} No active season.", ephemeral=True)
        return

    tms = L.teams(s["id"])
    if not tms:
        await interaction.followup.send(
            f"{EM.e('x')} No managers added yet. Use `/season add @user` first.",
            ephemeral=True)
        return

    undrawn = L.undrawn_managers(s["id"])
    if not undrawn:
        await interaction.followup.send(
            f"{EM.e('check')} All managers already have teams. The draw is done.",
            ephemeral=True)
        return

    if len(tms) > len(DRAW_CLUBS):
        await interaction.followup.send(
            f"{EM.e('x')} {len(tms)} managers but only {len(DRAW_CLUBS)} clubs in the pot. "
            f"Add more clubs to DRAW_CLUBS in main.py.", ephemeral=True)
        return

    view = DrawView(guild_id, s["id"], s["number"], guild=interaction.guild)
    await interaction.followup.send(embed=view._build_embed(), view=view)


@season_group.command(name="start", description="Generate fixtures and start the season")
async def season_start(interaction: discord.Interaction):
    await interaction.response.defer()
    if not is_admin(interaction.user.id):
        await interaction.followup.send(f"{EM.e('x')} Admins only.", ephemeral=True)
        return
    guild_id = interaction.guild_id
    s = L.active_season(guild_id)
    if not s:
        await interaction.followup.send(f"{EM.e('x')} No active season.", ephemeral=True)
        return
    if s["status"] == "active":
        await interaction.followup.send(f"{EM.e('x')} Season is already active.", ephemeral=True)
        return
    tms = L.teams(s["id"])
    if len(tms) < 2:
        await interaction.followup.send(f"{EM.e('x')} Need at least 2 teams.", ephemeral=True)
        return
    # Check all managers have teams drawn
    undrawn = L.undrawn_managers(s["id"])
    if undrawn:
        await interaction.followup.send(
            f"{EM.e('x')} {len(undrawn)} manager(s) still need a team. "
            f"Run `/season draw` first.", ephemeral=True)
        return
    try:
        L.generate_fixtures(s["id"])
    except Exception as ex:
        await interaction.followup.send(f"{EM.e('x')} Couldn't generate fixtures: {ex}", ephemeral=True)
        return
    fxs = L.fixtures(s["id"])
    await interaction.followup.send(
        f"**Season {s['number']}** is LIVE! {len(tms)} teams, "
        f"{len(fxs)} fixtures generated.\n"
        f"Format: **{s['format']}**.\n"
        f"Use `/fixtures` to see matches, `/quickresult` to enter scores, "
        f"`/table` for standings.")


@season_group.command(name="info", description="View season info")
async def season_info(interaction: discord.Interaction):
    s = L.active_season(interaction.guild_id)
    await interaction.response.defer()
    if not s:
        await interaction.followup.send(f"{EM.e('x')} No active season.", ephemeral=True)
        return
    tms = L.teams(s["id"])
    fxs = L.fixtures(s["id"])
    played = [f for f in fxs if f["status"] == "played"]
    upcoming = [f for f in fxs if f["status"] == "scheduled" and f["home_user"] and f["away_user"]]
    e = discord.Embed(
        title=f"Season {s['number']}",
        description=(f"**Format:** {s['format']}\n"
                     f"**Status:** {s['status']}\n"
                     f"**Teams:** {len(tms)}\n"
                     f"**Fixtures:** {len(fxs)} total . {len(played)} played . "
                     f"{len(upcoming)} scheduled"),
        color=C.TEAL)
    await interaction.followup.send(embed=e)


@season_group.command(name="end", description="End the current season")
async def season_end(interaction: discord.Interaction):
    await interaction.response.defer()
    if not is_admin(interaction.user.id):
        await interaction.followup.send(f"{EM.e('x')} Admins only.", ephemeral=True)
        return
    s = L.active_season(interaction.guild_id)
    if not s:
        await interaction.followup.send(f"{EM.e('x')} No active season.", ephemeral=True)
        return
    L.set_season_status(s["id"], "complete")
    champ = L.champion(s["id"]) or L.league_winner(s["id"])
    champ_txt = ""
    if champ:
        member = interaction.guild.get_member(champ)
        cn = L.team_name_of(s["id"], champ) or (member.display_name if member else "?")
        champ_txt = f"\n{EM.e('trophy')} **Champion: {cn}**"
    await interaction.followup.send(f"**Season {s['number']}** completed.{champ_txt}")


@season_group.command(name="clear", description="Remove test squads from your server (housekeeping)")
async def season_clear(interaction: discord.Interaction):
    """Removes all squads from the guild (housekeeping after /testseason)."""
    await interaction.response.defer(ephemeral=True)
    if not is_admin(interaction.user.id):
        await interaction.followup.send(f"{EM.e('x')} Admins only.", ephemeral=True)
        return
    with db.cursor() as c:
        # Count how many we're removing
        count = c.execute(
            "SELECT COUNT(*) as n FROM squads WHERE guild_id=?",
            (interaction.guild_id,)).fetchone()
        n = count["n"] if count else 0
        # Remove squads, users, lineups, formations for this guild
        c.execute("DELETE FROM squads WHERE guild_id=?", (interaction.guild_id,))
        c.execute("DELETE FROM users WHERE guild_id=?", (interaction.guild_id,))
        c.execute("DELETE FROM lineup_overrides WHERE guild_id=?", (interaction.guild_id,))
        c.execute("DELETE FROM formations WHERE guild_id=?", (interaction.guild_id,))
        c.execute("DELETE FROM season_teams WHERE season_id IN ("
                  "SELECT id FROM seasons WHERE guild_id=? AND status='complete')",
                  (interaction.guild_id,))
    await interaction.followup.send(
        f"{EM.e('check')} **Cleared {n} squad entries.** All squads, lineups, "
        f"and formations have been removed from this server.")


@bot.tree.command(description="View fixtures (upcoming, or a specific matchday).")
@app_commands.describe(matchday="Which matchday to view (leave empty for next upcoming).")
async def fixtures(interaction: discord.Interaction, matchday: int = None):
    s = L.active_season(interaction.guild_id)
    await interaction.response.defer()
    if not s:
        await interaction.followup.send(f"{EM.e('x')} No active season.", ephemeral=True)
        return

    if matchday:
        fxs = [f for f in L.fixtures(s["id"]) if f["matchday"] == matchday]
        title = f"Matchday {matchday}"
    else:
        all_fxs = L.fixtures(s["id"])
        unplayed_mds = sorted(set(
            f["matchday"] for f in all_fxs
            if f["status"] == "scheduled" and f["home_user"] and f["away_user"]
        ))
        if not unplayed_mds:
            await interaction.followup.send(f"{EM.e('check')} All fixtures played!", ephemeral=True)
            return
        md = unplayed_mds[0]
        fxs = [f for f in all_fxs if f["matchday"] == md]
        title = f"Next up — Matchday {md}"

    if not fxs:
        await interaction.followup.send("No fixtures found.", ephemeral=True)
        return

    # drop knockout placeholders with no teams assigned yet (they share matchday
    # numbers but aren't real fixtures until the bracket fills)
    fxs = [f for f in fxs if f["home_user"] is not None or f["away_user"] is not None]
    # re-check: the filter above may have emptied the list (e.g. a matchday that
    # only contained unfilled knockout bracket slots)
    if not fxs:
        await interaction.followup.send(
            f"No playable fixtures on matchday {matchday}. "
            "It may only contain unfilled knockout slots — play earlier rounds first.",
            ephemeral=True)
        return
    # group fixtures by their group label (None for league/knockout formats)
    from collections import OrderedDict
    grouped = OrderedDict()
    for f in fxs:
        key = f.get("group_label")
        grouped.setdefault(key, []).append(f)

    multi_group = any(k is not None for k in grouped) and len(grouped) > 1
    lines = []
    for grp_label, grp_fxs in grouped.items():
        if multi_group:
            lines.append(f"**━━ GROUP {grp_label} ━━**")
        for f in grp_fxs:
            hm = interaction.guild.get_member(f["home_user"]) if f["home_user"] else None
            am = interaction.guild.get_member(f["away_user"]) if f["away_user"] else None
            hname = _team_tag(s["id"], f["home_user"], hm) if f["home_user"] else "TBD"
            aname = _team_tag(s["id"], f["away_user"], am) if f["away_user"] else "TBD"
            if f["status"] == "played":
                score = f"{f['home_score']} - {f['away_score']}"
                lines.append(f"`#{f['id']:3}` **{hname}** {score} **{aname}** (done)")
            else:
                lines.append(f"`#{f['id']:3}` **{hname}** vs **{aname}**")
        if multi_group:
            lines.append("")
    # title: matchday only — groups shown as inline subheadings above
    stage_tag = f" · {fxs[0]['stage'].title()}" if fxs[0].get("stage") else ""
    e = discord.Embed(title=title + stage_tag,
                      description="\n".join(lines).strip(), color=C.OBSIDIAN)
    e.set_footer(text="Use the fixture # with /result to enter a score")
    await interaction.followup.send(embed=e)


async def fixture_autocomplete(interaction: discord.Interaction, current: str):
    s = L.active_season(interaction.guild_id)
    if not s:
        return []
    fxs = [f for f in L.fixtures(s["id"]) if f["status"] == "scheduled"
           and f["home_user"] and f["away_user"]]
    choices = []
    for f in fxs[:25]:
        hm = interaction.guild.get_member(f["home_user"]) if f["home_user"] else None
        am = interaction.guild.get_member(f["away_user"]) if f["away_user"] else None
        hname = _team_name(s["id"], f["home_user"], hm)
        aname = _team_name(s["id"], f["away_user"], am)
        stage = f" · {f['stage']}" if f.get("stage") and f["stage"] != "league" else ""
        label = f"#{f['id']}  {hname} vs {aname} (MD{f['matchday']}{stage})"
        choices.append(app_commands.Choice(name=label[:100], value=str(f["id"])))
    return choices


@bot.tree.command(description="League standings table (auto-updates from results).")
@app_commands.describe(group="Group letter (A, B, ...) for group-stage seasons.")
async def table(interaction: discord.Interaction, group: str = None):
    await interaction.response.defer(thinking=True)
    s = L.active_season(interaction.guild_id)
    if not s:
        await interaction.followup.send(f"{EM.e('x')} No active season.", ephemeral=True)
        return

    # If knockout-only format, show bracket instead of table
    if s["format"] == "knockout":
        rnds = L.bracket(s["id"])
        if rnds:
            try:
                import bracket_card as BC
                buf = BC.render_bracket(interaction.guild_id, s["id"])
                if buf:
                    file = discord.File(buf, filename="bracket.png")
                    await interaction.followup.send(
                        content=f"Knockout Bracket - Season {s['number']}", file=file)
                    return
            except Exception:
                pass

    tms = L.teams(s["id"])
    has_groups = any(t.get("group_label") for t in tms)

    if has_groups and not group:
        grps = L.groups(s["id"])
        if not grps:
            await interaction.followup.send("No group standings yet.", ephemeral=True)
            return
        try:
            import standings_card as ST
            grouped = [(gl, rows) for gl, rows in grps.items()]
            sub = f"Season {s['number']} · Group Stage"
            buf = ST.render_groups(grouped, subtitle=sub, zone_up=2, zone_down=0,
                                   season_id=s["id"])
            file = discord.File(buf, filename="groups.png")
            await interaction.followup.send(
                content=f"**Group Standings — Season {s['number']}**", file=file)
        except Exception as e:
            grouped = list(grps.items())
            for gl, rows in grouped[:3]:
                e2 = discord.Embed(title=f"Group {gl}", color=C.OBSIDIAN)
                e2.description = "```\n" + _format_table(rows) + "\n```"
                await interaction.followup.send(embed=e2)
            await interaction.followup.send(
                f"Image failed ({e}). Showing first 3 groups as text.")
        return

    if group:
        group = group.upper()
        rows = L.standings(s["id"], group=group, stage="group")
    else:
        rows = L.standings(s["id"], stage="league")

    try:
        import standings_card as ST
        n = len(rows)
        zone_down = 3 if n >= 10 and s["format"] != "knockout" else 0
        sub = f"Season {s['number']} · {s['format'].replace('_',' ').title()}"
        render_group = group
        render_stage = "group" if group else "league"
        buf = ST.render_standings(rows, title="STANDINGS", subtitle=sub,
                                  zone_up=4, zone_down=zone_down,
                                  season_id=s["id"], stage=render_stage,
                                  group=render_group)
        file = discord.File(buf, filename="standings.png")
        await interaction.followup.send(
            content=f"**Standings — Season {s['number']}**", file=file)
    except Exception as e:
        tbl_txt = _format_table(rows)
        embed = discord.Embed(title=f"Standings — Season {s['number']}", color=C.OBSIDIAN)
        embed.description = "```\n" + tbl_txt + "\n```"
        await interaction.followup.send(
            f"Couldn't render image ({e}). Text version:", embed=embed)


def _format_table(rows: list) -> str:
    """Format standings rows as a monospace table."""
    header = f"{'#':>2}  {'Team':<20} {'P':>2} {'W':>2} {'D':>2} {'L':>2} {'GF':>3} {'GA':>3} {'GD':>3} {'Pts':>3}"
    sep = "-" * len(header)
    lines = [header, sep]
    for i, r in enumerate(rows, 1):
        name = (r["team_name"] or "?")[:20]
        gd = f"{r['GD']:+d}"
        lines.append(
            f"{i:>2}  {name:<20} {r['P']:>2} {r['W']:>2} {r['D']:>2} {r['L']:>2} "
            f"{r['GF']:>3} {r['GA']:>3} {gd:>3} {r['Pts']:>3}")
    return "\n".join(lines)


@bot.tree.command(description="View the knockout bracket as an image.")
async def bracket(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)
    s = L.active_season(interaction.guild_id)
    if not s:
        await interaction.followup.send("No active season.", ephemeral=True)
        return
    rnds = L.bracket(s["id"])
    if not rnds:
        await interaction.followup.send(
            "No knockout bracket for this season format.", ephemeral=True)
        return
    try:
        import bracket_card as BC
        buf = BC.render_bracket(interaction.guild_id, s["id"])
        if buf:
            file = discord.File(buf, filename="bracket.png")
            await interaction.followup.send(
                content=f"Knockout Bracket - Season {s['number']}", file=file)
        else:
            await interaction.followup.send("No bracket data to render.")
    except Exception as e:
        lines = []
        for ri, rnd in enumerate(rnds):
            label = rnd[0]["stage"] if rnd else f"Round {ri+1}"
            lines.append(f"**{label}**")
            for f in rnd:
                hname = _team_name(s["id"], f["home_user"]) if f["home_user"] else "TBD"
                aname = _team_name(s["id"], f["away_user"]) if f["away_user"] else "TBD"
                if f["status"] == "played":
                    lines.append(f"  #{f['id']} {hname} {f['home_score']}-{f['away_score']} {aname}")
                else:
                    lines.append(f"  #{f['id']} {hname} vs {aname}")
            lines.append("")
        await interaction.followup.send(
            f"Image failed ({e}). Text:",
            embed=discord.Embed(description="\n".join(lines)[:4096]))

TEST_CLUBS = [
    "Real Madrid", "Manchester City", "Bayern Munich", "Liverpool",
    "Barcelona", "Inter Milan", "Atlético Madrid", "AC Milan",
    "Chelsea", "Arsenal", "Juventus", "Napoli",
    "Tottenham Hotspur", "Manchester United", "Borussia Dortmund", "Paris Saint-Germain",
    "Atalanta", "AS Roma", "Bayer Leverkusen", "Sevilla",
    "RB Leipzig", "Lazio", "Benfica", "Porto",
    "Ajax", "PSV Eindhoven", "Sporting CP", "Olympiacos",
    "Shakhtar Donetsk", "Celtic", "Rangers", "Galatasaray",
]
_TEST_UID_BASE = 900_000_000


@bot.tree.command(description="[Admin] Spin up a fake 32-team season to test all league commands.")
@app_commands.describe(
    fmt="Competition format (default: single round-robin).",
    autoplay="Auto-play ALL results with random scores so you can see a full table.",
)
@app_commands.choices(fmt=LEAGUE_FORMAT_CHOICES)
async def testseason(interaction: discord.Interaction,
                     fmt: app_commands.Choice[str] = None,
                     autoplay: bool = True):
    await interaction.response.defer(thinking=True)
    if not is_admin(interaction.user.id):
        await interaction.followup.send(f"{EM.e('x')} Admins only.", ephemeral=True)
        return
    guild_id = interaction.guild_id
    try:
        existing = L.active_season(guild_id)
        if existing:
            L.set_season_status(existing["id"], "complete")
        format_val = fmt.value if fmt else "round_robin"
        num = L.next_season_number(guild_id)
        sid = L.create_season(guild_id, format_val, number=num)
        added = 0

        # Distribute players by position to ensure balanced squads
        # Each team gets: 2 GK, 5 DEF, 5 MID, 3 FWD = 15 players
        by_group = {"GK": [], "DEF": [], "MID": [], "FWD": []}
        for p in sorted(P.all_players(), key=lambda x: x["ovr"], reverse=True):
            by_group.setdefault(p["group"], []).append(p)

        squad_needs = {"GK": 2, "DEF": 5, "MID": 5, "FWD": 3}
        team_idx = {g: 0 for g in squad_needs}

        for i, club in enumerate(TEST_CLUBS):
            uid = _TEST_UID_BASE + i
            E.ensure_user(guild_id, uid)
            E.set_team_name(guild_id, uid, club)
            L.add_team_auto_seed(sid, uid, team_name=club)
            added += 1

            # Assign players by position
            for group, count in squad_needs.items():
                pool = by_group[group]
                start = team_idx[group]
                for p in pool[start:start + count]:
                    E.add_player(guild_id, uid, p, p["value"])
                team_idx[group] += count

            E.set_formation(guild_id, uid, "4-3-3")

        L.generate_fixtures(sid)
        fxs = L.fixtures(sid)

        played = 0
        if autoplay:
            import random
            random.seed(1337)
            playable = [f for f in fxs if f["stage"] in ("league", "group")
                        and f["home_user"] and f["away_user"]]
            for f in playable:
                L.enter_result(f["id"], random.randint(0, 4), random.randint(0, 4))
                played += 1

        msg = (f"**Test season {num}** ready.\n"
               f"**{added} teams** (Real Madrid, Man City, Bayern, ...) · "
               f"format: **{format_val}** · {len(fxs)} fixtures generated.\n")
        if autoplay and played:
            msg += f"Auto-played **{played}** league/group matches with random scores.\n"
        msg += ("\nNow try:\n"
                f"• `/table` — see the live standings image\n"
                f"• `/fixtures` — view matchdays\n"
                f"• `/quickresult` — enter a score with stat buttons\n"
                f"• `/squad` — view a team (use the test UID)\n"
                f"• `/bracket` — knockout view (if applicable)\n"
                f"_Test team UIDs: 900000000 to 900000031_")
        await interaction.followup.send(msg)
    except Exception as e:
        await interaction.followup.send(f"{EM.e('x')} Test season failed: {e}", ephemeral=True)


# ==========================================================================
#  WATCHLIST
# ==========================================================================
@bot.tree.command(description="Manage your watchlist (get pinged when a target goes up).")
@app_commands.describe(
    action="What to do.",
    player="Player name (for add/remove).",
)
@app_commands.choices(action=[
    app_commands.Choice(name="Add to watchlist", value="add"),
    app_commands.Choice(name="Remove from watchlist", value="remove"),
    app_commands.Choice(name="View your watchlist", value="list"),
])
@app_commands.autocomplete(player=all_player_autocomplete)
async def watch(interaction: discord.Interaction,
                action: app_commands.Choice[str],
                player: str = None):
    await interaction.response.defer()
    act = action.value
    gid = interaction.guild_id
    uid = interaction.user.id

    if act == "add":
        if not player:
            await interaction.followup.send("Pick a player to watch.", ephemeral=True)
            return
        p = P.get(player)
        if not p:
            await interaction.followup.send("Player not found.", ephemeral=True)
            return
        if E.is_sold(gid, player):
            await interaction.followup.send(f"**{p['name']}** is already sold.", ephemeral=True)
            return
        E.watch_add(gid, uid, player)
        await interaction.followup.send(
            f"Watching **{p['name']}**. You'll get pinged when they go up for auction.")

    elif act == "remove":
        if not player:
            await interaction.followup.send("Pick a player to remove.", ephemeral=True)
            return
        E.watch_remove(gid, uid, player)
        await interaction.followup.send("Removed from watchlist.")

    elif act == "list":
        keys = E.watch_list(gid, uid)
        if not keys:
            await interaction.followup.send("Your watchlist is empty.", ephemeral=True)
            return
        lines = []
        for k in keys:
            p = P.get(k)
            if p:
                if E.is_sold(gid, k):
                    status = f" {EM.e('x')}"
                else:
                    status = f" {EM.e('check')}"
                lines.append(
                    f"**{p['ovr']}** {p['position']} · "
                    f"{P.flag(p['country'])} **{p['name']}**{status}"
                )
        e = discord.Embed(title=f"Watchlist ({len(keys)})",
                          description="\n".join(lines), color=C.AMBER)
        e.set_footer(text="You'll get pinged when these go up for auction")
        await interaction.followup.send(embed=e, ephemeral=True)


# ==========================================================================
#  DRAFT RECAP + AUCTION HISTORY
# ==========================================================================
@bot.tree.command(description="View the draft recap: biggest buys, steals, spending.")
async def draftrecap(interaction: discord.Interaction):
    recap = E.draft_recap(interaction.guild_id)
    await interaction.response.defer()
    if not recap:
        await interaction.followup.send("No auctions completed yet.", ephemeral=True)
        return

    e = discord.Embed(
        title="Draft Recap",
        description=(f"**{recap['total_sales']}** players sold for a total of "
                     f"**{E.money(recap['total_spent'])}**."),
        color=C.AMBER,
    )

    # Top buys
    top_lines = []
    for s in recap["top_buys"][:8]:
        p = P.get(s["player_key"])
        if not p:
            continue
        member = interaction.guild.get_member(s["winner_id"])
        buyer = member.display_name if member else f"<@{s['winner_id']}>"
        team_name = E.get_team_name(interaction.guild_id, s["winner_id"]) or buyer
        team_tag = EM.club_tag(team_name)
        top_lines.append(
            f"{P.flag(p['country'])} **{p['name']}** ({p['ovr']}) -> {team_tag} - **{E.money(s['final_price'])}**"
        )
    e.add_field(name="Biggest Buys", value="\n".join(top_lines), inline=False)

    # Steals
    if recap["steals"]:
        steal_lines = []
        for s, p, ratio in recap["steals"][:5]:
            member = interaction.guild.get_member(s["winner_id"])
            buyer = member.display_name if member else "?"
            team_name = E.get_team_name(interaction.guild_id, s["winner_id"]) or buyer
            team_tag = EM.club_tag(team_name)
            steal_lines.append(
                f"**{p['name']}** ({p['ovr']}) -> {team_tag} for **{E.money(s['final_price'])}** "
                f"(value {E.money(p['value'])}, {int(ratio*100)}% of value)"
            )
        e.add_field(name="Steals of the Draft", value="\n".join(steal_lines), inline=False)

    # Spending by manager
    spend_lines = []
    for uid, amount in sorted(recap["spending"].items(), key=lambda x: -x[1])[:10]:
        member = interaction.guild.get_member(uid)
        name = member.display_name if member else f"<@{uid}>"
        spend_lines.append(f"{name}: **{E.money(amount)}**")
    e.add_field(name="Spending by Manager", value="\n".join(spend_lines), inline=False)

    await interaction.followup.send(embed=e)


@bot.tree.command(description="Search auction history by player or manager.")
@app_commands.describe(
    player="Search by player name.",
    user="Search by buyer (mention).",
)
@app_commands.autocomplete(player=all_player_autocomplete)
async def soldsearch(interaction: discord.Interaction, player: str = None,
                     user: discord.Member = None):
    await interaction.response.defer()
    if not player and not user:
        await interaction.followup.send("Search by player or by manager.", ephemeral=True)
        return

    sales = E.search_sales(
        interaction.guild_id,
        player_key=player if player else None,
        user_id=user.id if user else None,
    )
    if not sales:
        await interaction.followup.send("No matching sales found.", ephemeral=True)
        return

    lines = []
    for s in sales[:20]:
        p = P.get(s["player_key"])
        if not p:
            continue
        member = interaction.guild.get_member(s["winner_id"])
        buyer = member.display_name if member else "?"
        team_name = E.get_team_name(interaction.guild_id, s["winner_id"]) or buyer
        team_tag = EM.club_tag(team_name)
        lines.append(f"{P.flag(p['country'])} **{p['name']}** ({p['ovr']}) -> {team_tag} - **{E.money(s['final_price'])}**")
    title = "Auction History"
    if player:
        pp = P.get(player)
        title += f" - {pp['name']}" if pp else ""
    elif user:
        title += f" - {user.display_name}"
    e = discord.Embed(title=title, description="\n".join(lines), color=C.AMBER)
    await interaction.followup.send(embed=e)


# ==========================================================================
#  PENALTY SHOOTOUT + H2H + SEASON ARCHIVE
# ==========================================================================
@bot.tree.command(description="Head-to-head record between two managers.")
@app_commands.describe(user1="First manager.", user2="Second manager.")
async def h2h(interaction: discord.Interaction, user1: discord.Member, user2: discord.Member):
    await interaction.response.defer()
    if user1.id == user2.id:
        await interaction.followup.send("Pick two different managers.", ephemeral=True)
        return
    data = E.head_to_head(interaction.guild_id, user1.id, user2.id)
    if not data["fixtures"]:
        await interaction.followup.send(
            f"No matches played between {user1.display_name} and {user2.display_name} yet.",
            ephemeral=True)
        return

    e = discord.Embed(
        title=f"{user1.display_name} vs {user2.display_name}",
        description=(f"**{data['a_wins']}** - {data['draws']} - **{data['b_wins']}** "
                     f"({user1.display_name} wins - draws - {user2.display_name} wins)"),
        color=C.SLATE,
    )
    lines = []
    for f in data["fixtures"][:10]:
        hm = interaction.guild.get_member(f["home_user"]) if f["home_user"] else None
        am = interaction.guild.get_member(f["away_user"]) if f["away_user"] else None
        hname = EM.club_tag(hm.display_name) if hm else "?"
        aname = EM.club_tag(am.display_name) if am else "?"
        pens_str = ""
        if f.get("home_pens") is not None:
            pens_str = f" ({f['home_pens']}-{f['away_pens']} pens)"
        stage = f.get("stage", "")
        lines.append(f"**{hname}** {f['home_score']}-{f['away_score']} **{aname}**{pens_str} _{stage}_")
    e.add_field(name="Results", value="\n".join(lines), inline=False)
    await interaction.followup.send(embed=e)


@bot.tree.command(description="Browse past seasons and their champions.")
async def archive(interaction: discord.Interaction):
    with db.cursor() as c:
        await interaction.response.defer()
        rows = c.execute(
            "SELECT * FROM seasons WHERE guild_id=? ORDER BY number DESC",
            (interaction.guild_id,),
        ).fetchall()
    if not rows:
        await interaction.followup.send("No seasons yet.", ephemeral=True)
        return

    lines = []
    for s in rows:
        champ = L.champion(s["id"]) or L.league_winner(s["id"])
        if champ:
            member = interaction.guild.get_member(champ)
            cn = member.display_name if member else f"<@{champ}>"
            champ_team = E.get_team_name(interaction.guild_id, champ) or cn
            champ_tag = EM.club_tag(champ_team)
        else:
            champ_tag = "No champion"
        n_teams = len(L.teams(s["id"]))
        n_fx = len(L.fixtures(s["id"]))
        played = len([f for f in L.fixtures(s["id"]) if f["status"] == "played"])
        fmt_label = s["format"].replace("_", " ").title()
        status_emoji = f"{EM.e('check')}" if s["status"] == "complete" else ("🔴" if s["status"] == "active" else "")
        lines.append(
            f"{status_emoji} **Season {s['number']}** — {fmt_label}\n"
            f"{EM.e('trophy')} {champ_tag} · {n_teams} teams · {played}/{n_fx} played"
        )
    e = discord.Embed(title=f"{EM.e('trophy')} Season Archive",
                      description="\n\n".join(lines), color=C.SLATE)
    e.set_footer(text=f"{len(rows)} season(s) in history")
    await interaction.followup.send(embed=e)


# ==========================================================================
#  QUICK RESULT + MATCH STATS (buttons)
# ==========================================================================
class QuickResultView(discord.ui.View):
    """Per-team stat entry. Steps split by team + stat type."""

    def __init__(self, guild_id, fixture_id, season_id, home_user, away_user,
                 home_score, away_score, is_knockout_draw=False):
        super().__init__(timeout=900)
        self.guild_id = guild_id
        self.fixture_id = fixture_id
        self.season_id = season_id
        self.home_user = home_user
        self.away_user = away_user
        self.home_score = home_score
        self.away_score = away_score
        self.is_knockout_draw = is_knockout_draw
        self.stats = {}
        self.own_goals_home = 0
        self.own_goals_away = 0
        self.motm_key = None

        # Build step list dynamically based on scores
        # stat_key maps to the actual stats dict key
        self.steps = []
        self.steps.append(("goals", self.home_user, self.home_score))
        if self.away_score > 0:
            self.steps.append(("goals", self.away_user, self.away_score))
        self.steps.append(("assists", self.home_user, self.home_score))
        if self.away_score > 0:
            self.steps.append(("assists", self.away_user, self.away_score))
        self.steps.append(("tackles", self.home_user, None))
        self.steps.append(("tackles", self.away_user, None))
        self.steps.append(("yellow", self.home_user, None))
        self.steps.append(("yellow", self.away_user, None))
        self.steps.append(("red", self.home_user, None))
        self.steps.append(("red", self.away_user, None))
        self.steps.append(("motm", None, None))  # both teams

        self.step_idx = 0
        self.build_step()

    def _team_squad(self, uid):
        """Get a team's full squad sorted by OVR."""
        squad = E.get_squad(self.guild_id, uid)
        squad.sort(key=lambda p: p["ovr"], reverse=True)
        return squad

    def _get(self, key):
        if key not in self.stats:
            self.stats[key] = {"goals": 0, "assists": 0, "tackles": 0,
                               "yellow": 0, "red": 0, "motm": 0}
        return self.stats[key]

    def _count(self, stat, uid=None):
        """Count how many of a stat have been assigned, optionally filtered by team."""
        total = 0
        for key, s in self.stats.items():
            if s[stat] == 0:
                continue
            if uid is not None:
                owner = E.get_player_owner(self.guild_id, key)
                if not owner or owner[0] != uid:
                    continue
            total += s[stat]
        return total

    def _team_name(self, uid):
        try:
            tn = L.team_name_of(self.season_id, uid)
            if tn:
                return tn
        except Exception:
            pass
        return f"Team {uid}"

    def _step_text(self):
        if self.step_idx >= len(self.steps):
            return "**Review & Save**"
        stat, uid, limit = self.steps[self.step_idx]
        stat_labels = {"goals": f"{EM.e('stat_goals')} GOAL SCORERS",
                      "assists": f"{EM.e('stat_assists')} ASSISTERS",
                      "tackles": f"{EM.e('stat_tackles')} TACKLES",
                      "yellow": f"{EM.e('stat_yellow')} YELLOW CARDS",
                      "red": f"{EM.e('stat_red')} RED CARDS",
                      "motm": f"{EM.e('stat_motm')} MAN OF THE MATCH"}
        team = self._team_name(uid) if uid else "Both Teams"
        total = self.step_idx + 1
        text = f"**Step {total}/{len(self.steps)}: {stat_labels.get(stat, stat)} ({team})**"
        if limit:
            assigned = self._count(stat, uid)
            if stat == "goals":
                assigned += self.own_goals_home if uid == self.home_user else self.own_goals_away
            text += f" | {assigned}/{limit} assigned"
        return text

    def build_step(self):
        self.clear_items()

        if self.step_idx >= len(self.steps):
            self._build_confirm()
            return

        stat, uid, limit = self.steps[self.step_idx]

        # Determine which players to show
        if uid:
            players = self._team_squad(uid)
        else:
            # MOTM: both teams
            players = self._team_squad(self.home_user) + self._team_squad(self.away_user)

        btn_count = 0
        for p in players:
            # Check limits
            if stat == "goals":
                if limit:
                    assigned = self._count("goals", uid)
                    if uid == self.home_user:
                        assigned += self.own_goals_home
                    else:
                        assigned += self.own_goals_away
                    if assigned >= limit:
                        break
            elif stat == "assists":
                if limit:
                    assigned = self._count("assists", uid)
                    if assigned >= limit:
                        break
            elif stat == "motm":
                if self.motm_key is not None:
                    break

            current = self._get(p["key"])[stat]
            suffix = f" x{current}" if current > 0 else ""
            short = p["name"][:16] + "." if len(p["name"]) > 17 else p["name"]

            row = btn_count // 5
            if row > 3:
                break

            btn = discord.ui.Button(label=f"{short}{suffix}", style=discord.ButtonStyle.primary, row=row)
            btn.callback = self._make_tap(p["key"], stat)
            self.add_item(btn)
            btn_count += 1

        # Own goal button (scorers only, if limit not reached)
        if stat == "goals" and limit:
            assigned = self._count("goals", uid)
            if uid == self.home_user:
                assigned += self.own_goals_home
            else:
                assigned += self.own_goals_away
            if assigned < limit and btn_count < 20:
                row = min(btn_count // 5, 3)
                og = discord.ui.Button(label="Own Goal", style=discord.ButtonStyle.secondary, row=row)
                og.callback = self._own_goal(uid)
                self.add_item(og)

        # Next + Skip on row 4
        nxt_label = "Review & Save" if self.step_idx >= len(self.steps) - 1 else f"Next"
        nxt = discord.ui.Button(label=nxt_label, style=discord.ButtonStyle.success, row=4)
        nxt.callback = self._next
        self.add_item(nxt)

        skip = discord.ui.Button(label="Skip", style=discord.ButtonStyle.danger, row=4)
        skip.callback = self._skip
        self.add_item(skip)

    def _make_tap(self, key, stat):
        async def cb(interaction):
            s = self._get(key)
            auto_advance = False
            if stat == "goals":
                _, uid, limit = self.steps[self.step_idx]
                assigned = self._count("goals", uid)
                if uid == self.home_user:
                    assigned += self.own_goals_home
                else:
                    assigned += self.own_goals_away
                if assigned >= limit:
                    await interaction.response.send_message("All goals assigned for this team.", ephemeral=True)
                    return
                s["goals"] += 1
                # Check if max reached after this tap
                assigned = self._count("goals", uid)
                if uid == self.home_user:
                    assigned += self.own_goals_home
                else:
                    assigned += self.own_goals_away
                if assigned >= limit:
                    auto_advance = True
            elif stat == "assists":
                _, uid, limit = self.steps[self.step_idx]
                assigned = self._count("assists", uid)
                if assigned >= limit:
                    await interaction.response.send_message("Max assists reached for this team.", ephemeral=True)
                    return
                s["assists"] += 1
                assigned = self._count("assists", uid)
                if assigned >= limit:
                    auto_advance = True
            elif stat == "motm":
                if self.motm_key is not None:
                    await interaction.response.send_message("MOTM already picked.", ephemeral=True)
                    return
                for k in self.stats:
                    self.stats[k]["motm"] = 0
                s["motm"] = 1
                self.motm_key = key
                auto_advance = True
            else:
                s[stat] += 1

            if auto_advance:
                self.step_idx += 1
            self.build_step()

            if self.step_idx >= len(self.steps):
                text = self._review_text()
            else:
                text = self._step_text()
            await interaction.response.edit_message(content=text, view=self)
        return cb

    def _own_goal(self, uid):
        async def cb(interaction):
            _, _, limit = self.steps[self.step_idx]
            if uid == self.home_user:
                if self.own_goals_home >= limit:
                    await interaction.response.send_message("No goals left.", ephemeral=True)
                    return
                self.own_goals_home += 1
            else:
                if self.own_goals_away >= limit:
                    await interaction.response.send_message("No goals left.", ephemeral=True)
                    return
                self.own_goals_away += 1
            self.build_step()
            await interaction.response.edit_message(content=self._step_text(), view=self)
        return cb

    async def _next(self, interaction):
        self.step_idx += 1
        self.build_step()
        text = self._review_text() if self.step_idx >= len(self.steps) else self._step_text()
        await interaction.response.edit_message(content=text, view=self)

    async def _skip(self, interaction):
        self.step_idx = len(self.steps)
        self._build_confirm()
        await interaction.response.edit_message(content=self._review_text(), view=self)

    def _review_text(self):
        """Build the review summary text."""
        hn = self._team_name(self.home_user)
        an = self._team_name(self.away_user)
        lines = [f"**{hn} {self.home_score}-{self.away_score} {an}**", "", "**Match Stats:**"]
        any_stats = False
        for key, s in self.stats.items():
            p = P.get(key)
            if not p:
                continue
            parts = []
            if s["goals"]: parts.append(f"{EM.e('stat_goals')}{s['goals']}")
            if s["assists"]: parts.append(f"{EM.e('stat_assists')}{s['assists']}")
            if s["tackles"]: parts.append(f"{EM.e('stat_tackles')}{s['tackles']}")
            if s["yellow"]: parts.append(f"{EM.e('stat_yellow')}{s['yellow']}")
            if s["red"]: parts.append(f"{EM.e('stat_red')}{s['red']}")
            if s["motm"]: parts.append(f"{EM.e('stat_motm')}MOTM")
            if parts:
                lines.append(f"  {p['name']}: {' '.join(parts)}")
                any_stats = True
        og = self.own_goals_home + self.own_goals_away
        if og:
            lines.append(f"  Own goals: {og}")
            any_stats = True
        if not any_stats:
            lines.append("  (Score only, no extra stats)")
        self.summary = "\n".join(lines[2:])
        return "\n".join(lines)

    def _build_confirm(self):
        self.clear_items()
        save = discord.ui.Button(label="Save Stats", style=discord.ButtonStyle.success)
        save.callback = self._save
        self.add_item(save)
        cancel = discord.ui.Button(label="Cancel", style=discord.ButtonStyle.danger)
        cancel.callback = self._cancel
        self.add_item(cancel)

    async def _save(self, interaction):
        for key, s in self.stats.items():
            if any(s.values()):
                E.add_player_stats(self.guild_id, key,
                    goals=s["goals"], assists=s["assists"], tackles=s["tackles"],
                    saves=0, motm=s["motm"], yellow=s["yellow"], red=s["red"],
                    season_id=self.season_id)

        msg = self._review_text()

        if self.is_knockout_draw:
            pv = PenaltyView(self.guild_id, self.fixture_id, self.season_id,
                             self.home_user, self.away_user, self.home_score, self.away_score)
            await interaction.response.edit_message(
                content=msg + "\n\n**Draw! Who won penalties?**", view=pv)
        else:
            await interaction.response.edit_message(content=msg, view=None)

    async def _cancel(self, interaction):
        await interaction.response.edit_message(content="Cancelled.", view=None)


class PenaltyView(discord.ui.View):
    def __init__(self, guild_id, fixture_id, season_id, home_user, away_user, hs, as_):
        super().__init__(timeout=300)
        self.guild_id = guild_id
        self.fixture_id = fixture_id
        self.season_id = season_id
        self.home_user = home_user
        self.away_user = away_user
        self.hs = hs
        self.as_ = as_

    def _name(self, uid):
        try:
            tn = L.team_name_of(self.season_id, uid)
            if tn: return tn
        except Exception:
            pass
        return f"Team {uid}"

    @discord.ui.button(label="Home wins pens", style=discord.ButtonStyle.primary)
    async def home_wins(self, interaction, button):
        import random
        wp = random.randint(4, 5)
        lp = random.randint(2, wp - 1)
        L.enter_result_with_penalties(self.fixture_id, self.hs, self.as_, wp, lp)
        h = self._name(self.home_user)
        await interaction.response.edit_message(
            content=f"**{h}** {self.hs}({wp}) - {self.as_}({lp}) **{self._name(self.away_user)}**\n**{h}** advance!", view=None)

    @discord.ui.button(label="Away wins pens", style=discord.ButtonStyle.danger)
    async def away_wins(self, interaction, button):
        import random
        wp = random.randint(4, 5)
        lp = random.randint(2, wp - 1)
        L.enter_result_with_penalties(self.fixture_id, self.hs, self.as_, lp, wp)
        a = self._name(self.away_user)
        await interaction.response.edit_message(
            content=f"**{self._name(self.home_user)}** {self.hs}({lp}) - {self.as_}({wp}) **{a}**\n**{a}** advance!", view=None)

    @discord.ui.button(label="Custom pens", style=discord.ButtonStyle.secondary)
    async def custom(self, interaction, button):
        await interaction.response.send_modal(PenaltyModal(self))


class PenaltyModal(discord.ui.Modal, title="Penalty Shootout Score"):
    def __init__(self, pv):
        super().__init__()
        self.pv = pv
        self.hp = discord.ui.TextInput(label="Home pens", required=True, max_length=2)
        self.ap = discord.ui.TextInput(label="Away pens", required=True, max_length=2)
        self.add_item(self.hp)
        self.add_item(self.ap)

    async def on_submit(self, interaction):
        try:
            hp = int(self.hp.value)
            ap = int(self.ap.value)
        except ValueError:
            await interaction.response.send_message("Invalid.", ephemeral=True)
            return
        if hp == ap:
            await interaction.response.send_message("Can't be a draw!", ephemeral=True)
            return
        L.enter_result_with_penalties(self.pv.fixture_id, self.pv.hs, self.pv.as_, hp, ap)
        h = self.pv._name(self.pv.home_user)
        a = self.pv._name(self.pv.away_user)
        w = h if hp > ap else a
        await interaction.response.send_message(
            f"**{h}** {self.pv.hs}({hp}) - {self.pv.as_}({ap}) **{a}**\n**{w}** advance!")


@bot.tree.command(description="Enter match result with stat buttons. Updates table + stats instantly.")
@app_commands.describe(fixture="The match.", score="Score e.g. 2-1.")
@app_commands.autocomplete(fixture=fixture_autocomplete)
async def quickresult(interaction: discord.Interaction, fixture: str, score: str):
    await interaction.response.defer()
    if not is_admin(interaction.user.id):
        await interaction.followup.send("Admins only.", ephemeral=True)
        return
    s = L.active_season(interaction.guild_id)
    if not s:
        await interaction.followup.send("No active season.", ephemeral=True)
        return
    try:
        fid = int(fixture)
    except ValueError:
        await interaction.followup.send("Invalid fixture ID.", ephemeral=True)
        return
    import re
    m = re.match(r"\s*(\d+)\s*-\s*(\d+)\s*", score.strip())
    if not m:
        await interaction.followup.send("Format: 2-1", ephemeral=True)
        return
    hs, as_ = int(m.group(1)), int(m.group(2))

    fx = L.fixture_by_id(fid)
    if not fx:
        await interaction.followup.send("Fixture not found.", ephemeral=True)
        return

    L.enter_result(fid, hs, as_)
    is_ko = (hs == as_ and fx.get("next_fixture"))

    view = QuickResultView(interaction.guild_id, fid, s["id"],
                           fx["home_user"], fx["away_user"], hs, as_, is_knockout_draw=is_ko)
    await interaction.followup.send(content=view._step_text(), view=view)


# ==========================================================================
#  CSV MATCH IMPORT
# ==========================================================================
@bot.tree.command(description="[Admin] Import match stats from a FL26 export CSV.")
@app_commands.describe(file="Upload the CSV file exported by the Sider match_export module.")
async def importmatch(interaction: discord.Interaction,
                      file: discord.Attachment):
    await interaction.response.defer(thinking=True)
    if not is_admin(interaction.user.id):
        await interaction.followup.send("Admins only.", ephemeral=True)
        return
    if not file.filename.endswith(".csv"):
        await interaction.followup.send("Please upload a .csv file.", ephemeral=True)
        return

    try:
        data = await file.read()
        text = data.decode("utf-8")
    except Exception as e:
        await interaction.followup.send(f"Could not read file: {e}")
        return

    # Parse CSV
    import csv
    import io as _io
    reader = csv.DictReader(_io.StringIO(text))

    updated = 0
    errors = 0
    match_info = {}

    for row in reader:
        try:
            player_id = row.get("player_id", "").strip()
            if not player_id or player_id == "0":
                # This is the match info row — skip
                if row.get("home_team_id"):
                    match_info = row
                continue

            goals = int(row.get("goals", 0) or 0)
            assists = int(row.get("assists", 0) or 0)
            tackles = int(row.get("tackles", 0) or 0)
            saves = int(row.get("saves", 0) or 0)
            motm = int(row.get("motm", 0) or 0)
            yellow = int(row.get("yellow", 0) or 0)
            red = int(row.get("red", 0) or 0)

            # Skip if all zeros (player didn't do anything notable but still played)
            if goals + assists + tackles + saves + motm + yellow + red == 0:
                # Still add an appearance
                pass

            # Find the player by PES ID (the CSV has in-game player IDs)
            # We need to match against our database's pes_id field
            pid_str = str(player_id)
            player = None
            for p in P.all_players():
                if p.get("pes_id") == pid_str:
                    player = p
                    break

            if not player:
                # Try by slug-based search of the name if CSV has one
                csv_name = row.get("player_name", "").strip()
                if csv_name:
                    results = P.search(csv_name, limit=1)
                    if results:
                        player = results[0]

            if player:
                _imp_s = L.active_season(interaction.guild_id)
                _imp_sid = _imp_s["id"] if _imp_s else None
                E.add_player_stats(
                    interaction.guild_id, player["key"],
                    goals=goals, assists=assists, tackles=tackles,
                    saves=saves, motm=motm, yellow=yellow, red=red,
                    season_id=_imp_sid,
                )
                updated += 1
            else:
                errors += 1
        except Exception as e:
            errors += 1

    # Build response
    lines = [f"**Match imported successfully.**"]
    lines.append(f"Players updated: **{updated}**")
    if errors:
        lines.append(f"Could not match: **{errors}** (player not found in database)")
    if match_info:
        hs = match_info.get("home_score", "?")
        as_ = match_info.get("away_score", "?")
        lines.append(f"Score: **{hs}-{as_}**")
    lines.append("")
    lines.append("Stats are now live. Use `/topscorers` or `/playerstats` to see them.")

    await interaction.followup.send("\n".join(lines))


# ==========================================================================
#  HELP
# ==========================================================================
class AdminHelpView(discord.ui.View):
    """Button that reveals admin commands. Only shows for admins."""

    def __init__(self):
        super().__init__(timeout=120)

    @discord.ui.button(label="Admin Commands", style=discord.ButtonStyle.secondary, row=0)
    async def show_admin(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_admin(interaction.user.id):
            await interaction.response.send_message("Admins only.", ephemeral=True)
            return
        e = discord.Embed(
            title="Admin Commands",
            color=C.OBSIDIAN,
        )
        e.add_field(name="Auction Control", value=(
            "`/phase <group>` - set position day (FWD/MID/DEF/GK/ALL)\n"
            "`/next` - drop next player (queue or top available)\n"
            "`/drop <name>` - nominate a specific player\n"
            "`/queue <action>` - scripted list (add, bulk, shuffle)\n"
            "`/cancel` - stop the running auction"
        ), inline=False)
        e.add_field(name="Season & League", value=(
            "`/season setup` - create a new season\n"
            "`/season add @user` - add a manager\n"
            "`/season signup` - add managers via message reactions\n"
            "`/season draw` - team draw ceremony\n"
            "`/season start` - generate fixtures and go live\n"
            "`/season end` / `/season clear` - end or clean up"
        ), inline=False)
        e.add_field(name="Results & Stats", value=(
            "`/quickresult <fixture> <2-1>` - enter result + stats\n"
            "`/updatestats <player>` - add match stats manually\n"
            "`/resetstats` - wipe all stats for a new season\n"
            "`/importmatch` - upload a FL26 CSV"
        ), inline=False)
        e.add_field(name="Manager & Economy", value=(
            "`/give @user <amount>` - grant budget\n"
            "`/reset @user` - reset a manager\n"
            "`/resetall` - reset everyone\n"
            "`/toggletrades <true/false>` - enable/disable trades\n"
            "`/export` / `/exportfl26` - download squad data"
        ), inline=False)
        e.set_footer(text="Made by mumu_111111")
        await interaction.response.send_message(embed=e, ephemeral=True)


@bot.tree.command(description="Show all commands.")
async def help(interaction: discord.Interaction):
    await interaction.response.defer()
    e = discord.Embed(
        title="Football Auction Bot",
        description=(
            "Build your squad by winning live auctions.\n"
            f"Every manager starts with **{E.money(Config.STARTING_BALANCE)}**."
        ),
        color=C.AMBER,
    )
    e.add_field(name="Your Squad", value=(
        "`/balance` - check your budget\n"
        "`/profile` - net worth and top players\n"
        "`/team` - your starting XI card\n"
        "`/squad` - full squad overview\n"
        "`/bench` - your substitutes\n"
        "`/leaderboard` - richest managers\n"
        "`/needs` - what positions you still need\n"
        "`/check` - squad requirements status"
    ), inline=False)
    e.add_field(name="Players", value=(
        "`/player <name>` - view a player card\n"
        "`/playerstats <name>` - match stats for a player\n"
        "`/compare <p1> <p2>` - head-to-head duel\n"
        "`/matchup [@user]` - your XI vs a rival\n"
        "`/pool` - browse available players\n"
        "`/topscorers` - golden boot race"
    ), inline=False)
    e.add_field(name="League", value=(
        "`/season info` - current season status\n"
        "`/fixtures` - upcoming matches\n"
        "`/table` - league standings\n"
        "`/bracket` - knockout bracket\n"
        "`/h2h @user1 @user2` - head-to-head record\n"
        "`/archive` - past seasons"
    ), inline=False)
    e.add_field(name="Transfers & Activity", value=(
        "`/trade @user` - offer a player trade\n"
        "`/trades` - your pending offers\n"
        "`/sold` - recent sales\n"
        "`/soldsearch` - search auction history\n"
        "`/draftrecap` - draft summary\n"
        "`/watch` - get pinged when a target goes up\n"
        "`/formation` - set your formation\n"
        "`/tactics` - view your FL26 tactics"
    ), inline=False)
    e.set_footer(text="Made by mumu_111111")
    view = AdminHelpView() if is_admin(interaction.user.id) else None
    await interaction.followup.send(embed=e, view=view)


# --------------------------------------------------------------------------
if __name__ == "__main__":
    if not Config.TOKEN or Config.TOKEN == "put-your-bot-token-here":
        raise SystemExit(f"{EM.e('x')} No bot token set. Copy .env.example to .env and add DISCORD_TOKEN.")
    bot.run(Config.TOKEN)
