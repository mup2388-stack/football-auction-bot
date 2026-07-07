"""
Top Scorers card renderer — Golden Boot race graphic.

Matches the standings_card design language exactly:
  - Flat mineral dark surface, NO gradients
  - Wide horizontal table layout (1120px)
  - Right-anchored column geometry (nothing overlaps)
  - 3-letter country codes (NOT emoji flags — PIL renders emoji as boxes)
  - _fit_name truncation so names never collide with stats
  - ONE accent (amber) — reserved for goals + leader row
  - Title IS the design element (no decorative lines)
  - Top 10 hard cap
  - Subtle DIVIDER lines between rows, not borders

Dials: VARIANCE 3, MOTION 0, DENSITY 5.
"""
import io
from PIL import Image, ImageDraw

import economy as E
import players as P
from squad_card import F, FD, fetch_face, silhouette, circular

# ── palette (matches standings_card flat mineral) ────────
SURFACE     = (12, 12, 18)
LEADER      = (28, 26, 16)       # #1 warm tint
ZONE_2      = (24, 22, 14)       # #2-3 subtle warm tint
INK         = (244, 248, 252)
INK_BODY    = (190, 192, 204)
INK_MUTED   = (120, 122, 140)
INK_DIM     = (72, 74, 90)
DIVIDER     = (30, 30, 40)
ACCENT      = (255, 180, 60)     # the ONE accent — goals + leader
AMBER_DIM   = (140, 110, 50)
SILHOUETTE_C = (28, 30, 42)

MAX_PLAYERS = 10


def _b(d, text, fnt):
    return d.textbbox((0, 0), text, font=fnt)

def _vc_right(d, x_right, cy, text, fnt, fill):
    bb = _b(d, text, fnt)
    w, h = bb[2] - bb[0], bb[3] - bb[1]
    d.text((x_right - w, cy - h / 2 - bb[1]), text, font=fnt, fill=fill)

def _vc_left(d, x, cy, text, fnt, fill):
    bb = _b(d, text, fnt)
    h = bb[3] - bb[1]
    d.text((x, cy - h / 2 - bb[1]), text, font=fnt, fill=fill)


def _fit_name(d, name, max_w, fnt):
    if _b(d, name, fnt)[2] <= max_w:
        return name
    while len(name) > 2:
        name = name[:-1]
        if _b(d, name + "…", fnt)[2] <= max_w:
            return name + "…"
    return name[:2] + "…"


# ISO country → 3-letter code (PIL can't render flag emoji)
_CC = {
    "Argentina": "ARG", "Brazil": "BRA", "France": "FRA", "Germany": "GER",
    "England": "ENG", "Spain": "ESP", "Italy": "ITA", "Portugal": "POR",
    "Netherlands": "NED", "Belgium": "BEL", "Croatia": "CRO", "Uruguay": "URU",
    "Norway": "NOR", "Egypt": "EGY", "Senegal": "SEN", "Poland": "POL",
    "Serbia": "SRB", "Morocco": "MAR", "Mexico": "MEX", "Japan": "JPN",
    "South Korea": "KOR", "Austria": "AUT", "Switzerland": "SUI",
    "Denmark": "DEN", "Sweden": "SWE", "Colombia": "COL", "Chile": "CHI",
    "Ivory Coast": "CIV", "Nigeria": "NGA", "Ghana": "GHA", "Turkey": "TUR",
    "Ukraine": "UKR", "Russia": "RUS", "Czech Republic": "CZE",
    "Slovakia": "SVK", "Scotland": "SCO", "Wales": "WAL", "Ireland": "IRL",
    "United States": "USA", "Canada": "CAN", "Australia": "AUS",
    "Algeria": "ALG", "Tunisia": "TUN", "Cameroon": "CMR", "Mali": "MLI",
    "Gabon": "GAB", "Finland": "FIN", "Hungary": "HUN", "Greece": "GRE",
    "Romania": "ROU", "Slovenia": "SVN", "Bosnia": "BIH", "Albania": "ALB",
    "Bulgaria": "BUL", "Iceland": "ISL", "Georgia": "GEO", "Armenia": "ARM",
    "Ecuador": "ECU", "Peru": "PER", "Paraguay": "PAR", "Venezuela": "VEN",
    "Costa Rica": "CRC", "Jamaica": "JAM", "Iran": "IRN", "Saudi Arabia": "KSA",
    "Qatar": "QAT", "Iraq": "IRQ", "China": "CHN", "Thailand": "THA",
}

def _cc(country):
    """3-letter country code, or first 3 letters of the country name."""
    if not country:
        return ""
    return _CC.get(country, country[:3].upper())


def _face_for(player_key, r):
    """Circular player face (SoFIFA) or silhouette fallback."""
    face_url = E.get_face_url(player_key)
    raw = fetch_face(face_url) if face_url else None
    if raw:
        return circular(raw, r * 2, ring_w=2, ring_colour=AMBER_DIM)
    return circular(silhouette(r * 2, SILHOUETTE_C), r * 2, ring_w=2,
                    ring_colour=AMBER_DIM)


