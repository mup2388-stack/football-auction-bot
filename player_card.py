"""
THE Player Detail Card - Deep Ocean + Coral palette.

Background: deep ocean blue gradient
Accents: bright blue (OVR/headers) + coral (club) + sand gold (nation)
"""
import io
import math
from PIL import Image, ImageDraw, ImageFont, ImageFilter

import economy as E
import players as P
from squad_card import (F, FD, fetch_face, silhouette, circular,
                        text_centered, fit_font, TIER_COLORS)

BG_TOP = (8, 18, 32)
BG_BOTTOM = (3, 8, 16)
PANEL = (14, 28, 44)
PANEL_HI = (20, 38, 58)

C_NAME    = (250, 248, 240)
C_CLUB    = (255, 130, 100)
C_NATION  = (255, 200, 100)
C_OVR     = (100, 180, 255)
C_HEADER  = (100, 180, 255)
C_LABEL   = (130, 150, 175)
C_INFO    = (160, 180, 200)
C_SKILL   = (175, 195, 215)
C_STYLE   = (255, 180, 100)
ACCENT    = (100, 180, 255)

PITCH_DARK = (8, 35, 20)
PITCH_LIGHT = (12, 48, 28)
PITCH_LINE = (200, 230, 220)


def sc(v):
    if v >= 90: return (57, 255, 20)
    if v >= 80: return (0, 212, 255)
    if v >= 70: return (255, 200, 0)
    if v >= 60: return (255, 140, 0)
    return (255, 60, 80)


def _star(d, cx, cy, r, c, filled=True):
    """Draw a 5-pointed star centered at (cx, cy)."""
    if not filled:
        c_outline = c
        c = (40, 44, 52)  # dark fill for empty stars
    pts = []
    for i in range(10):
        angle = math.pi / 2 + i * math.pi / 5
        radius = r if i % 2 == 0 else r * 0.40
        px = cx + radius * math.cos(angle)
        py = cy - radius * math.sin(angle)
        pts.append((px, py))
    d.polygon(pts, fill=c)
    if not filled:
        # draw outline
        d.line(pts + [pts[0]], fill=c_outline, width=1)


def _stars(d, cx, cy, filled, total, r, color):
    """Draw a row of stars centered horizontally at cx."""
    gap = r * 2.4
    total_w = gap * (total - 1)
    start_x = cx - total_w / 2
    for i in range(total):
        sx = start_x + i * gap
        _star(d, sx, cy, r, color, filled=(i < filled))


def _sbar(d, x, y, label, val, w):
    d.text([x, y], label, font=F(14), fill=C_LABEL)
    vs = str(val); vf = FD(22)
    bw = d.textbbox((0,0), vs, font=vf); vw = bw[2]-bw[0]
    d.text([x + w - vw, y - 2], vs, font=vf, fill=sc(val))
    by = y + 24
    d.rounded_rectangle([x, by, x+w-4, by+3], radius=1, fill=(35, 45, 60))
    d.rounded_rectangle([x, by, x+int((w-4)*min(val,99)/99), by+3], radius=1, fill=sc(val))


def _card(canvas, x, y, w, h, fill=PANEL):
    d = ImageDraw.Draw(canvas)
    d.rounded_rectangle([x, y, x+w, y+h], radius=10, fill=fill)


def _lbl(d, x, y, text, c=C_LABEL, sz=13):
    d.text([x, y], text, font=F(sz, bold=True), fill=c)


def _pdot(d, cx, cy, r, code, val):
    if val >= 2:
        bg = (57, 255, 20); tc = (5, 20, 8); bc = (57, 255, 20)
    elif val == 1:
        bg = (255, 200, 0); tc = (35, 25, 0); bc = (255, 200, 0)
    else:
        bg = (35, 38, 44); tc = (65, 68, 75); bc = (50, 52, 58)
    if val >= 2:
        d.ellipse([cx-r-4, cy-r-4, cx+r+4, cy+r+4], outline=(57,255,20,30), width=2)
    d.ellipse([cx-r, cy-r, cx+r, cy+r], fill=bg, outline=bc, width=1)
    text_centered(d, (cx, cy), code, F(12, bold=True), tc)


