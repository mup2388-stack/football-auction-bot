"""
Standings board renderer — broadcast football graphic.

DESIGN READ: league standings checked between matches. Broadcast sports-media
language. Flat mineral dark surface, massive type hierarchy, form indicators.
Dials: VARIANCE 4, MOTION 0, DENSITY 6.

LAYOUT (impeccable layout.md):
  - 4pt base spacing scale
  - Tight grouping of name+form (related data), generous gap to stats
  - Form dots sit in their OWN column with clear air on both sides

ANTI-SLOP (impeccable bans):
  - NO side-stripe borders → full-row background tint for zones
  - NO hero-metric template → Pts is one column, not a gold beacon
  - NO eyebrow → title IS the design element
  - NO gradient bg → flat mineral surface
  - Dramatic weight contrast (Anton display 26px vs Oswald regular 15px)
"""
import io
from PIL import Image, ImageDraw

import league as L


# -- flat mineral palette, ONE accent, zone tints carry meaning -------------
SURFACE     = (12, 22, 36)
ZONE_UP     = (18, 42, 30)
ZONE_DOWN   = (40, 18, 20)
LEADER      = (28, 36, 22)

INK         = (244, 248, 252)
INK_BODY    = (196, 210, 230)
INK_MUTED   = (120, 138, 162)
INK_DIM     = (78, 92, 112)
DIVIDER     = (28, 40, 58)

ACCENT      = (120, 188, 255)

FORM_W      = (46, 204, 113)
FORM_D      = (241, 196, 64)
FORM_L      = (231, 76, 60)
FORM_EMPTY  = (38, 48, 64)


def _F(size, bold=False):
    from squad_card import F
    return F(size, bold=bold)

def _FD(size):
    from squad_card import FD
    return FD(size)


def _b(draw, text, fnt):
    return draw.textbbox((0, 0), text, font=fnt)


def _vc_right(d, x_right, cy, text, fnt, fill):
    bb = _b(d, text, fnt)
    w, h = bb[2] - bb[0], bb[3] - bb[1]
    d.text((x_right - w, cy - h / 2 - bb[1]), text, font=fnt, fill=fill)


def _vc_left(d, x, cy, text, fnt, fill):
    bb = _b(d, text, fnt)
    h = bb[3] - bb[1]
    d.text((x, cy - h / 2 - bb[1]), text, font=fnt, fill=fill)


def _form_dots(d, x, cy, form, r=6, gap=16):
    """Draw last-5 form dots. x is the LEFT edge of the dots cluster."""
    for i in range(5):
        cx = x + i * gap + r
        res = form[i] if i < len(form) else None
        col = {"W": FORM_W, "D": FORM_D, "L": FORM_L}.get(res, FORM_EMPTY)
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=col)


def _form_width(gap=16, r=6):
    """Pixel width of a 5-dot cluster (for column layout math)."""
    return 4 * gap + 2 * r