def render_top_scorers(guild_id, scorers, subtitle=""):
    """
    scorers: list of dicts from E.get_top_scorers() with keys:
             player_key, goals, assists, motm, matches
    Returns a BytesIO PNG buffer, or None if empty.
    Hard cap: MAX_PLAYERS (10).
    """
    if not scorers:
        return None

    scorers = scorers[:MAX_PLAYERS]
    n = len(scorers)

    # ── geometry (matches standings_card width) ─────────────
    W = 1120
    PAD = 48
    ROW_H = 52
    title_h = 96
    header_h = 28
    H = title_h + header_h + n * ROW_H + 24

    canvas = Image.new("RGBA", (W, H), SURFACE + (255,))
    d = ImageDraw.Draw(canvas)

    # ── title ────────────────────────────────────────────────
    _vc_left(d, PAD, 44, "GOLDEN BOOT", FD(48), INK)
    if subtitle:
        _vc_left(d, PAD, 80, subtitle, F(14, bold=True), INK_MUTED)
    _vc_right(d, W - PAD, 48, f"TOP {n}", F(13, bold=True), INK_MUTED)

    # ── column geometry (right-anchored, like standings) ────
    right = W - PAD
    cols = {
        "MOTM":  right - 8,
        "A":     right - 68,
        "G":     right - 128,
        "NAT":   right - 196,
    }
    name_x = PAD + 80           # name starts after rank + face
    name_max = cols["NAT"] - name_x - 28

    # ── header row ──────────────────────────────────────────
    hy = title_h + header_h / 2
    _vc_left(d, PAD, hy, "#", F(12, bold=True), INK_DIM)
    _vc_left(d, name_x, hy, "PLAYER", F(12, bold=True), INK_DIM)
    _vc_right(d, cols["NAT"], hy, "NAT", F(12, bold=True), INK_DIM)
    _vc_right(d, cols["G"], hy, "G", F(12, bold=True), INK_DIM)
    _vc_right(d, cols["A"], hy, "A", F(12, bold=True), INK_DIM)
    _vc_right(d, cols["MOTM"], hy, "MOTM", F(12, bold=True), INK_DIM)
    d.line([PAD, title_h + header_h, W - PAD, title_h + header_h],
           fill=DIVIDER, width=1)

    # ── body ────────────────────────────────────────────────
    for i, s in enumerate(scorers):
        ry = title_h + header_h + i * ROW_H
        row_cy = ry + ROW_H / 2
        rank = i + 1

        # leader / podium tint
        if rank == 1:
            d.rectangle([0, ry, W, ry + ROW_H], fill=LEADER)
        elif rank <= 3:
            d.rectangle([0, ry, W, ry + ROW_H], fill=ZONE_2)

        if i > 0:
            d.line([PAD, ry, W - PAD, ry], fill=DIVIDER, width=1)

        # rank — display font, accent for #1
        pos_col = ACCENT if rank == 1 else INK_BODY
        _vc_left(d, PAD, row_cy, str(rank), FD(24), pos_col)

        # face circle
        p = P.get(s["player_key"])
        if not p:
            _vc_left(d, name_x, row_cy, s["player_key"], F(14), INK_DIM)
            continue

        face_r = 16
        face = _face_for(s["player_key"], face_r)
        canvas.paste(face,
                     (PAD + 40 - face.width // 2,
                      int(row_cy - face.height / 2)),
                     face)

        # name + club badge (name truncated to fit before NAT column)
        name_fnt = F(16, bold=True)
        name = _fit_name(d, p["name"], name_max, name_fnt)
        name_col = INK if rank == 1 else INK_BODY
        _vc_left(d, name_x, row_cy, name, name_fnt, name_col)

        # club badge right after name
        owner = E.get_player_owner(guild_id, s["player_key"])
        team = owner[1] if owner and owner[1] else p.get("club", "")
        if team:
            try:
                import club_logos as CL
                logo = CL.get_club_logo(team, 18)
                name_w = _b(d, name, name_fnt)[2]
                logo_x = int(name_x + name_w + 12)
                # only paste if it won't collide with NAT column
                if logo_x + 18 < cols["NAT"] - 8:
                    canvas.paste(logo, (logo_x, int(row_cy - 9)), logo)
            except Exception:
                pass

        # country code (3 letters, NOT emoji flag)
        cc = _cc(p.get("country", ""))
        _vc_right(d, cols["NAT"], row_cy, cc, F(12, bold=True), INK_MUTED)

        # stats — right-anchored to same positions as header
        _vc_right(d, cols["G"], row_cy, str(s["goals"]),
                  F(19, bold=True), ACCENT)
        _vc_right(d, cols["A"], row_cy, str(s["assists"]),
                  F(15, bold=False), INK_BODY)
        _vc_right(d, cols["MOTM"], row_cy, str(s["motm"]),
                  F(15, bold=False), INK_BODY)

    buf = io.BytesIO()
    canvas.convert("RGB").save(buf, "PNG", optimize=True)
    buf.seek(0)
    return buf
