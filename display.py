"""
Display builders for rich embeds.

The headline feature is build_team_embed(): renders a manager's best XI as a
tactics-board formation (4-3-3) plus their bench, squad rating and value.
"""
import discord

import economy as E
import players as P


def _chip(p: dict) -> str:
    """A single player chip: 'Name (OVR)'."""
    name = p["name"]
    if len(name) > 18:
        name = name[:17] + "..."
    return f"{P.flag(p['country'])} {name} ({p['ovr']})"


def _line(players: list) -> str:
    if not players:
        return "_(empty)_"
    return "   ".join(_chip(p) for p in players)


def build_team_embed(guild_id: int, member: discord.Member) -> discord.Embed:
    squad = E.get_squad(guild_id, member.id)
    if not squad:
        return discord.Embed(
            title=f"{member.display_name}'s team",
            description="No players yet. Win some in the auction!",
            color=0x95A5A6,
        )

    groups = {"GK": [], "DEF": [], "MID": [], "FWD": []}
    for p in squad:
        groups.setdefault(p["group"], []).append(p)
    for g in groups.values():
        g.sort(key=lambda p: p["ovr"], reverse=True)

    xi = {
        "GK": groups["GK"][:1],
        "DEF": groups["DEF"][:4],
        "MID": groups["MID"][:3],
        "FWD": groups["FWD"][:3],
    }
    xi_keys = {p["key"] for seg in xi.values() for p in seg}

    bench = [p for p in squad if p["key"] not in xi_keys]
    bench.sort(key=lambda p: (p["group"], -p["ovr"]))

    xi_ovrs = [p["ovr"] for seg in xi.values() for p in seg]
    rating = round(sum(xi_ovrs) / len(xi_ovrs)) if xi_ovrs else 0
    avg_all = round(sum(p["ovr"] for p in squad) / len(squad)) if squad else 0

    colour = P.TIER_COLOUR.get(
        "GoldRare" if rating >= 86 else "Gold" if rating >= 75
        else "Silver" if rating >= 65 else "Bronze", 0x3498DB
    )

    e = discord.Embed(
        title=f"{member.display_name} - Starting XI",
        description=(
            f"**4-3-3** - Squad rating **{rating}** - "
            f"{len(squad)} players - {E.money(E.squad_value(squad))} value"
        ),
        color=colour,
    )
    e.add_field(name="Goalkeeper",  value=_line(xi["GK"]) or "_(none)_", inline=False)
    e.add_field(name="Defence (4)",  value=_line(xi["DEF"]) or "_(none)_", inline=False)
    e.add_field(name="Midfield (3)", value=_line(xi["MID"]) or "_(none)_", inline=False)
    e.add_field(name="Attack (3)",   value=_line(xi["FWD"]) or "_(none)_", inline=False)

    if bench:
        e.add_field(name=f"Bench ({len(bench)})", value=_line(bench), inline=False)

    bal = E.get_balance(guild_id, member.id)
    e.add_field(name="Budget left", value=E.money(bal), inline=True)
    e.add_field(name="Avg OVR (all)", value=str(avg_all), inline=True)
    e.set_thumbnail(url=member.display_avatar.url)
    e.set_footer(text="Squad rating = average OVR of your best XI")
    return e


def build_squad_embed(guild_id: int, member: discord.Member) -> discord.Embed:
    """Full squad list grouped by position group."""
    squad = E.get_squad(guild_id, member.id)
    if not squad:
        return discord.Embed(
            title=f"{member.display_name}'s squad",
            description="No players yet. Win some in the auction!",
            color=0x95A5A6,
        )

    groups = {"GK": [], "DEF": [], "MID": [], "FWD": []}
    for p in squad:
        groups.setdefault(p["group"], []).append(p)

    labels = {"GK": "Goalkeepers", "DEF": "Defenders",
              "MID": "Midfielders", "FWD": "Forwards"}

    e = discord.Embed(
        title=f"{member.display_name}'s squad ({len(squad)})",
        color=0x1ABC9C,
    )
    for gkey in P.PHASE_ORDER:
        players = sorted(groups.get(gkey, []), key=lambda p: p["ovr"], reverse=True)
        if not players:
            continue
        lines = []
        for p in players:
            lines.append(
                f"{P.flag(p['country'])} **{p['name']}** - {p['position']} - "
                f"**{p['ovr']}** - _bought {E.money(p['acquired_price'])}_"
            )
        e.add_field(name=f"{labels[gkey]} ({len(players)})",
                    value="\n".join(lines), inline=False)

    e.add_field(name="Budget left",
                value=E.money(E.get_balance(guild_id, member.id)), inline=True)
    e.add_field(name="Squad value",
                value=E.money(E.squad_value(squad)), inline=True)
    e.set_footer(text=f"View their best XI with /team")
    return e


def build_player_embed(p: dict) -> discord.Embed:
    is_gk = p["position"] == "GK"
    e = discord.Embed(
        title=f"{P.flag(p['country'])} {p['name']}  -  {p['tier']}",
        color=P.TIER_COLOUR.get(p["tier"], 0x3498DB),
    )
    e.add_field(name=f"```{p['ovr']}```",
                value=f"**{p['position']}** - {p.get('club','')}", inline=True)
    e.add_field(name="Market Value", value=E.money(p["value"]), inline=True)
    e.add_field(name="Stats", value=P.stat_bars(p["stats"], is_gk), inline=False)
    return e