def render_standings(rows, title="STANDINGS", subtitle=None,
                     zone_up=4, zone_down=0, season_id=None,
                     stage="league", group=None):
    n = len(rows)
    W = 1120
    PAD = 48
    ROW_H = 44
    title_h = 96
    header_h = 28
    H = title_h + header_h + n * ROW_H + 20

    canvas = Image.new("RGBA", (W, H), SURFACE + (255,))
    d = ImageDraw.Draw(canvas)

    # ── title ────────────────────────────────────────────────────────────
    _vc_left(d, PAD, 44, title, _FD(48), INK)
    if subtitle:
        _vc_left(d, PAD, 80, subtitle, _F(14, bold=True), INK_MUTED)
    played = sum(r["P"] for r in rows) // 2 if rows else 0
    _vc_right(d, W - PAD, 48, f"{played} PLAYED", _F(13, bold=True), INK_MUTED)

    # ── column geometry (right-anchored) ────────────────────────────────
    right = W - PAD
    cols = {
        "Pts": right - 4,
        "GD":  right - 56,
        "GA":  right - 100,
        "GF":  right - 144,
        "L":   right - 180,
        "D":   right - 216,
        "W":   right - 252,
        "P":   right - 288,
    }
    # FORM column: own region with clear air on BOTH sides (the overlap fix)
    form_w = _form_width(16, 6)
    form_x = cols["P"] - 60 - form_w   # 60px gutter before stats, left-anchored
    team_x = PAD + 40

    # ── header ───────────────────────────────────────────────────────────
    hy = title_h + header_h // 2
    _vc_left(d, PAD, hy, "#", _F(12, bold=True), INK_DIM)
    _vc_left(d, team_x, hy, "CLUB", _F(12, bold=True), INK_DIM)
    _vc_left(d, form_x, hy, "FORM", _F(12, bold=True), INK_DIM)
    for key in ("P", "W", "D", "L", "GF", "GA", "GD"):
        _vc_right(d, cols[key], hy, key, _F(12, bold=True), INK_DIM)
    _vc_right(d, cols["Pts"], hy, "PTS", _F(12, bold=True), INK_MUTED)
    d.line([PAD, title_h + header_h, W - PAD, title_h + header_h],
           fill=DIVIDER, width=1)

    # ── form data ────────────────────────────────────────────────────────
    form_map = {}
    if season_id:
        for r in rows:
            form_map[r["user_id"]] = L.recent_form(
                season_id, r["user_id"], limit=5, stage=stage, group=group)

    # ── body ─────────────────────────────────────────────────────────────
    num_reg = _F(15, bold=False)
    num_pts = _F(17, bold=True)

    for i, r in enumerate(rows):
        ry = title_h + header_h + i * ROW_H
        row_cy = ry + ROW_H / 2
        rank = i + 1

        # full-row zone tint (NOT a side stripe)
        row_bg = None
        if rank == 1:
            row_bg = LEADER
        elif zone_up and rank <= zone_up:
            row_bg = ZONE_UP
        elif zone_down and rank > n - zone_down:
            row_bg = ZONE_DOWN
        if row_bg:
            d.rectangle([0, ry, W, ry + ROW_H], fill=row_bg)

        if i > 0:
            d.line([PAD, ry, W - PAD, ry], fill=DIVIDER, width=1)

        # position — massive display type
        if rank == 1:
            pos_col = (255, 220, 130)
        elif zone_up and rank <= zone_up:
            pos_col = (130, 220, 160)
        else:
            pos_col = INK_BODY
        _vc_left(d, PAD, row_cy, str(rank), _FD(26), pos_col)

        # team name — width capped so it never collides with form column
        name_max = form_x - team_x - 24
        name = _fit_name(d, r.get("team_name") or "?", name_max, _F(17, bold=True))
        name_col = INK if rank <= (zone_up or 1) else INK_BODY
        _vc_left(d, team_x + 22, row_cy, name, _F(17, bold=True), name_col)
        try:
            import club_logos as CL
            logo = CL.get_club_logo(r.get("team_name", ""), 22)
            canvas.paste(logo, (team_x, int(row_cy - 11)), logo)
        except Exception:
            pass

        # form dots — in their own column, clear air both sides
        form = form_map.get(r["user_id"], [])
        _form_dots(d, form_x, row_cy, form, r=6, gap=16)

        # stats
        for key in ("P", "W", "D", "L", "GF", "GA"):
            _vc_right(d, cols[key], row_cy, str(r[key]), num_reg, INK_BODY)
        gd = r["GD"]
        gd_s = f"{gd:+d}" if gd != 0 else "0"
        _vc_right(d, cols["GD"], row_cy, gd_s, num_reg, INK_BODY)
        _vc_right(d, cols["Pts"], row_cy, str(r["Pts"]), num_pts, INK)

    buf = io.BytesIO()
    canvas.convert("RGB").save(buf, "PNG", optimize=True)
    buf.seek(0)
    return buf


def _fit_name(d, name, max_w, fnt):
    """Truncate name with ellipsis if wider than max_w."""
    if _b(d, name, fnt)[2] <= max_w:
        return name
    while len(name) > 2:
        name = name[:-1]
        if _b(d, name + "…", fnt)[2] <= max_w:
            return name + "…"
    return name[:2] + "…"


