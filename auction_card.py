"""
Compact Auction Card v3 — anti-slop, bigger fonts, proper hierarchy.

Design principles applied:
  - Impeccable: NO side-stripe borders (banned). Background tints for grouping.
  - Taste Skill: DENSITY=5 (data-dense gaming), VARIANCE=7
  - Emil Kowalski: unseen details compound
  - 4pt spacing scale (4,8,12,16,20,24,32,40)
  - Hierarchy: BID AMOUNT > Player Name > Timer > Stats
"""
import io
import math
from PIL import Image, ImageDraw, ImageFont

import economy as E
from squad_card import (F, FD, fetch_face, silhouette, circular,
                        text_centered, fit_font, TIER_COLORS)

# ── Palette ─────────────────────────────────────────────────────────────
BG = (14, 12, 24)
PANEL = (20, 18, 36)       # background tint for grouping (no border stripes)
PANEL_HI = (28, 25, 48)    # highlighted panel
BORDER = (50, 45, 75)      # subtle full borders only
WHITE = (245, 245, 255)
T2 = (185, 180, 205)
T3 = (130, 125, 150)
ACCENT = (120, 160, 255)   # blue accent
BID_GREEN = (0, 230, 110)
BID_GOLD = (255, 210, 60)
TIMER_BLUE = (100, 200, 255)
TIMER_ORANGE = (255, 150, 50)
TIMER_RED = (255, 65, 65)


def sc(v):
    if v >= 90: return (57, 255, 20)
    if v >= 80: return (0, 212, 255)
    if v >= 70: return (255, 200, 0)
    if v >= 60: return (255, 140, 0)
    return (255, 60, 80)


def _star(d, cx, cy, r, c):
    pts = [(cx + (r if i%2==0 else r*.38)*math.cos(math.pi/2+i*math.pi/5),
            cy - (r if i%2==0 else r*.38)*math.sin(math.pi/2+i*math.pi/5)) for i in range(10)]
    d.polygon(pts, fill=c)


def _card(d, x, y, w, h, fill=PANEL):
    """Background tint card — NO side-stripe border (Impeccable ban)."""
    d.rounded_rectangle([x, y, x+w, y+h], radius=12, fill=fill)