def _draw_pitch(d, x, y, w, h):
    stripes = 8
    sh = h / stripes
    for i in range(stripes):
        col = PITCH_LIGHT if i % 2 == 0 else PITCH_DARK
        d.rectangle([x, y+i*sh, x+w, y+(i+1)*sh], fill=col)
    d.rectangle([x, y, x+w, y+h], outline=PITCH_LINE, width=1)
    mid_y = y + h * 0.48
    d.line([x, mid_y, x+w, mid_y], fill=PITCH_LINE, width=1)
    ccx = x + w/2; ccr = min(w, h) * 0.09
    d.ellipse([ccx-ccr, mid_y-ccr, ccx+ccr, mid_y+ccr], outline=PITCH_LINE, width=1)
    d.ellipse([ccx-2, mid_y-2, ccx+2, mid_y+2], fill=PITCH_LINE)
    pb_w = w*0.58; pb_h = h*0.12
    pbx = x + (w-pb_w)/2
    d.rectangle([pbx, y+h-pb_h, pbx+pb_w, y+h], outline=PITCH_LINE, width=1)
    sb_w = w*0.32; sb_h = h*0.05
    sbx = x + (w-sb_w)/2
    d.rectangle([sbx, y+h-sb_h, sbx+sb_w, y+h], outline=PITCH_LINE, width=1)
    tb_h = h*0.08
    d.rectangle([pbx, y, pbx+pb_w, y+tb_h], outline=PITCH_LINE, width=1)


def _gradient_bg(w, h):
    from PIL import Image as I
    bg = I.new("RGBA", (w, h), BG_TOP + (255,))
    px = bg.load()
    for y in range(h):
        ratio = y / max(1, h - 1)
        r = int(BG_TOP[0] + (BG_BOTTOM[0] - BG_TOP[0]) * ratio)
        g = int(BG_TOP[1] + (BG_BOTTOM[1] - BG_TOP[1]) * ratio)
        b = int(BG_TOP[2] + (BG_BOTTOM[2] - BG_TOP[2]) * ratio)
        for x in range(w):
            px[x, y] = (r, g, b, 255)
    return bg


STYLE_RENAMES = {
    "Extra Frontman": "Attacking Defender",
    "Offensive Goalkeeper": "Sweeper Keeper",
}


