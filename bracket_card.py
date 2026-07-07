"""
Knockout bracket renderer — converges to a CENTER FINAL.

  R16_L → QF_L → SF_L ┐
                       ├─ FINAL ─┤
                SF_R ← QF_R ← R16_R

Left half flows RIGHTWARD to center, right half flows LEFTWARD to center.
Every parent match is vertically centred between its two children, so the
tree visibly CONVERGES on the middle.

DESIGN NOTES
  • Compact canvas (~2700px) + large fonts → survives Discord's auto-downscale.
  • ONE accent (gold) reserved for the climax: Final label, Final underline,
    the two connectors feeding the Final, and the champion banner. Everything
    else is tinted-neutral (Impeccable: no pure black, no random color swaps).
  • No glow / glassmorphism / gradients / side-stripes (anti-AI-slop).
  • Penalties: a drawn KO match shows  "1 (5)" / "1 (4)"  for both teams.
"""
import io
from PIL import Image, ImageDraw

import league as L
import club_logos as CL
from squad_card import F, FD

# ── palette (tinted neutrals + single gold accent) ────────
BG           = (12, 12, 16)
PANEL        = (24, 24, 31)
PANEL_PLAYED = (35, 35, 44)
PANEL_FINAL  = (40, 31, 18)
LINE         = (60, 60, 74)
DIVIDER      = (46, 46, 58)
INK          = (244, 244, 248)
INK_BODY     = (178, 178, 194)
INK_DIM      = (118, 118, 136)   # round-label text (a touch brighter for legibility)
RULE_DIM     = (96, 96, 116)     # structural underline under round labels
WIN          = (255, 186, 70)
LOSS         = (96, 96, 110)
GOLD         = (255, 206, 96)     # the ONE accent — reserved for the climax
SPINE        = (70, 70, 86)

# ── geometry (compact canvas → less Discord downscaling) ──
MW    = 332          # match box width
MH    = 104          # match box height  (52 per team row)
CG    = 56           # horizontal gap between columns (room for connectors)
VG    = 140          # vertical gap between matches (taller image = more screen)
LS    = 40           # club-logo size
PAD   = 40           # outer padding
TH    = 138          # title strip height
FH    = 104          # champion footer height


def _b(d, t, f):
    return d.textbbox((0, 0), t, font=f)

def _vl(d, x, cy, t, f, c):
    bb = _b(d, t, f); h = bb[3] - bb[1]
    d.text((x, cy - h / 2 - bb[1]), t, font=f, fill=c)

def _vr(d, x, cy, t, f, c):
    bb = _b(d, t, f); w, h = bb[2] - bb[0], bb[3] - bb[1]
    d.text((x - w, cy - h / 2 - bb[1]), t, font=f, fill=c)

def _vc(d, cx, cy, t, f, c):
    bb = _b(d, t, f); w, h = bb[2] - bb[0], bb[3] - bb[1]
    d.text((cx - w / 2 - bb[0], cy - h / 2 - bb[1]), t, font=f, fill=c)


def _round_label(d, text, anchor_x, top_y, align, is_final):
    """Round section header: big label + short editorial underline beneath.

    Gold treatment is reserved for the Final (the single accent / focal point);
    every other round uses a tinted-neutral rule so the eye still lands on center.
    """
    sz = 42 if is_final else 36
    col = GOLD if is_final else INK_DIM
    rule = GOLD if is_final else RULE_DIM
    rw = 4 if is_final else 3          # slightly heavier rule on the climax
    f = FD(sz)
    bb = _b(d, text, f); w, h = bb[2] - bb[0], bb[3] - bb[1]
    cy = top_y - 18
    base_y = cy + h / 2 + 6            # underline baseline (below the glyphs)

    if align == "left":
        d.text((anchor_x, cy - h / 2 - bb[1]), text, font=f, fill=col)
        d.line([anchor_x, base_y, anchor_x + w, base_y], fill=rule, width=rw)
    elif align == "right":
        d.text((anchor_x - w, cy - h / 2 - bb[1]), text, font=f, fill=col)
        d.line([anchor_x - w, base_y, anchor_x, base_y], fill=rule, width=rw)
    else:  # center
        d.text((anchor_x - w / 2 - bb[0], cy - h / 2 - bb[1]), text, font=f, fill=col)
        d.line([anchor_x - w / 2, base_y, anchor_x + w / 2, base_y],
               fill=rule, width=rw)


def _y(i, m, top_y, content_h):
    """Match Y-centre for match index i in a column of m matches.

    slot = content_h / m with each match at (i+0.5)*slot.  Because this is
    linear in (i+0.5), a parent at index j//2 in the next round sits EXACTLY
    centred between children 2j and 2j+1 → clean convergence to centre.
    """
    slot = content_h / m
    return top_y + (i + 0.5) * slot


