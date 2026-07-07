"""
Club logo system — generates clean circular badges with club initials.

Each badge is a 120x120 PNG with:
- Circular shape
- Club-specific gradient color
- 3-letter abbreviation in display font
- Consistent style (no AI slop)

Files are cached in assets/logos/. If a real PNG logo exists for a club
(named {slug}.png), it's used instead of the generated badge.

Usage:
    from club_logos import get_club_logo
    img = get_club_logo("Real Madrid CF")  # returns RGBA Image
"""
import os
import hashlib
from PIL import Image, ImageDraw, ImageFont

LOGO_DIR = os.path.join("assets", "logos")
LOGO_SIZE = 120

# Club color mapping — based on real club primary colors
CLUB_COLORS = {
    "real madrid": ((255, 255, 255), (240, 240, 240), (20, 20, 20)),
    "barcelona": ((165, 25, 45), (140, 15, 35), (255, 255, 255)),
    "manchester united": ((200, 20, 40), (160, 10, 30), (255, 255, 255)),
    "manchester city": ((108, 171, 221), (80, 140, 200), (255, 255, 255)),
    "liverpool": ((200, 20, 40), (160, 10, 30), (255, 255, 255)),
    "chelsea": ((0, 70, 160), (0, 50, 120), (255, 255, 255)),
    "arsenal": ((220, 30, 30), (180, 20, 20), (255, 255, 255)),
    "tottenham": ((255, 255, 255), (230, 230, 230), (20, 40, 80)),
    "bayern": ((220, 20, 20), (180, 15, 15), (255, 255, 255)),
    "dortmund": ((240, 200, 0), (220, 180, 0), (20, 20, 20)),
    "juventus": ((20, 20, 20), (40, 40, 40), (255, 255, 255)),
    "ac milan": ((200, 20, 40), (40, 40, 40), (255, 255, 255)),
    "inter": ((0, 100, 200), (40, 40, 40), (255, 255, 255)),
    "atletico": ((40, 40, 120), (20, 20, 80), (255, 255, 255)),
    "psg": ((20, 20, 60), (10, 10, 40), (255, 255, 255)),
    "napoli": ((0, 120, 200), (0, 90, 160), (255, 255, 255)),
    "roma": ((140, 20, 30), (100, 10, 20), (255, 215, 0)),
    "ajax": ((220, 20, 20), (180, 15, 15), (255, 255, 255)),
    "porto": ((20, 40, 120), (10, 20, 80), (255, 255, 255)),
    "benfica": ((200, 20, 40), (160, 10, 30), (255, 255, 255)),
    "sevilla": ((200, 20, 40), (160, 10, 30), (255, 255, 255)),
    "celtic": ((0, 140, 60), (0, 100, 40), (255, 255, 255)),
    "rangers": ((40, 80, 180), (20, 50, 130), (255, 255, 255)),
    "aston villa": ((120, 40, 160), (80, 20, 120), (255, 215, 0)),
    "newcastle": ((20, 20, 20), (40, 40, 40), (255, 255, 255)),
    "valencia": ((20, 40, 120), (10, 20, 80), (255, 255, 255)),
    "villarreal": ((240, 200, 0), (220, 180, 0), (20, 20, 20)),
    "athletic": ((200, 20, 40), (160, 10, 30), (255, 255, 255)),
    "sporting": ((0, 140, 60), (0, 100, 40), (255, 255, 255)),
    "betis": ((0, 120, 80), (0, 90, 60), (255, 255, 255)),
}

# Club abbreviations
CLUB_ABBR = {
    "real madrid": "RMA", "barcelona": "BAR", "manchester united": "MUN",
    "manchester city": "MCI", "liverpool": "LIV", "chelsea": "CHE",
    "arsenal": "ARS", "tottenham": "TOT", "bayern": "BAY",
    "dortmund": "BVB", "juventus": "JUV", "ac milan": "MIL",
    "inter milan": "INT", "inter": "INT", "atletico": "ATM",
    "paris saint": "PSG", "psg": "PSG", "napoli": "NAP",
    "roma": "ROM", "ajax": "AJA", "porto": "POR",
    "benfica": "BEN", "sevilla": "SEV", "celtic": "CEL",
    "rangers": "RAN", "aston villa": "AVL", "newcastle": "NEW",
    "valencia": "VAL", "villarreal": "VIL", "athletic": "ATH",
    "sporting": "SCP", "betis": "BET", "leverkusen": "LEV",
    "leipzig": "RBL", "lazio": "LAZ", "atalanta": "ATA",
    "fiorentina": "FIO", "monaco": "MON", "lyon": "LYO",
    "marseille": "MAR", "psv": "PSV", "eindhoven": "PSV",
    "porto": "FCP", "galatasaray": "GAL", "shakhtar": "SHK",
    "olympiacos": "OLY", "benfica": "SLB",
}


def _slug(name):
    import unicodedata
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_only = nfkd.encode("ascii", "ignore").decode("ascii")
    out = ""
    for ch in ascii_only.lower():
        out += ch if ch.isalnum() else "-"
    return "-".join(p for p in out.split("-") if p)


def _get_colors(name):
    """Get (outer, inner, text) colors for a club."""
    import unicodedata
    nfkd = unicodedata.normalize("NFKD", name)
    low = nfkd.encode("ascii", "ignore").decode("ascii").lower()
    for key, colors in CLUB_COLORS.items():
        if key in low:
            return colors
    # Default: dark blue badge
    return ((30, 50, 90), (15, 30, 60), (200, 220, 250))


