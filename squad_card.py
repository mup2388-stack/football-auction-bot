"""
Squad Card Renderer v12 — Deep Ocean-Coral, anti-slop, premium.

Skills applied:
  - Impeccable: NO side-stripe borders (banned). Background tints.
    Color strategy: "Committed" — ocean blue is the identity.
    Tinted neutrals toward blue hue.
    Shape consistency: radius=12 everywhere.
  - Taste Skill: DENSITY=4 (airy formation), VARIANCE=7
  - Emil Kowalski: subtle depth, unseen details compound
  - Anthropic: typography carries personality, structure is information
  - UI/UX Pro Max: premium dark theme

Key changes:
  - Deep ocean gradient background (NOT black behind pitch)
  - Player cards use background tints, no stripe borders
  - Card faces use soft ocean-tinted silhouettes
  - Header/footer use proper depth layering
  - Rating badge has proper glow
"""
import io
import os
import hashlib
import urllib.request

from PIL import Image, ImageDraw, ImageFont, ImageFilter

import economy as E

FACE_CACHE_DIR = os.getenv("FACE_CACHE_DIR", os.path.join("data", "faces"))
PITCH_BG = os.path.join("assets", "pitch_bg.png")
os.makedirs(FACE_CACHE_DIR, exist_ok=True)

# ── Deep Ocean-Coral palette (matches player_card.py) ───────────────────
BG_TOP = (8, 18, 32)
BG_BOTTOM = (3, 8, 16)
PITCH_FILL = (8, 18, 32)       # fill behind pitch image if it has transparency
CARD_BG = (14, 28, 44)         # ocean card background tint
CARD_BG2 = (20, 38, 58)        # highlighted card
BORDER = (30, 50, 75)          # subtle border
SILHOUETTE = (20, 35, 52)      # ocean-tinted silhouette
GLOW_BLUE = (100, 180, 255)
GLOW_CORAL = (255, 130, 100)

# Font colors
WHITE = (250, 248, 240)        # pearl white
T2 = (160, 180, 200)           # light steel
T3 = (130, 150, 175)           # steel blue-grey

TIER_COLORS = {
    "GoldRare": {"light": (255, 210, 60),  "dark": (165, 115, 15),  "text": (30, 22, 5)},
    "Gold":     {"light": (210, 155, 30),  "dark": (130, 85, 10),   "text": (30, 22, 5)},
    "Silver":   {"light": (185, 195, 210), "dark": (100, 115, 140),  "text": (25, 30, 45)},
    "Bronze":   {"light": (200, 130, 60),  "dark": (110, 60, 20),   "text": (35, 20, 5)},
}
FONT_DIR = os.path.join("assets", "fonts")

_FONT_CACHE = {}
_CUSTOM_FONTS = {}


def _load_custom_fonts():
    if not os.path.exists(FONT_DIR):
        return
    for f in os.listdir(FONT_DIR):
        fl = f.lower()
        path = os.path.join(FONT_DIR, f)
        if not fl.endswith((".ttf", ".otf")):
            continue
        if "bebas" in fl:
            _CUSTOM_FONTS["display"] = path
        elif "anton" in fl:
            _CUSTOM_FONTS["heavy"] = path
        elif "oswald" in fl and "bold" in fl:
            _CUSTOM_FONTS["bold"] = path
        elif "oswald" in fl:
            _CUSTOM_FONTS["regular"] = path

_load_custom_fonts()


