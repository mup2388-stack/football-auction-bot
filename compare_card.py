"""
Comparison cards — Player Duel + Team Matchup.

VISUAL LANGUAGE: a symmetric "duel" split by a center spine.
  - Player A  ->  BRIGHT BLUE  (100,180,255)
  - Player B  ->  CORAL        (255,130,100)
Tug-of-war diverging bars grow from the center toward whoever is stronger.
Winner stays saturated, loser dims.

DESIGN NOTES (what makes it premium, not slop):
  - OVR numbers are BARE confident display type (Anton/Bebas via FD) — never
    trapped in a bordered rectangle box. A number in a box reads as a generic
    dashboard widget. A number in a dramatic condensed font reads as a stat
    programme.
  - All text uses FD() (Anton/BebasNeue) for numbers + labels and
    F(bold=True) (Oswald Bold) for names — the user's installed display fonts.
  - Pixel-exact vertical centering via _vc_* so nothing drifts or overlaps.
"""
import io
from PIL import Image, ImageDraw, ImageFont, ImageFilter

import economy as E
import players as P
from squad_card import (F, FD, fetch_face, silhouette, circular,
                        text_centered, fit_font, TIER_COLORS)

# -- Deep Ocean-Coral family (matches player_card.py / squad_card.py) -------
BG_TOP    = (8, 18, 32)
BG_BOTTOM = (3, 8, 16)
PANEL     = (14, 28, 44)
PANEL_HI  = (20, 38, 58)

C_NAME   = (250, 248, 240)
C_LABEL  = (130, 150, 175)
C_INFO   = (160, 180, 200)
C_DIM    = (95, 105, 120)
TRACK    = (30, 40, 54)

SIDE_A      = (100, 180, 255)   # bright blue
SIDE_A_DIM  = (40, 64, 92)
SIDE_B      = (255, 130, 100)   # coral
SIDE_B_DIM  = (96, 52, 42)

WIN_GOLD = (255, 200, 100)

_OUTFIELD = [("PAC", "pac"), ("SHO", "sho"), ("PAS", "pas"),
             ("DRI", "dri"), ("DEF", "def"), ("PHY", "phy")]
_GK = [("DIV", "div"), ("HAN", "han"), ("KIC", "kic"),
       ("REF", "ref"), ("SPD", "spd"), ("POS", "pos")]


# --------------------------------------------------------------------------
#  primitives
# --------------------------------------------------------------------------
def _gradient_bg(w, h, top=BG_TOP, bottom=BG_BOTTOM):
    col = Image.new("RGB", (1, h))
    px = col.load()
    for y in range(h):
        r = y / max(1, h - 1)
        px[0, y] = (int(top[0] + (bottom[0] - top[0]) * r),
                    int(top[1] + (bottom[1] - top[1]) * r),
                    int(top[2] + (bottom[2] - top[2]) * r))
    return col.resize((w, h)).convert("RGBA")


def _glow(canvas, cx, cy, r, colour, blur=44):
    blob = Image.new("RGBA", (r * 2, r * 2), (0, 0, 0, 0))
    ImageDraw.Draw(blob).ellipse([0, 0, r * 2 - 1, r * 2 - 1], fill=colour)
    blob = blob.filter(ImageFilter.GaussianBlur(blur))
    canvas.alpha_composite(blob, (cx - r, cy - r))


def _rounded(d, xy, radius=10, **kw):
    d.rounded_rectangle(xy, radius=radius, **kw)


def _b(draw, text, fnt):
    return draw.textbbox((0, 0), text, font=fnt)


def _vc_left(d, x, cy, text, fnt, fill):
    """Left-aligned, vertically centered at cy (pixel-exact)."""
    bb = _b(d, text, fnt)
    h = bb[3] - bb[1]
    d.text((x, cy - h / 2 - bb[1]), text, font=fnt, fill=fill)


def _vc_right(d, x, cy, text, fnt, fill):
    """Right-aligned, vertically centered at cy."""
    bb = _b(d, text, fnt)
    w, h = bb[2] - bb[0], bb[3] - bb[1]
    d.text((x - w, cy - h / 2 - bb[1]), text, font=fnt, fill=fill)