def _connect(d, x1, y1, x2, y2, color=SPINE):
    """Elbow connector: out → across → up/down → into target."""
    mid = (x1 + x2) // 2
    d.line([x1, y1, mid, y1], fill=color, width=2)
    d.line([mid, y1, mid, y2], fill=color, width=2)
    d.line([mid, y2, x2, y2], fill=color, width=2)


def render_bracket(guild_id, season_id):
    rounds = L.bracket(season_id)
    if not rounds:
        return None

    # ── identify the FINAL (the single-match round) ──────────
    final_fx = None
    pre = rounds
    if len(rounds[-1]) == 1:
        final_fx = rounds[-1][0]
        pre = rounds[:-1]

    # split each pre-final round into LEFT / RIGHT halves (outer→inner)
    left_rounds, right_rounds = [], []
    for rnd in pre:
        half = len(rnd) // 2
        left_rounds.append(list(rnd[:half]))
        right_rounds.append(list(rnd[half:]))

    nL = len(left_rounds)            # # of left columns (== # of right columns)
    max_half = max((len(c) for c in (left_rounds + right_rounds)), default=1)

    content_h = max(max_half * (MH + VG), 520)
    has_final = final_fx is not None

    # total columns: nL (left) + [final] + nL (right)
    n_cols = nL + nL + (1 if has_final else 0)
    W = PAD * 2 + n_cols * MW + (n_cols - 1) * CG
    H = TH + content_h + FH + 24

    canvas = Image.new("RGBA", (W, H), BG + (255,))
    d = ImageDraw.Draw(canvas)

    # ── title strip ──────────────────────────────────────────
    _vl(d, PAD, 50, "KNOCKOUT STAGE", FD(54), INK)
    sn = L.get_season(season_id)
    slabel = f"Season {sn['number']}" if sn else f"Season {season_id}"
    _vr(d, W - PAD, 60, slabel, F(22, bold=True), INK_DIM)
    d.line([PAD, TH - 60, W - PAD, TH - 60], fill=LINE, width=1)

    top_y = TH

    # ── store positions:  key -> (left_x, right_x, cy) ───────
    pos = {}

    # ── LEFT columns (outermost far-left → innermost near centre) ──
    lx = PAD
    for ci, col in enumerate(left_rounds):
        m = len(col)
        for mi, fx in enumerate(col):
            cy = _y(mi, m, top_y, content_h)
            _draw_match(d, canvas, lx, cy, fx, guild_id, season_id, "left")
            pos[("L", ci, mi)] = (lx, lx + MW, cy)
        _round_label(d, col[0].get("stage", "").upper(), lx, top_y, "left", False)
        lx += MW + CG

    # ── FINAL (centre) ───────────────────────────────────────
    final_cy = top_y + content_h / 2
    final_left = final_right = None
    if has_final:
        _draw_match(d, canvas, lx, final_cy, final_fx, guild_id, season_id, "center")
        final_left, final_right = lx, lx + MW
        _round_label(d, "FINAL", lx + MW / 2, top_y, "center", True)
        lx += MW + CG

    # ── RIGHT columns (innermost SF near centre → outermost R16 far-right) ──
    #    iterate right_rounds REVERSED so SF (last) is drawn beside the Final,
    #    R16 (first) lands at the far-right edge → right half CONVERGES inward.
    rx = lx
    for ri, col in enumerate(reversed(right_rounds)):
        ci = nL - 1 - ri      # original column index for connector mapping
        m = len(col)
        for mi, fx in enumerate(col):
            cy = _y(mi, m, top_y, content_h)
            _draw_match(d, canvas, rx, cy, fx, guild_id, season_id, "right")
            pos[("R", ci, mi)] = (rx, rx + MW, cy)
        _round_label(d, col[0].get("stage", "").upper(), rx + MW, top_y, "right", False)
        rx += MW + CG

    # ── CONNECTORS ───────────────────────────────────────────
    # LEFT:  L[ci][mi] → L[ci+1][mi//2]   (right edge → left edge, toward centre)
    for ci in range(nL - 1):
        for mi in range(len(left_rounds[ci])):
            p1 = pos.get(("L", ci, mi))
            p2 = pos.get(("L", ci + 1, mi // 2))
            if p1 and p2:
                _connect(d, p1[1], p1[2], p2[0], p2[2])
    # LEFT innermost → Final  (gold: path to glory)
    if has_final and nL:
        p1 = pos.get(("L", nL - 1, 0))
        if p1 and final_left is not None:
            _connect(d, p1[1], p1[2], final_left, final_cy, color=GOLD)

    # RIGHT: R[ci][mi] → R[ci+1][mi//2]   (left edge → right edge, toward centre)
    for ci in range(nL - 1):
        for mi in range(len(right_rounds[ci])):
            p1 = pos.get(("R", ci, mi))
            p2 = pos.get(("R", ci + 1, mi // 2))
            if p1 and p2:
                _connect(d, p1[0], p1[2], p2[1], p2[2])
    # RIGHT innermost → Final  (gold: path to glory)
    if has_final and nL:
        p1 = pos.get(("R", nL - 1, 0))
        if p1 and final_right is not None:
            _connect(d, p1[0], p1[2], final_right, final_cy, color=GOLD)

    # ── CHAMPION banner ──────────────────────────────────────
    champ = L.champion(season_id)
    if champ:
        from economy import get_team_name
        cn = (get_team_name(guild_id, champ) or L.team_name_of(season_id, champ)
              or "Champion")
        d.rounded_rectangle([PAD, H - FH, W - PAD, H - 16], radius=12,
                            fill=(32, 26, 16), outline=GOLD, width=3)
        _vl(d, PAD + 32, H - FH // 2 - 8, f"CHAMPION  {cn}", FD(40), GOLD)

    buf = io.BytesIO()
    canvas.convert("RGB").save(buf, "PNG", optimize=True)
    buf.seek(0)
    return buf


# ── match + team drawing ───────────────────────────────────
def _team_name(gid, sid, user):
    if not user:
        return "TBD"
    try:
        from economy import get_team_name
        n = get_team_name(gid, user)
        if n:
            return n
    except Exception:
        pass
    return L.team_name_of(sid, user) or "TBD"


def _draw_match(d, canvas, x, cy, fx, gid, sid, align):
    w, h = MW, MH
    y = int(cy - h / 2)
    played = fx.get("status") == "played"
    is_final = fx.get("stage", "").lower() in ("final", "grand final")

    if is_final:
        fill = PANEL_FINAL
    elif played:
        fill = PANEL_PLAYED
    else:
        fill = PANEL
    d.rounded_rectangle([x, y, x + w, y + h], radius=9, fill=fill)
    if is_final:
        d.rounded_rectangle([x, y, x + w, y + h], radius=9, outline=GOLD, width=3)

    home = fx.get("home_user")
    away = fx.get("away_user")
    hs = fx.get("home_score")
    as_ = fx.get("away_score")
    hn = _team_name(gid, sid, home)
    an = _team_name(gid, sid, away)

    hw = played and hs is not None and as_ is not None and hs > as_
    aw = played and hs is not None and as_ is not None and as_ > hs
    hp = fx.get("home_pens")
    ap = fx.get("away_pens")
    if played and hs == as_ and hp is not None and ap is not None:
        hw, aw = hp > ap, ap > hp

    # shootout? show FT + pens for BOTH teams, e.g.  1 (5) / 1 (4)
    shootout = (played and hs is not None and as_ is not None
                and hs == as_ and hp is not None and ap is not None)
    rh = h / 2
    _draw_team(d, canvas, x, cy - rh / 2, w, hn, hs, hw, played, align,
               is_final, hp if shootout else None)
    d.line([x + 10, y + rh, x + w - 10, y + rh], fill=DIVIDER, width=1)
    _draw_team(d, canvas, x, cy + rh / 2, w, an, as_, aw, played, align,
               is_final, ap if shootout else None)


def _short(name):
    return name if len(name) <= 12 else name[:11] + "…"


def _draw_team(d, canvas, x, cy, w, name, score, won, played, align,
               is_final, pens):
    nc = INK if won else (INK_BODY if played else INK_DIM)
    sc = WIN if won else LOSS
    nm_f = F(22 if is_final else 20, bold=True)
    sc_f = FD(38 if is_final else 34)
    short = _short(name)

    # score text — append pens in parens for shootouts:  "1 (5)"
    if score is not None and played:
        stext = f"{score} ({pens})" if pens is not None else str(score)
    else:
        stext = None

    if align == "right":
        # score faces centre (left), name+logo to the right
        if stext is not None:
            _vl(d, x + 16, cy, stext, sc_f, sc)
        elif name != "TBD":
            _vl(d, x + 16, cy, "—", F(21), INK_DIM)
        _vr(d, x + w - LS - 18, cy, short, nm_f, nc)
        if name != "TBD":
            try:
                logo = CL.get_club_logo(name, LS)
                canvas.paste(logo, (x + w - LS - 6, int(cy - LS / 2)), logo)
            except Exception:
                pass
    else:
        # left & centre: logo+name left, score right (faces centre)
        if name != "TBD":
            try:
                logo = CL.get_club_logo(name, LS)
                canvas.paste(logo, (x + 6, int(cy - LS / 2)), logo)
            except Exception:
                pass
        _vl(d, x + LS + 18, cy, short, nm_f, nc)
        if stext is not None:
            _vr(d, x + w - 16, cy, stext, sc_f, sc)
        elif name != "TBD":
            _vr(d, x + w - 16, cy, "—", F(21), INK_DIM)