def _font_path(bold=False):
    if bold:
        for key in ("bold", "heavy", "display"):
            if key in _CUSTOM_FONTS:
                return _CUSTOM_FONTS[key]
    else:
        for key in ("regular",):
            if key in _CUSTOM_FONTS:
                return _CUSTOM_FONTS[key]
    paths = [
        (r"C:\Windows\Fonts\arialbd.ttf", r"C:\Windows\Fonts\arial.ttf"),
        (r"C:\Windows\Fonts\segoeuib.ttf", r"C:\Windows\Fonts\segoeui.ttf"),
        ("/usr/local/lib/python3.13/site-packages/cv2/qt/fonts/DejaVuSansCondensed-Bold.ttf",
         "/usr/local/lib/python3.13/site-packages/cv2/qt/fonts/DejaVuSansCondensed.ttf"),
        ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
         "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    ]
    for bold_p, reg_p in paths:
        target = bold_p if bold else reg_p
        if os.path.exists(target):
            return target
    for p in ["/usr/local/lib/python3.13/site-packages/matplotlib/mpl-data/fonts/ttf/DejaVuSans-Bold.ttf",
              "/usr/local/lib/python3.13/site-packages/matplotlib/mpl-data/fonts/ttf/DejaVuSans.ttf"]:
        if os.path.exists(p):
            return p
    return None


def _display_font_path():
    for key in ("display", "heavy", "bold"):
        if key in _CUSTOM_FONTS:
            return _CUSTOM_FONTS[key]
    return _font_path(bold=True)


def F(size, bold=False):
    key = (size, bold)
    if key not in _FONT_CACHE:
        p = _font_path(bold)
        try:
            _FONT_CACHE[key] = ImageFont.truetype(p, size) if p else ImageFont.load_default()
        except Exception:
            for k in list(_CUSTOM_FONTS.keys()):
                if _CUSTOM_FONTS[k] == p:
                    del _CUSTOM_FONTS[k]
            p = _font_path(bold)
            try:
                _FONT_CACHE[key] = ImageFont.truetype(p, size) if p else ImageFont.load_default()
            except Exception:
                _FONT_CACHE[key] = ImageFont.load_default()
    return _FONT_CACHE[key]


def FD(size):
    key = ("display", size)
    if key not in _FONT_CACHE:
        p = _display_font_path()
        try:
            _FONT_CACHE[key] = ImageFont.truetype(p, size) if p else ImageFont.load_default()
        except Exception:
            for k in ("display", "heavy", "bold"):
                _CUSTOM_FONTS.pop(k, None)
            p = _display_font_path()
            try:
                _FONT_CACHE[key] = ImageFont.truetype(p, size) if p else ImageFont.load_default()
            except Exception:
                _FONT_CACHE[key] = ImageFont.load_default()
    return _FONT_CACHE[key]


def text_centered(draw, center, text, fnt, fill):
    bbox = draw.textbbox((0, 0), text, font=fnt)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text((center[0] - w / 2 - bbox[0], center[1] - h / 2 - bbox[1]),
              text, font=fnt, fill=fill)


def fit_font(draw, text, max_w, sizes, bold=False):
    for s in sizes:
        f = F(s, bold=bold)
        if draw.textbbox((0, 0), text, font=f)[2] <= max_w:
            return text, f
    s = sizes[-1]
    f = F(s, bold=bold)
    while len(text) > 2:
        text = text[:-1]
        if draw.textbbox((0, 0), text + "…", font=f)[2] <= max_w:
            return text + "…", f
    return text, f


def fetch_face(url):
    h = hashlib.md5(url.encode()).hexdigest()[:16]
    path = os.path.join(FACE_CACHE_DIR, f"{h}.png")
    if os.path.exists(path) and os.path.getsize(path) > 1000:
        try:
            return Image.open(path).convert("RGBA")
        except Exception:
            pass
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        data = urllib.request.urlopen(req, timeout=15).read()
        if len(data) < 1000:
            return None
        im = Image.open(io.BytesIO(data)).convert("RGBA")
        im.save(path)
        return im
    except Exception:
        return None


def fetch_avatar_sync(url):
    if not url:
        return None
    img = fetch_face(url)
    if img:
        return img
    clean = url.split("?")[0]
    clean = clean.rsplit(".", 1)[0] + ".png?size=128"
    return fetch_face(clean)


def silhouette(size, colour):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cx = size / 2
    hr = size * 0.20
    d.ellipse([cx - hr, size * 0.14, cx + hr, size * 0.14 + 2 * hr], fill=colour)
    d.ellipse([cx - size * 0.34, size * 0.45, cx + size * 0.34, size * 1.02], fill=colour)
    return img


def circular(im, size, ring_w=3, ring_colour=None):
    total = size + ring_w * 2
    canvas = Image.new("RGBA", (total, total), (0, 0, 0, 0))
    if ring_colour:
        ImageDraw.Draw(canvas).ellipse([0, 0, total - 1, total - 1], fill=ring_colour)
    im_s = im.resize((size, size), Image.LANCZOS)
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, size - 1, size - 1], fill=255)
    canvas.paste(im_s, (ring_w, ring_w), mask)
    return canvas