def render_auction_card(player, current_bid, highest_bidder_name, next_min_bid,
                        time_remaining, bid_count, guild_id=None):
    W, H = 800, 440
    canvas = Image.new("RGBA", (W, H), BG + (255,))
    d = ImageDraw.Draw(canvas)

    tier = player.get("tier", "Gold")
    tc = TIER_COLORS.get(tier, TIER_COLORS["Gold"])
    light = tc["light"]
    is_gk = player["position"] == "GK"

    # ═════════════════════════════════════════════════════════════════
    # LEFT PANEL — player identity (background tint, no stripe)
    # ═════════════════════════════════════════════════════════════════
    LP = 360
    _card(d, 12, 12, LP - 24, H - 24)

    # OVR — BIG
    d.text([24, 24], str(player["ovr"]), font=FD(44), fill=light)
    d.text([26, 74], player["position"], font=FD(20), fill=T2)

    # Face
    fr = 52
    fcx, fcy = 110, 180
    fu = E.get_face_url(player["key"])
    fi = None
    if fu:
        raw = fetch_face(fu)
        if raw:
            fi = circular(raw, fr*2, ring_w=3, ring_colour=light)
    if fi is None:
        fi = circular(silhouette(fr*2, (25,22,30)), fr*2, ring_w=3, ring_colour=light)
    canvas.paste(fi, (fcx - fi.width//2, fcy - fi.height//2), fi)
    d = ImageDraw.Draw(canvas)

    # Name — BIG (right of face)
    nx = 180
    nm, nf = fit_font(d, player["name"], LP - nx - 32, [22, 20, 18, 16], bold=True)
    d.text([nx, 130], nm, font=nf, fill=WHITE)

    # Club / Team
    display_club = player.get("club", "")
    if guild_id:
        owner = E.get_player_owner(guild_id, player["key"])
        if owner and owner[1]:
            display_club = owner[1]
    if display_club:
        ct, cf = fit_font(d, display_club, LP - nx - 32, [16, 14, 12])
        d.text([nx, 160], ct, font=cf, fill=T2)

    # Nation
    country = player.get("country", "")
    if country:
        d.text([nx, 182], country.upper(), font=F(15, bold=True), fill=light)

    # Foot info — SEPARATED, clearly labeled, BIGGER
    foot_y = 230
    d.text([24, foot_y], "PREFERRED", font=F(13, bold=True), fill=T3)
    d.text([24, foot_y + 20], player.get("foot", "Right").upper(), font=F(18, bold=True), fill=WHITE)
    d.text([140, foot_y], "WEAK FOOT", font=F(13, bold=True), fill=T3)
    weak = player.get("weak_foot", 2)
    sx_s = 140; sy_s = foot_y + 24
    for i in range(5):
        _star(d, sx_s + i*20, sy_s + 6, 8, light if i < weak else (40,38,52))

    # Playing style
    style = player.get("playing_style", "")
    if style:
        renames = {"Extra Frontman": "Attacking Defender", "Offensive Goalkeeper": "Sweeper Keeper"}
        style = renames.get(style, style)
        d.text([24, foot_y + 50], style.upper(), font=F(14, bold=True), fill=light)

    # ALL 6 stats — BIGGER font
    stats = player["stats"]
    if is_gk:
        stat_list = [("DIV", stats.get("div",0)), ("HAN", stats.get("han",0)),
                     ("KIC", stats.get("kic",0)), ("REF", stats.get("ref",0)),
                     ("SPD", stats.get("spd",0)), ("POS", stats.get("pos",0))]
    else:
        stat_list = [("PAC", stats.get("pac",0)), ("SHO", stats.get("sho",0)),
                     ("PAS", stats.get("pas",0)), ("DRI", stats.get("dri",0)),
                     ("DEF", stats.get("def",0)), ("PHY", stats.get("phy",0))]

    stat_y = 310
    stat_w = (LP - 48) // 6
    for i, (lbl, val) in enumerate(stat_list):
        sx = 24 + i * stat_w
        d.text([sx, stat_y], lbl, font=F(13, bold=True), fill=T3)
        d.text([sx, stat_y + 18], str(val), font=FD(22), fill=sc(val))

    # ═════════════════════════════════════════════════════════════════
    # RIGHT PANEL — live auction (background tint, no stripe)
    # ═════════════════════════════════════════════════════════════════
    RX = 360
    RW = W - RX - 12
    _card(d, RX, 12, RW, H - 24, fill=PANEL_HI)

    # "LIVE AUCTION" header
    d.text([RX + 20, 24], "LIVE AUCTION", font=F(18, bold=True), fill=BID_GOLD)

    # Timer — text only, NO emoji
    timer_color = TIMER_BLUE
    if time_remaining <= 5:
        timer_color = TIMER_RED
    elif time_remaining <= 10:
        timer_color = TIMER_ORANGE
    d.text([RX + 20, 56], "TIME LEFT", font=F(14, bold=True), fill=T3)
    d.text([RX + 20, 76], f"{time_remaining}s", font=FD(40), fill=timer_color)

    # Current bid — THE BIGGEST ELEMENT (hierarchy)
    by = 140
    d.text([RX + 20, by], "CURRENT BID", font=F(14, bold=True), fill=T3)
    d.text([RX + 20, by + 20], f"£{current_bid:,}", font=FD(40), fill=BID_GREEN)

    # Highest bidder — show Discord username
    if highest_bidder_name:
        bname = highest_bidder_name[:22]
        d.text([RX + 20, by + 68], f"Leading: {bname}", font=F(16, bold=True), fill=WHITE)
    else:
        d.text([RX + 20, by + 68], "No bids yet", font=F(16), fill=T3)

    # Next minimum bid
    d.text([RX + 20, by + 96], "NEXT MIN BID", font=F(14, bold=True), fill=T3)
    d.text([RX + 20, by + 116], f"£{next_min_bid:,}", font=FD(28), fill=BID_GOLD)

    # Bid count + market value
    d.text([RX + 20, by + 156], f"{bid_count} bids placed", font=F(15), fill=T2)
    mv = player.get("value", 0)
    if mv:
        d.text([RX + 20, by + 178], f"Market Value: £{mv:,}", font=F(14), fill=T3)

    # Status
    if time_remaining <= 5:
        d.text([RX + 20, by + 202], "GOING TWICE!", font=F(18, bold=True), fill=TIMER_RED)
    elif time_remaining <= 10:
        d.text([RX + 20, by + 202], "GOING ONCE!", font=F(18, bold=True), fill=TIMER_ORANGE)

    buf = io.BytesIO()
    canvas.convert("RGB").save(buf, "PNG", optimize=True)
    buf.seek(0)
    return buf