def render_player_card(player, guild_id=None):
    W, H = 1200, 760
    canvas = _gradient_bg(W, H)

    for bx, by, br, bc in [
        (150, 100, 100, (100, 180, 255, 12)),
        (950, 650, 140, (255, 130, 100, 8)),
    ]:
        blob = Image.new("RGBA", (br*2, br*2), (0, 0, 0, 0))
        ImageDraw.Draw(blob).ellipse([0, 0, br*2-1, br*2-1], fill=bc)
        blob = blob.filter(ImageFilter.GaussianBlur(40))
        canvas.alpha_composite(blob, (bx - br, by - br))

    d = ImageDraw.Draw(canvas)

    tier = player.get("tier", "Gold")
    tc = TIER_COLORS.get(tier, TIER_COLORS["Gold"])
    is_gk = player["position"] == "GK"
    LP = 360

    _card(canvas, 12, 12, LP - 24, H - 24)
    d = ImageDraw.Draw(canvas)

    d.text([24, 24], str(player["ovr"]), font=FD(52), fill=C_OVR)
    d.text([26, 80], player["position"], font=FD(22), fill=C_INFO)

    fr = 80
    fcx, fcy = LP // 2, 170
    fu = E.get_face_url(player["key"])
    fi = None
    if fu:
        raw = fetch_face(fu)
        if raw:
            fi = circular(raw, fr*2, ring_w=4, ring_colour=ACCENT)
    if fi is None:
        fi = circular(silhouette(fr*2, (20, 24, 32)), fr*2, ring_w=4, ring_colour=ACCENT)
    canvas.paste(fi, (fcx - fi.width//2, fcy - fi.height//2), fi)
    d = ImageDraw.Draw(canvas)

    ny = 280
    nm, nf = fit_font(d, player["name"], LP - 50, [24, 20, 16, 13], bold=True)
    text_centered(d, (LP//2, ny), nm, nf, C_NAME)

    # If the player is owned, show the manager's TEAM NAME (the name they
    # chose for their squad). Otherwise fall back to the player's real club.
    display_club = player.get("club", "")
    if guild_id:
        owner = E.get_player_owner(guild_id, player["key"])
        if owner and owner[1]:
            display_club = owner[1]

    club_y = 310
    logo_size = 36
    club_fit, club_f = fit_font(d, display_club, LP - 90, [18, 16, 14, 12], bold=True)
    tw = d.textbbox((0,0), club_fit, font=club_f)
    tw = tw[2] - tw[0]

    # Club logo from assets/logos/ (priority 1) or generated badge (fallback).
    # Paste directly — do NOT wrap in circular() (that was the blue-circle slop).
    try:
        import club_logos as CL
        badge = CL.get_club_logo(display_club, logo_size)
        total_w = logo_size + 10 + tw
        logo_x = (LP - total_w) // 2
        canvas.paste(badge, (logo_x, club_y - 8 + (logo_size - badge.height) // 2), badge)
        text_x = logo_x + logo_size + 10
        d = ImageDraw.Draw(canvas)
    except Exception:
        text_x = (LP - tw) // 2
    d.text([text_x, club_y], club_fit, font=club_f, fill=C_CLUB)

    country = player.get("country", "")
    if country:
        text_centered(d, (LP//2, club_y + 35), country.upper(), F(16, bold=True), C_NATION)

    py = 378
    _card(canvas, 24, py, LP - 48, 34, fill=PANEL_HI)
    d = ImageDraw.Draw(canvas)
    items = []
    if player.get("age"): items.append(f"AGE {player['age']}")
    if player.get("height"): items.append(f"{player['height']}cm")
    if player.get("weight"): items.append(f"{player['weight']}kg")
    if items:
        text_centered(d, (LP//2, py + 17), "   ".join(items), F(15, bold=True), C_INFO)

    fy = 420
    _card(canvas, 24, fy, LP - 48, 56, fill=PANEL_HI)
    d = ImageDraw.Draw(canvas)
    foot = player.get("foot", "Right")
    weak = player.get("weak_foot", 2)
    col_mid = LP // 2
    _lbl(d, 36, fy + 8, "PREFERRED FOOT")
    d.text([36, fy + 28], foot.upper(), font=F(17, bold=True), fill=C_NAME)
    d.line([col_mid, fy + 10, col_mid, fy + 46], fill=(40, 55, 75), width=1)
    _lbl(d, col_mid + 16, fy + 8, "WEAK FOOT")
    # Stars centered in the right column
    right_center_x = col_mid + (LP - 48 - (LP // 2)) // 2 + 12
    _stars(d, right_center_x, fy + 38, weak, 5, 7, ACCENT)

    sy = 486
    style = player.get("playing_style", "")
    if style:
        style = STYLE_RENAMES.get(style, style)
        panel_x = 24
        panel_w = LP - 48
        _card(canvas, panel_x, sy, panel_w, 36, fill=PANEL_HI)
        d = ImageDraw.Draw(canvas)
        # Single line: "PLAYING STYLE" label left, style value right beside it
        _lbl(d, panel_x + 14, sy + 11, "PLAYING STYLE")
        lbl_font = F(13, bold=True)
        lbl_w = d.textbbox((0, 0), "PLAYING STYLE", font=lbl_font)[2]
        d.text([panel_x + 14 + lbl_w + 16, sy + 11],
               style.upper(), font=F(14, bold=True), fill=C_STYLE)

    skills = player.get("skills", [])
    if skills:
        sk_y = 546
        _lbl(d, 32, sk_y, f"PLAYSTYLES & SKILLS ({len(skills)})", ACCENT, sz=13)
        sx = 24; sy2 = sk_y + 18
        max_y = H - 24
        for sk in skills[:18]:
            clean = sk.replace("control", "").replace("Specialist", "").strip()
            bb = d.textbbox((0,0), clean, font=F(11, bold=True))
            sw = bb[2] - bb[0] + 10
            if sx + sw > LP - 24:
                sx = 24; sy2 += 20
            if sy2 + 16 > max_y:
                break
            d.rounded_rectangle([sx, sy2, sx+sw, sy2+16], radius=4, fill=PANEL_HI)
            d.text([sx+5, sy2+2], clean, font=F(11, bold=True), fill=C_SKILL)
            sx += sw + 4
        d = ImageDraw.Draw(canvas)

    RX = LP + 12
    RW = W - RX - 12
    GAP = 12

    all_stats = player.get("all_stats", {})

    if is_gk:
        cats = [
            ("GOALKEEPING", [("GK Awareness","GKAwareness"),("GK Catching","GKCatching"),
                            ("GK Clearing","GKClearing"),("GK Reflexes","GKReflexes"),
                            ("GK Reach","GKReach")]),
            ("PHYSICAL", [("Speed","Speed"),("Acceleration","Acceleration"),
                         ("Physical Contact","PhysicalContact"),("Stamina","Stamina"),
                         ("Balance","Balance"),("Jump","Jump")]),
            ("DISTRIBUTION", [("Low Pass","LowPass"),("Lofted Pass","LoftedPass"),
                             ("Kicking Power","KickingPower"),("Curl","Curl")]),
        ]
    else:
        cats = [
            ("PACE", [("Speed","Speed"),("Acceleration","Acceleration")]),
            ("SHOOTING", [("Finishing","Finishing"),("Heading","Heading"),
                         ("Place Kicking","PlaceKicking"),("Kicking Power","KickingPower")]),
            ("PASSING", [("Low Pass","LowPass"),("Lofted Pass","LoftedPass"),("Curl","Curl")]),
            ("DRIBBLING", [("Dribbling","Dribbling"),("Ball Control","BallControl"),
                          ("Tight Possession","TightPossession"),("Balance","Balance")]),
            ("DEFENDING", [("Defensive Awareness","DefensiveAwareness"),
                          ("Ball Winning","BallWinning"),("Aggression","Aggression")]),
            ("PHYSICAL", [("Physical Contact","PhysicalContact"),("Stamina","Stamina"),
                         ("Jump","Jump")]),
        ]

    col_w = (RW - 2*GAP) // 3
    hdr_h = 24
    srh = 28

    def bh(n): return hdr_h + 8 + n * srh + 8

    for ci, (cn, sis) in enumerate(cats):
        col = ci % 3
        row = ci // 3
        cx = RX + col * (col_w + GAP)
        row_sisters = cats[row*3:(row+1)*3]
        row_max = max(len(s) for _, s in row_sisters)
        cy = 16 + row * (bh(row_max) + GAP)
        _card(canvas, cx, cy, col_w, bh(len(sis)))
        d = ImageDraw.Draw(canvas)
        text_centered(d, (cx + col_w//2, cy + hdr_h//2), cn, FD(14), C_HEADER)
        for si, (lab, key) in enumerate(sis):
            sy2 = cy + hdr_h + 8 + si * srh
            val = all_stats.get(key, 40)
            lab_fit, _ = fit_font(d, lab, col_w - 36, [14, 13, 12, 11])
            _sbar(d, cx + 8, sy2, lab_fit, val, col_w - 16)

    r0 = max(len(cats[0][1]), len(cats[1][1]), len(cats[2][1]))
    r1 = max(len(cats[3][1]) if len(cats)>3 else 0,
             len(cats[4][1]) if len(cats)>4 else 0,
             len(cats[5][1]) if len(cats)>5 else 0)
    stats_end = 16 + bh(r0) + GAP + bh(r1) + GAP

    d = ImageDraw.Draw(canvas)

    pr = player.get("position_ratings", {})
    px = RX; py = stats_end + 4
    pw = RW; ph = H - py - 12

    _card(canvas, px, py, pw, ph, fill=(8, 30, 18))
    d = ImageDraw.Draw(canvas)
    _draw_pitch(d, px+3, py+3, pw-6, ph-6)
    d = ImageDraw.Draw(canvas)

    _lbl(d, px + 12, py + 8, "POSITION COMPATIBILITY", C_NAME, sz=14)
    lx = px + pw - 160; ly = py + 10
    d.ellipse([lx, ly+2, lx+8, ly+10], fill=(57, 255, 20))
    d.text([lx+12, ly], "Natural", font=F(13), fill=C_INFO)
    d.ellipse([lx+70, ly+2, lx+78, ly+10], fill=(255, 200, 0))
    d.text([lx+82, ly], "Familiar", font=F(13), fill=C_INFO)

    dot_r = min(16, int((pw - 32) / 10))
    ix = px + 8; iy = py + 8; iw = pw - 16; ih = ph - 16

    if is_gk:
        layout = [("GK", 0.50, 0.92)]
    else:
        layout = [
            ("LW", 0.08, 0.14), ("ST", 0.50, 0.10), ("CF", 0.50, 0.18), ("RW", 0.92, 0.14),
            ("LM", 0.10, 0.34), ("CAM", 0.50, 0.34), ("RM", 0.90, 0.34),
            ("CM", 0.50, 0.44), ("CDM", 0.50, 0.52),
            ("LWB", 0.07, 0.66), ("LB", 0.07, 0.74), ("CB", 0.35, 0.74),
            ("CB", 0.65, 0.74), ("RB", 0.93, 0.74), ("RWB", 0.93, 0.66),
            ("GK", 0.50, 0.92),
        ]

    for code, xf, yf in layout:
        dx = ix + iw * xf; dy = iy + ih * yf
        val = pr.get(code, 0)
        _pdot(d, dx, dy, dot_r, code, val)

    reg = player.get("position", "")
    for code, xf, yf in layout:
        if code == reg:
            dx = ix + iw * xf; dy = iy + ih * yf
            d.ellipse([dx-dot_r-5, dy-dot_r-5, dx+dot_r+5, dy+dot_r+5],
                     outline=ACCENT, width=2)
            break

    d = ImageDraw.Draw(canvas)

    buf = io.BytesIO()
    canvas.convert("RGB").save(buf, "PNG", optimize=True)
    buf.seek(0)
    return buf