def paste_shadow(base, img, pos, blur=14, opacity=120, offset=(3, 8)):
    """Premium double drop shadow for depth."""
    x, y = pos
    w, h = img.size
    pad = blur * 2
    # Outer soft shadow
    shadow = Image.new("RGBA", (w + pad * 2, h + pad * 2), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle(
        [pad, pad, pad + w, pad + h], radius=14, fill=(0, 0, 0, opacity))
    shadow = shadow.filter(ImageFilter.GaussianBlur(blur))
    # Inner sharp shadow
    shadow2 = Image.new("RGBA", (w + pad * 2, h + pad * 2), (0, 0, 0, 0))
    ImageDraw.Draw(shadow2).rounded_rectangle(
        [pad, pad, pad + w, pad + h], radius=14, fill=(0, 0, 0, 60))
    shadow2 = shadow2.filter(ImageFilter.GaussianBlur(6))
    base.alpha_composite(shadow2, (int(x - pad + offset[0] + 2), int(y - pad + offset[1] + 2)))
    base.alpha_composite(shadow, (int(x - pad + offset[0]), int(y - pad + offset[1])))
    base.alpha_composite(img, (int(x), int(y)))


def _cover_fit(im, tw, th):
    w, h = im.size
    s = max(tw/w, th/h)
    nw, nh = int(w*s), int(h*s)
    im = im.resize((nw, nh), Image.LANCZOS)
    return im.crop(((nw-tw)//2, (nh-th)//2, (nw+tw)//2, (nh+th)//2))


def _v_gradient(w, h, top, bottom):
    """Fast numpy gradient."""
    import numpy as np
    top_arr = np.array(top, dtype=np.float32)
    bot_arr = np.array(bottom, dtype=np.float32)
    ratios = np.linspace(0, 1, h, dtype=np.float32).reshape(-1, 1, 1)
    gradient = (top_arr * (1 - ratios) + bot_arr * ratios).astype(np.uint8)
    gradient = np.broadcast_to(gradient, (h, w, 3)).copy()
    return Image.fromarray(gradient, "RGB").convert("RGBA")


def _card_gradient(w, h, tier):
    """Metallic FUT-style gradient body — gold/silver/bronze."""
    cols = TIER_COLORS.get(tier, TIER_COLORS["Gold"])
    light, dark = cols["light"], cols["dark"]
    grad = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    px = grad.load()
    for y in range(h):
        for x in range(w):
            rv = y / h
            rh = abs(x - w/2) / (w/2)
            blend = rv * 0.65 + rh * 0.35
            r = int(light[0] * (1-blend) + dark[0] * blend)
            g = int(light[1] * (1-blend) + dark[1] * blend)
            b = int(light[2] * (1-blend) + dark[2] * blend)
            px[x, y] = (r, g, b, 255)
    sheen = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    sd = ImageDraw.Draw(sheen)
    for i in range(w + h):
        alpha = max(0, 40 - abs(i - w * 0.55) * 0.35)
        if alpha > 0:
            sd.line([(i, 0), (i - h, h)], fill=(255, 255, 255, int(alpha)))
    return Image.alpha_composite(grad, sheen)


def build_card(player, cw=200, ch=250, display_pos=None):
    """FUT-style metallic card — gold/silver/bronze gradient body."""
    is_empty = player is None
    tier = player.get("tier", "Gold") if player else "Silver"
    cols = TIER_COLORS.get(tier, TIER_COLORS["Gold"])
    light, dark = cols["light"], cols["dark"]
    shown_pos = display_pos or (player["position"] if player else "")

    if is_empty:
        # Empty card — same shape as player cards but dark/muted
        card = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
        dl = (30, 35, 48)
        dd = (12, 14, 22)
        grad = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
        px = grad.load()
        for yy in range(ch):
            for xx in range(cw):
                rv = yy / ch
                rh = abs(xx - cw/2) / (cw/2)
                b = rv * 0.65 + rh * 0.35
                px[xx, yy] = (int(dl[0]*(1-b)+dd[0]*b), int(dl[1]*(1-b)+dd[1]*b),
                              int(dl[2]*(1-b)+dd[2]*b), 255)
        mask = Image.new("L", (cw, ch), 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, cw-1, ch-1], radius=12, fill=255)
        card.paste(grad, (0, 0), mask)
        d = ImageDraw.Draw(card)
        d.rounded_rectangle([0, 0, cw-1, ch-1], radius=12, outline=(60, 65, 80), width=2)
        d.rounded_rectangle([3, 3, cw-4, ch-4], radius=9, outline=(40, 45, 58), width=1)
        text_centered(d, (cw/2, ch*0.42), "—", F(int(cw*0.20)), (75, 80, 95))
        text_centered(d, (cw/2, ch*0.60), "EMPTY", F(int(cw*0.09), bold=True), (65, 70, 85))
        return card

    # Metallic gradient body
    body = _card_gradient(cw, ch, tier)
    card = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    mask = Image.new("L", (cw, ch), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, cw-1, ch-1], radius=12, fill=255)
    card.paste(body, (0, 0), mask)

    d = ImageDraw.Draw(card)
    # Borders (double — outer bright, inner dark)
    d.rounded_rectangle([0, 0, cw-1, ch-1], radius=12, outline=light, width=2)
    d.rounded_rectangle([3, 3, cw-4, ch-4], radius=9, outline=dark, width=1)

    # OVR + position
    ovr_sz = int(cw * 0.22)
    d.text([cw*0.06, ch*0.05], str(player["ovr"]), font=FD(ovr_sz), fill=cols["text"])
    d.text([cw*0.06, ch*0.05 + ovr_sz + 6], shown_pos,
           font=FD(int(cw*0.11)), fill=cols["text"])

    # Foot indicator
    foot = player.get("foot", "Right")
    foot_letter = foot[0] if foot else "R"
    foot_y = ch * 0.05 + ovr_sz + 6 + int(cw * 0.11) + 10
    foot_r = int(cw * 0.05)
    foot_x = cw * 0.07
    d.ellipse([foot_x, foot_y, foot_x + foot_r*2, foot_y + foot_r*2],
              outline=cols["text"], width=2)
    text_centered(d, (foot_x + foot_r, foot_y + foot_r), foot_letter,
                  F(int(cw*0.065), bold=True), cols["text"])

    # Face (CENTER, HUGE)
    face_cx = cw * 0.55
    face_cy = ch * 0.35
    face_r = int(cw * 0.35)
    face_url = E.get_face_url(player["key"])
    face_im = None
    if face_url:
        raw = fetch_face(face_url)
        if raw:
            face_im = circular(raw, face_r*2, ring_w=3, ring_colour=light)
    if face_im is None:
        face_im = circular(silhouette(face_r*2, SILHOUETTE), face_r*2, ring_w=3, ring_colour=light)
    card.paste(face_im, (int(face_cx - face_im.width/2), int(face_cy - face_im.height/2)), face_im)

    d = ImageDraw.Draw(card)

    # Name bar — dark strip on the metallic body
    name_y = ch * 0.72
    bar_h = int(ch * 0.12)
    d.rounded_rectangle([4, int(name_y - bar_h/2), cw-5, int(name_y + bar_h/2)],
                       radius=6, fill=(0, 0, 0, 120))
    nm, nf = fit_font(d, player["name"], cw - 16,
                      [int(cw*0.12), int(cw*0.11), int(cw*0.10), int(cw*0.09)], bold=True)
    text_centered(d, (cw/2, name_y), nm, nf, WHITE)

    # Playing style
    style = player.get("playing_style", "")
    if style:
        renames = {"Extra Frontman": "Attacking Defender", "Offensive Goalkeeper": "Sweeper Keeper"}
        style = renames.get(style, style)
        text_centered(d, (cw/2, ch*0.88), style.upper(),
                      FD(int(cw*0.065)), cols["text"])

    return card


def render_squad_card(guild_id, member_name, user_id, squad, avatar_url=None):
    W, H = 1696, 1360

    # Get team name + logo
    team_name = E.get_team_name(guild_id, user_id) or member_name
    team_logo_url = E.get_team_logo(guild_id, user_id) or avatar_url

    STADIUM_BG = os.path.join("assets", "stadium_bg.png")

    # ── Background: stadium image, then pitch on top ────────────────
    if os.path.exists(STADIUM_BG):
        try:
            stadium = Image.open(STADIUM_BG).convert("RGBA")
            canvas = _cover_fit(stadium, W, H)
            dark = Image.new("RGBA", (W, H), (0, 0, 0, 60))
            canvas.alpha_composite(dark)
        except Exception:
            canvas = _v_gradient(W, H, BG_TOP, BG_BOTTOM)
    else:
        canvas = _v_gradient(W, H, BG_TOP, BG_BOTTOM)
        for bx, by, br, bc in [
            (300, 200, 200, (100, 180, 255, 10)),
            (1200, 1000, 250, (255, 130, 100, 6)),
        ]:
            blob = Image.new("RGBA", (br*2, br*2), (0, 0, 0, 0))
            ImageDraw.Draw(blob).ellipse([0, 0, br*2-1, br*2-1], fill=bc)
            blob = blob.filter(ImageFilter.GaussianBlur(60))
            canvas.alpha_composite(blob, (bx - br, by - br))

    # Pitch image on top (centered)
    if os.path.exists(PITCH_BG):
        try:
            pitch = Image.open(PITCH_BG).convert("RGBA")
            pw, ph = pitch.size
            scale = min(W / pw, H / ph)
            nw, nh = int(pw * scale), int(ph * scale)
            pitch = pitch.resize((nw, nh), Image.LANCZOS)
            px_pos = (W - nw) // 2
            py_pos = (H - nh) // 2
            canvas.alpha_composite(pitch, (px_pos, py_pos))
        except Exception:
            pass

    d = ImageDraw.Draw(canvas)

    PITCH_TOP    = 270
    PITCH_BOTTOM = 1270
    PITCH_LEFT   = 110
    PITCH_RIGHT  = 1586
    pitch_w = PITCH_RIGHT - PITCH_LEFT
    pitch_h = PITCH_BOTTOM - PITCH_TOP

    # ── Header — premium layered design ─────────────────────────────
    bar_h = 100
    header_grad = _v_gradient(W, bar_h, (10, 22, 38), (4, 10, 18))
    canvas.alpha_composite(header_grad, (0, 0))
    d = ImageDraw.Draw(canvas)
    d.rectangle([0, bar_h - 3, W, bar_h], fill=(40, 70, 110))

    # Team logo with glow
    pfp_r = 38
    pfp_cx, pfp_cy = 60, bar_h // 2
    logo_glow = Image.new("RGBA", (pfp_r*2+30, pfp_r*2+30), (0,0,0,0))
    ImageDraw.Draw(logo_glow).ellipse([0, 0, pfp_r*2+29, pfp_r*2+29], fill=(100, 180, 255, 25))
    logo_glow = logo_glow.filter(ImageFilter.GaussianBlur(10))
    canvas.alpha_composite(logo_glow, (pfp_cx-pfp_r-15, pfp_cy-pfp_r-15))

    pfp_im = None
    if team_logo_url:
        raw = fetch_avatar_sync(team_logo_url)
        if raw:
            pfp_im = circular(raw, pfp_r*2, ring_w=3, ring_colour=GLOW_BLUE)
    if pfp_im is None:
        pfp_im = circular(silhouette(pfp_r*2, SILHOUETTE), pfp_r*2, ring_w=3, ring_colour=GLOW_BLUE)
    canvas.alpha_composite(pfp_im, (pfp_cx - pfp_im.width//2, pfp_cy - pfp_im.height//2))

    d = ImageDraw.Draw(canvas)
    team_display = team_name.upper()
    d.text([107, bar_h // 2 - 26], team_display, font=FD(42), fill=(0, 0, 0, 100))
    d.text([105, bar_h // 2 - 28], team_display, font=FD(42), fill=WHITE)
    d.text([106, bar_h // 2 + 16], "S T A R T I N G   X I", font=F(16, bold=True), fill=GLOW_BLUE)

    # ── Formation + lineup ──────────────────────────────────────────
    import formations as FM
    lineup, formation_name = E.get_lineup(guild_id, user_id)

    xi_ovrs = [p["ovr"] for _, p in lineup if p]
    rating = round(sum(xi_ovrs)/len(xi_ovrs)) if xi_ovrs else 0

    # ── Rating badge — with proper glow (Emil Kowalski: depth) ──────
    badge_r = 58
    bx, by = W - 165, 100
    # Glow layer
    glow = Image.new("RGBA", (badge_r*2+20, badge_r*2+20), (0,0,0,0))
    ImageDraw.Draw(glow).ellipse([0, 0, badge_r*2+19, badge_r*2+19],
                                fill=(100, 180, 255, 30))
    glow = glow.filter(ImageFilter.GaussianBlur(12))
    canvas.alpha_composite(glow, (bx-badge_r-10, by-badge_r-10))
    d = ImageDraw.Draw(canvas)
    # Badge
    d.ellipse([bx-badge_r, by-badge_r, bx+badge_r, by+badge_r],
              fill=TIER_COLORS["GoldRare"]["light"],
              outline=TIER_COLORS["GoldRare"]["dark"], width=3)
    text_centered(d, (bx, by+2), str(rating), FD(52),
                  TIER_COLORS["GoldRare"]["text"])

    CW_BASE, CH_BASE = 200, 250
    CARD_ASPECT = CW_BASE / CH_BASE  # 0.8 — keep the FUT card shape when scaling

    # ── ROW SPACING — fit ALL rows, no overflow, no overlap ─────────
    unique_ys = sorted(set(s["y"] for s in FM.all_slots(FM.get_formation(formation_name))))
    n_rows = len(unique_ys)
    # Usable area: just below the header (bar_h) to just above the footer.
    # Starting higher (was PITCH_TOP=270) moves the formation UP and frees
    # ~100px of vertical room that was previously wasted.
    usable_top = bar_h + 70
    usable_bottom = (H - 64) - 14   # 64px footer + 14px breathing room
    usable_h = usable_bottom - usable_top
    min_gap = 22
    # Scale card height so every row fits with min_gap. 4-row formations keep
    # the full 250px; 5-6 row formations compress (previously they overflowed
    # and the GK was clipped off the bottom of the canvas).
    fit_ch = (usable_h - (n_rows - 1) * min_gap) / n_rows
    CH = min(CH_BASE, int(fit_ch))
    CW = int(CH * CARD_ASPECT)
    # Even vertical distribution across the usable area (guarantees no overlap)
    actual_gap = (usable_h - n_rows * CH) / max(1, n_rows - 1)

    # Map each formation Y fraction to its row's top-left pixel Y
    y_map = {}
    for i, orig_y in enumerate(unique_ys):
        y_map[orig_y] = usable_top + i * (CH + actual_gap)

    d = ImageDraw.Draw(canvas)

    # ── CARDS ───────────────────────────────────────────────────────
    CH_CARD = CH

    for slot, player in lineup:
        cx = PITCH_LEFT + pitch_w * slot["x"]
        card_x = cx - CW / 2
        # Y from the fitted row map (fallback should never trigger)
        card_y = y_map.get(slot["y"], usable_top + (pitch_h * slot["y"]) - CH_CARD / 2)
        if player:
            card = build_card(player, CW, CH_CARD, display_pos=slot["pos"])
        else:
            card = build_card(None, CW, CH_CARD, display_pos=slot["pos"])
        paste_shadow(canvas, card, (card_x, card_y))

    # ── Footer — premium with accent line and label/value pairs ─────
    sv = E.squad_value(squad)
    bal = E.get_balance(guild_id, user_id)
    foot_h = 64
    foot_grad = _v_gradient(W, foot_h, (4, 10, 18), (8, 20, 36))
    canvas.alpha_composite(foot_grad, (0, H - foot_h))
    d = ImageDraw.Draw(canvas)
    d.rectangle([0, H - foot_h, W, H - foot_h + 3], fill=(40, 70, 110))
    fy = H - foot_h // 2

    f_label_y = fy - 14
    f_value_y = fy + 6
    text_centered(d, (W*0.18, f_label_y), "FORMATION", F(12, bold=True), T3)
    text_centered(d, (W*0.18, f_value_y), formation_name, FD(26), WHITE)

    text_centered(d, (W*0.42, f_label_y), "SQUAD VALUE", F(12, bold=True), T3)
    text_centered(d, (W*0.42, f_value_y), E.money(sv), FD(26), GLOW_BLUE)

    text_centered(d, (W*0.65, f_label_y), "BUDGET", F(12, bold=True), T3)
    text_centered(d, (W*0.65, f_value_y), E.money(bal), FD(26), GLOW_CORAL)

    squad_size = len(squad)
    text_centered(d, (W*0.85, f_label_y), "PLAYERS", F(12, bold=True), T3)
    text_centered(d, (W*0.85, f_value_y), str(squad_size), FD(26), WHITE)

    buf = io.BytesIO()
    canvas.convert("RGB").save(buf, "PNG", optimize=True)
    buf.seek(0)
    return buf