def _vc_center(d, cx, cy, text, fnt, fill):
    bb = _b(d, text, fnt)
    w, h = bb[2] - bb[0], bb[3] - bb[1]
    d.text((cx - w / 2 - bb[0], cy - h / 2 - bb[1]), text, font=fnt, fill=fill)


def _text_right(d, x, y, text, fnt, fill):
    w = _b(d, text, fnt)[2]
    d.text((x - w, y), text, font=fnt, fill=fill)


def _duel_bar(d, cx, y, half_w, a_val, b_val, h=12):
    """Diverging tug-of-war bar. A grows LEFT, B grows RIGHT.
    half_w is POSITIONAL — never pass as a keyword."""
    _rounded(d, [cx - half_w, y, cx + half_w, y + h], radius=h // 2, fill=TRACK)
    aw = int(half_w * min(a_val, 99) / 99)
    if aw > 0:
        col = SIDE_A if a_val >= b_val else SIDE_A_DIM
        _rounded(d, [cx - aw, y, cx, y + h], radius=h // 2, fill=col)
    bw = int(half_w * min(b_val, 99) / 99)
    if bw > 0:
        col = SIDE_B if b_val >= a_val else SIDE_B_DIM
        _rounded(d, [cx, y, cx + bw, y + h], radius=h // 2, fill=col)
    d.line([cx, y - 3, cx, y + h + 3], fill=(180, 190, 205), width=2)


def _face(player, guild_id, r, ring_colour):
    fu = E.get_face_url(player["key"])
    raw = fetch_face(fu) if fu else None
    if raw is None:
        raw = silhouette(r * 2, (20, 24, 32))
    return circular(raw, r * 2, ring_w=4, ring_colour=ring_colour)


def _club_display(player, guild_id):
    base = player.get("club", "") or ""
    if guild_id:
        owner = E.get_player_owner(guild_id, player["key"])
        if owner and owner[1]:
            return owner[1]
    return base or "Free Agent"


# ===========================================================================
#  PLAYER  vs  PLAYER
# ===========================================================================
def render_player_duel(player_a, player_b, guild_id=None):
    W, H = 1280, 900
    canvas = _gradient_bg(W, H)
    d = ImageDraw.Draw(canvas)

    a_gk = player_a.get("position") == "GK"
    b_gk = player_b.get("position") == "GK"
    cats = _GK if (a_gk and b_gk) else _OUTFIELD
    sa = player_a.get("stats", {})
    sb = player_b.get("stats", {})

    a_wins = sum(1 for _, k in cats if sa.get(k, 0) > sb.get(k, 0))
    b_wins = sum(1 for _, k in cats if sb.get(k, 0) > sa.get(k, 0))

    _duel_header(canvas, d, player_a, guild_id, side="A", W=W)
    _duel_header(canvas, d, player_b, guild_id, side="B", W=W)
    d = ImageDraw.Draw(canvas)

    cx = W // 2
    # centre VS — thin ring only, no fill, no shadow
    my = 110
    mr = 40
    d.ellipse([cx - mr, my - mr, cx + mr, my + mr],
              outline=(140, 150, 170), width=2)
    _vc_center(d, cx, my, "VS", FD(32), C_NAME)

    # section title
    ty = 250
    _vc_center(d, cx, ty, "HEAD TO HEAD", FD(24), C_LABEL)
    d.line([cx - 80, ty + 18, cx + 80, ty + 18], fill=(60, 75, 95), width=2)

    # stat rows (tug-of-war bars kept)
    row_h = 56
    bar_half = 250
    sy = ty + 38
    for i, (label, key) in enumerate(cats):
        av = sa.get(key, 0)
        bv = sb.get(key, 0)
        ry = sy + i * row_h

        _rounded(d, [40, ry, W - 40, ry + row_h - 8], radius=10, fill=PANEL)
        d = ImageDraw.Draw(canvas)

        row_cy = ry + (row_h - 8) / 2
        a_col = SIDE_A if av >= bv else C_DIM
        b_col = SIDE_B if bv >= av else C_DIM
        # big display-font values (no box)
        _vc_left(d, 78, row_cy, str(av), FD(30), a_col)
        _vc_right(d, W - 78, row_cy, str(bv), FD(30), b_col)

        _vc_center(d, cx, ry + 10, label, F(14, bold=True), C_LABEL)
        _duel_bar(d, cx, ry + 30, bar_half, av, bv, h=11)
        d = ImageDraw.Draw(canvas)

    # verdict strip
    vy = sy + len(cats) * row_h + 6
    _rounded(d, [40, vy, W - 40, vy + 46], radius=10, fill=PANEL_HI)
    d = ImageDraw.Draw(canvas)
    if a_wins > b_wins:
        verdict = f"{player_a['name'].split()[-1].upper()} WINS {a_wins} OF {len(cats)}"
        vcol = SIDE_A
    elif b_wins > a_wins:
        verdict = f"{player_b['name'].split()[-1].upper()} WINS {b_wins} OF {len(cats)}"
        vcol = SIDE_B
    else:
        verdict = f"DEAD HEAT  {a_wins}-{b_wins}"
        vcol = WIN_GOLD
    _vc_center(d, cx, vy + 23, verdict, F(17, bold=True), vcol)

    # key facts — label flanked by values, vertically centered, display font
    fy = vy + 64
    facts = [
        ("AGE", player_a.get("age"), player_b.get("age")),
        ("HEIGHT", player_a.get("height"), player_b.get("height")),
        ("WEIGHT", player_a.get("weight"), player_b.get("weight")),
        ("FOOT", player_a.get("foot"), player_b.get("foot")),
        ("WEAK FOOT", player_a.get("weak_foot"), player_b.get("weak_foot")),
        ("SKILLS", len(player_a.get("skills", [])), len(player_b.get("skills", []))),
    ]
    col_w = (W - 80) // 3
    fact_h = 46
    fact_gap = 12
    for i, (label, av, bv) in enumerate(facts):
        col = i % 3
        row = i // 3
        fx = 40 + col * col_w
        fyy = fy + row * (fact_h + fact_gap)
        card_w = col_w - 12
        _rounded(d, [fx, fyy, fx + card_w, fyy + fact_h], radius=8, fill=PANEL)
        d = ImageDraw.Draw(canvas)

        card_cx = fx + card_w / 2
        card_cy = fyy + fact_h / 2
        av_s = _fact_str(av, label == "WEAK FOOT")
        bv_s = _fact_str(bv, label == "WEAK FOOT")
        a_tc = SIDE_A if _fact_better(av, bv, label) else C_INFO
        b_tc = SIDE_B if _fact_better(bv, av, label) else C_INFO

        _vc_center(d, card_cx, card_cy, label, F(12, bold=True), C_LABEL)
        # values in display font, bigger, vertically centered with label
        _vc_left(d, fx + 18, card_cy, av_s, FD(20), a_tc)
        _vc_right(d, fx + card_w - 18, card_cy, bv_s, FD(20), b_tc)

    buf = io.BytesIO()
    canvas.convert("RGB").save(buf, "PNG", optimize=True)
    buf.seek(0)
    return buf


def _fact_str(v, is_weak_foot):
    if v is None:
        return "-"
    if is_weak_foot:
        return f"{v}/5"
    return str(v)


def _fact_better(a, b, label):
    if a is None or b is None:
        return False
    if isinstance(a, str) or isinstance(b, str):
        return False
    return a > b


def _duel_header(canvas, d, player, guild_id, side, W):
    """Identity block. A=left/blue, B=right/coral. Big bare OVR, no box."""
    accent = SIDE_A if side == "A" else SIDE_B
    ovr = player["ovr"]
    fr = 60

    if side == "A":
        _vc_left(d, 44, 80, str(ovr), FD(58), accent)
        _vc_left(d, 50, 122, player["position"], FD(22), C_INFO)
        fcx = 250
    else:
        _text_right(d, W - 44, 56, str(ovr), FD(58), accent)
        # position right-aligned too
        _text_right(d, W - 50, 104, player["position"], FD(22), C_INFO)
        fcx = W - 250

    fi = _face(player, guild_id, fr, accent)
    canvas.paste(fi, (fcx - fi.width // 2, 122 - fi.height // 2), fi)
    d = ImageDraw.Draw(canvas)

    name = player["name"]
    club = _club_display(player, guild_id)
    if side == "A":
        nf = fit_font(d, name, 300, [28, 24, 19, 15], bold=True)
        d.text([44, 196], nf[0], font=nf[1], fill=C_NAME)
        cf = fit_font(d, club, 300, [17, 15, 13], bold=True)
        d.text([44, 230], cf[0], font=cf[1], fill=accent)
    else:
        nf = fit_font(d, name, 300, [28, 24, 19, 15], bold=True)
        _text_right(d, W - 44, 196, nf[0], nf[1], C_NAME)
        cf = fit_font(d, club, 300, [17, 15, 13], bold=True)
        _text_right(d, W - 44, 230, cf[0], cf[1], accent)


# ===========================================================================
#  TEAM  vs  TEAM
# ===========================================================================
def render_team_matchup(guild_id, user_a, user_b, name_a, name_b,
                        logo_a=None, logo_b=None, avatar_a=None, avatar_b=None):
    lineup_a, fa = E.get_lineup(guild_id, user_a)
    lineup_b, fb = E.get_lineup(guild_id, user_b)

    rows = list(zip(lineup_a, lineup_b))

    a_ovrs = [p["ovr"] for (_, p) in lineup_a if p]
    b_ovrs = [p["ovr"] for (_, p) in lineup_b if p]
    avg_a = round(sum(a_ovrs) / len(a_ovrs), 1) if a_ovrs else 0
    avg_b = round(sum(b_ovrs) / len(b_ovrs), 1) if b_ovrs else 0

    a_win = b_win = 0
    for (sa, pa), (sb, pb) in rows:
        oa = pa["ovr"] if pa else 0
        ob = pb["ovr"] if pb else 0
        if oa > ob:
            a_win += 1
        elif ob > oa:
            b_win += 1

    val_a = E.squad_value(E.get_squad(guild_id, user_a))
    val_b = E.squad_value(E.get_squad(guild_id, user_b))

    N = len(rows)
    header_h = 210
    row_h = 74
    footer_h = 96
    H = header_h + N * row_h + footer_h + 24
    W = 1380
    canvas = _gradient_bg(W, H)
    d = ImageDraw.Draw(canvas)
    cx = W // 2

    _team_header(canvas, d, name_a, avg_a, val_a, fa, logo_a, avatar_a, side="A", W=W)
    _team_header(canvas, d, name_b, avg_b, val_b, fb, logo_b, avatar_b, side="B", W=W)
    d = ImageDraw.Draw(canvas)

    # centre VS — thin ring only, no fill, no shadow
    mr = 38
    d.ellipse([cx - mr, 105 - mr, cx + mr, 105 + mr],
              outline=(140, 150, 170), width=2)
    _vc_center(d, cx, 103, "VS", FD(28), C_NAME)

    chy = header_h - 6
    _vc_center(d, cx, chy - 20, "POSITION", F(11, bold=True), C_LABEL)

    bar_half = 300
    for i, ((sa, pa), (sb, pb)) in enumerate(rows):
        ry = header_h + i * row_h
        oa = pa["ovr"] if pa else None
        ob = pb["ovr"] if pb else None
        row_cy = ry + (row_h - 8) / 2

        _rounded(d, [30, ry, W - 30, ry + row_h - 8], radius=10, fill=PANEL)
        d = ImageDraw.Draw(canvas)

        # A side: name (top) + bare big OVR number below (NO box)
        if pa:
            a_col = SIDE_A if (oa or 0) >= (ob or 0) else C_DIM
            nf = fit_font(d, pa["name"], 230, [19, 16, 14, 12], bold=True)
            d.text([64, ry + 12], nf[0], font=nf[1], fill=C_NAME)
            # OVR as bare display number — vertically centered under name area
            _vc_left(d, 66, ry + 46, str(oa), FD(26), a_col)
        else:
            d.text([64, ry + 28], "- vacant -", font=F(15), fill=C_DIM)

        # B side
        if pb:
            b_col = SIDE_B if (ob or 0) >= (oa or 0) else C_DIM
            nf = fit_font(d, pb["name"], 230, [19, 16, 14, 12], bold=True)
            _text_right(d, W - 64, ry + 12, nf[0], nf[1], C_NAME)
            _vc_right(d, W - 66, ry + 46, str(ob), FD(26), b_col)
        else:
            _text_right(d, W - 64, ry + 28, "- vacant -", F(15), fill=C_DIM)

        # center: position label + tug-of-war bar
        pos_label = (sa or {}).get("pos", "?")
        _vc_center(d, cx, ry + 14, pos_label, FD(17), C_INFO)
        _duel_bar(d, cx, ry + 38, bar_half, oa or 0, ob or 0, h=10)
        d = ImageDraw.Draw(canvas)

        # winner chevron on the bar
        if oa and ob and oa != ob:
            chev = "<" if oa > ob else ">"
            chev_col = SIDE_A if oa > ob else SIDE_B
            cy_chev = ry + 38
            if oa > ob:
                _text_right(d, cx - bar_half - 10, cy_chev - 9, chev, F(15, bold=True), chev_col)
            else:
                d.text([cx + bar_half + 10, cy_chev - 9], chev, font=F(15, bold=True), fill=chev_col)

    # footer verdict + squad-strength bar
    fyy = header_h + N * row_h + 8
    _rounded(d, [30, fyy, W - 30, fyy + footer_h - 8], radius=12, fill=PANEL_HI)
    d = ImageDraw.Draw(canvas)

    if a_win > b_win:
        verdict = f"{name_a.upper()} STRONGER IN {a_win}/{N} POSITIONS"
        vcol = SIDE_A
    elif b_win > a_win:
        verdict = f"{name_b.upper()} STRONGER IN {b_win}/{N} POSITIONS"
        vcol = SIDE_B
    else:
        verdict = f"EVEN SPLIT  {a_win}-{b_win}"
        vcol = WIN_GOLD
    _vc_center(d, cx, fyy + 22, verdict, F(18, bold=True), vcol)

    aby = fyy + 52
    _vc_center(d, cx, aby, "SQUAD STRENGTH", F(11, bold=True), C_LABEL)
    _duel_bar(d, cx, aby + 20, 260, avg_a or 0, avg_b or 0, h=12)
    d = ImageDraw.Draw(canvas)
    _vc_left(d, cx - 260 - 64, aby + 16, f"{avg_a}", FD(22), SIDE_A)
    _vc_right(d, cx + 260 + 64, aby + 16, f"{avg_b}", FD(22), SIDE_B)

    buf = io.BytesIO()
    canvas.convert("RGB").save(buf, "PNG", optimize=True)
    buf.seek(0)
    return buf


def _team_header(canvas, d, name, avg_ovr, value, formation,
                 logo_url, avatar_url, side, W):
    accent = SIDE_A if side == "A" else SIDE_B
    if side == "A":
        lx = 60; tx = 60; align_right = False
    else:
        lx = W - 60; tx = W - 60; align_right = True

    img_src = logo_url or avatar_url
    im = None
    if img_src:
        raw = fetch_face(img_src)
        if raw:
            im = circular(raw, 76, ring_w=3, ring_colour=accent)
    if im is None:
        im = circular(silhouette(76, (20, 24, 32)), 76, ring_w=3, ring_colour=accent)
    if align_right:
        canvas.paste(im, (lx - im.width, 36), im)
    else:
        canvas.paste(im, (lx, 36), im)
    d = ImageDraw.Draw(canvas)

    nf = fit_font(d, name, 360, [26, 22, 18, 14], bold=True)
    line = f"AVG {avg_ovr}  -  {formation}  -  {E.money(value)}"
    lf = fit_font(d, line, 380, [15, 13, 12], bold=True)
    if align_right:
        _text_right(d, tx, 120, nf[0], nf[1], C_NAME)
        _text_right(d, tx, 156, lf[0], lf[1], accent)
    else:
        d.text([tx, 120], nf[0], font=nf[1], fill=C_NAME)
        d.text([tx, 156], lf[0], font=lf[1], fill=accent)