def _get_abbr(name):
    """Get 3-letter abbreviation for a club."""
    import unicodedata
    nfkd = unicodedata.normalize("NFKD", name)
    low = nfkd.encode("ascii", "ignore").decode("ascii").lower()
    for key, abbr in CLUB_ABBR.items():
        if key in low:
            return abbr
    # Generate from initials
    words = name.replace("FC", "").replace("CF", "").replace("SC", "").split()
    if len(words) >= 2:
        return "".join(w[0] for w in words[:3]).upper()
    return name[:3].upper()


def _font(size):
    from squad_card import FD
    return FD(size)


_cache = {}
_file_scan_cache = None  # cached directory listing

# Known alternate names → canonical slug (for clubs with spelling differences
# between English and the FL26 data's native spelling)
_CLUB_ALIASES = {
    # data name (lowercased, accent-stripped) : english slug
    "munchen": "munich",        # Bayern München → munich
    "koln": "cologne",
    "dusseldorf": "dusseldorf",
    "monchengladbach": "gladbach",
    "mainz-05": "mainz",
    "furth": "furth",
    "dunajska-streda": "dunajska",
}

# Suffixes to strip when matching logos (so "Real Madrid" matches "Real Madrid CF")
_STRIP_SUFFIXES = [
    "fc", "cf", "ac", "sc", "afc", "sl", "ssc", "ss", "bc", "rc",
    "cd", "sv", "vfl", "vfb", "tsg", "rb", "as", "ss", "usc",
]


def _core_slug(slug):
    """Strip common football suffixes from a slug for fuzzy matching.
    e.g. 'real-madrid-cf' -> 'real-madrid', 'fc-barcelona' -> 'barcelona'"""
    parts = slug.split("-")
    while parts and parts[-1] in _STRIP_SUFFIXES:
        parts.pop()
    while parts and parts[0] in _STRIP_SUFFIXES:
        parts.pop(0)
    return "-".join(parts)


def _scan_logo_files():
    """List all .png files in LOGO_DIR. NOT cached — re-scans each time so
    logos added at runtime are picked up without a restart."""
    result = {}
    if os.path.isdir(LOGO_DIR):
        for f in os.listdir(LOGO_DIR):
            if f.lower().endswith(".png"):
                s = f[:-4].lower()
                result[s] = os.path.join(LOGO_DIR, f)
    return result


def _find_logo_file(name):
    """Find a logo PNG by fuzzy-matching the club name.
    
    Tries in order:
      1. Exact slug match         (real-madrid-cf -> real-madrid-cf.png)
      2. Core slug match          (real-madrid-cf -> real-madrid.png)
      3. File whose core contains lookup core, or vice versa
    Returns filepath or None.
    """
    files = _scan_logo_files()
    if not files:
        return None

    slug = _slug(name)

    # apply known spelling aliases (munchen -> munich etc)
    for native, eng in _CLUB_ALIASES.items():
        if native in slug:
            slug = slug.replace(native, eng)

    # 1) exact
    if slug in files:
        return files[slug]

    # 2) core match (strip FC/CF/AC etc from both sides)
    core = _core_slug(slug)
    if core != slug and core in files:
        return files[core]

    # 3) fuzzy: does any file's core contain ours, or ours contain theirs?
    for file_slug, path in files.items():
        file_core = _core_slug(file_slug)
        if file_core == core:
            return path
        if len(core) >= 4 and (core in file_core or file_core in core):
            return path

    return None


def get_club_logo(name, size=LOGO_SIZE):
    """Get a club logo image. Returns RGBA Image.
    
    If a real PNG exists in assets/logos/ (fuzzy-matched by name), it's used.
    Otherwise a generated badge is created.
    """
    if name in _cache:
        return _cache[name].resize((size, size), Image.LANCZOS)

    # Try to find a real logo file (fuzzy match)
    logo_path = _find_logo_file(name)
    if logo_path and os.path.exists(logo_path):
        try:
            img = Image.open(logo_path).convert("RGBA")
            _cache[name] = img
            return img.resize((size, size), Image.LANCZOS)
        except Exception:
            pass

    # Generate badge
    img = _generate_badge(name, LOGO_SIZE)
    _cache[name] = img
    return img.resize((size, size), Image.LANCZOS)


def _generate_badge(name, size):
    """Generate a clean circular badge with club initials."""
    outer, inner, text_color = _get_colors(name)
    abbr = _get_abbr(name)

    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    cx = size // 2
    r = size // 2 - 2

    # Outer ring
    d.ellipse([cx - r, cx - r, cx + r, cx + r], fill=outer)

    # Inner circle (slightly smaller, gradient effect)
    inner_r = r - 3
    d.ellipse([cx - inner_r, cx - inner_r, cx + inner_r, cx + inner_r], fill=inner)

    # Text
    font = _font(size // 3)
    bbox = d.textbbox((0, 0), abbr, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    tx = cx - tw // 2 - bbox[0]
    ty = cx - th // 2 - bbox[1]
    d.text((tx, ty), abbr, font=font, fill=text_color)

    return img


def circular_logo(name, size, ring_w=0, ring_colour=None):
    """Get a logo as a circular image with optional ring (for cards)."""
    logo = get_club_logo(name, size - (ring_w * 2 if ring_w else 0))
    if ring_w and ring_colour:
        canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        d = ImageDraw.Draw(canvas)
        d.ellipse([0, 0, size - 1, size - 1], fill=ring_colour)
        canvas.paste(logo, (ring_w, ring_w), logo)
        return canvas
    return logo