def render_groups(grouped_rows, subtitle=None, zone_up=2, zone_down=0,
                  season_id=None):
    import math as _math
    W = 1120
    PAD = 36
    main_title_h = 96
    gap_x = 24
    gap_y = 22

    n_groups = len(grouped_rows)
    n_cols = 2 if n_groups <= 8 else 3
    n_rows = _math.ceil(n_groups / n_cols)

    col_w = (W - 2 * PAD - gap_x * (n_cols - 1)) // n_cols
    max_rows_per_group = max(len(rows) for _, rows in grouped_rows)
    col_block_h = 30 + 24 + max_rows_per_group * 36 + 8

    grid_h = n_rows * col_block_h + (n_rows - 1) * gap_y
    H = main_title_h + grid_h + 20

    canvas = Image.new("RGBA", (W, H), SURFACE + (255,))
    d = ImageDraw.Draw(canvas)

    _vc_left(d, PAD, 44, "GROUP STAGE", _FD(48), INK)
    if subtitle:
        _vc_left(d, PAD, 80, subtitle, _F(14, bold=True), INK_MUTED)
    played = sum(r["P"] for _, rows in grouped_rows for r in rows) // 2
    _vc_right(d, W - PAD, 48, f"{played} PLAYED", _F(13, bold=True), INK_MUTED)

    for idx, (label, rows) in enumerate(grouped_rows):
        col = idx % n_cols
        row = idx // n_cols
        x0 = PAD + col * (col_w + gap_x)
        y0 = main_title_h + row * (col_block_h + gap_y)
        _draw_group(canvas, d, rows, x0, y0, col_w, title=label,
                    zone_up=zone_up, season_id=season_id, group=label)

    buf = io.BytesIO()
    canvas.convert("RGB").save(buf, "PNG", optimize=True)
    buf.seek(0)
    return buf


def _draw_group(canvas, d, rows, x0, y0, col_w, title, zone_up=0,
                season_id=None, group=None):
    n = len(rows)
    ROW_H = 36
    header_h = 22
    title_h = 28
    inner = 12
    right = x0 + col_w - inner

    _vc_left(d, x0 + inner, y0 + title_h / 2, f"GROUP {title}",
             _FD(22), ACCENT)

    body_top = y0 + title_h
    cols = {
        "Pts": right,
        "GA":  right - 28,
        "GF":  right - 52,
        "L":   right - 76,
        "D":   right - 100,
        "W":   right - 124,
        "P":   right - 148,
    }
    # form column — own region with clear gutters (the overlap fix)
    form_w = _form_width(11, 4)
    form_x = cols["P"] - 28 - form_w
    team_x = x0 + inner + 18

    hy = body_top + header_h // 2
    _vc_left(d, x0 + inner, hy, "#", _F(9, bold=True), INK_DIM)
    _vc_left(d, team_x, hy, "CLUB", _F(9, bold=True), INK_DIM)
    _vc_left(d, form_x, hy, "FORM", _F(9, bold=True), INK_DIM)
    for key in ("P", "W", "D", "L", "GF", "GA"):
        _vc_right(d, cols[key], hy, key, _F(9, bold=True), INK_DIM)
    _vc_right(d, cols["Pts"], hy, "PTS", _F(9, bold=True), INK_MUTED)
    d.line([x0 + 4, body_top + header_h, right, body_top + header_h],
           fill=DIVIDER, width=1)

    form_map = {}
    if season_id:
        for r in rows:
            form_map[r["user_id"]] = L.recent_form(
                season_id, r["user_id"], limit=5, stage="group", group=group)

    for i, r in enumerate(rows):
        ry = body_top + header_h + i * ROW_H
        row_cy = ry + ROW_H / 2
        rank = i + 1

        if zone_up and rank <= zone_up:
            d.rectangle([x0, ry, x0 + col_w, ry + ROW_H], fill=ZONE_UP)
        if i > 0:
            d.line([x0 + 4, ry, right, ry], fill=DIVIDER, width=1)

        pos_col = (255, 220, 130) if rank == 1 else (
            (130, 220, 160) if zone_up and rank <= zone_up else INK_BODY)
        _vc_left(d, x0 + inner + 2, row_cy, str(rank), _FD(17), pos_col)

        name_max = form_x - team_x - 8
        name = _fit_name(d, r.get("team_name") or "?", name_max, _F(13, bold=True))
        name_col = INK if rank <= zone_up else INK_BODY
        _vc_left(d, team_x + 18, row_cy, name, _F(13, bold=True), name_col)
        try:
            import club_logos as CL
            logo = CL.get_club_logo(r.get("team_name", ""), 18)
            canvas.paste(logo, (team_x, int(row_cy - 9)), logo)
        except Exception:
            pass

        form = form_map.get(r["user_id"], [])
        _form_dots(d, form_x, row_cy, form, r=4, gap=11)

        for key in ("P", "W", "D", "L", "GF", "GA"):
            _vc_right(d, cols[key], row_cy, str(r[key]), _F(12, bold=False), INK_BODY)
        _vc_right(d, cols["Pts"], row_cy, str(r["Pts"]), _F(13, bold=True), INK)
