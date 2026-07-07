"""
Bench View v5 — simple, anti-slop, same cards as squad view.

5 fixed slots. Filled with real cards or EMPTY cards.
No section dividers, no badges, no grid patterns.
Just a clean row of cards on the ocean background.
"""
import io
from PIL import Image, ImageDraw, ImageFont, ImageFilter

import economy as E
from squad_card import (F, FD, fetch_face, silhouette, circular,
                        text_centered, fit_font, paste_shadow,
                        _v_gradient, build_card,
                        TIER_COLORS, WHITE, T2, T3,
                        BG_TOP, BG_BOTTOM, CARD_BG, CARD_BG2,
                        GLOW_BLUE, GLOW_CORAL, SILHOUETTE,
                        BORDER)

MAX_BENCH_SLOTS = 5


def render_bench_card(guild_id, team_name, user_id, squad, xi_keys, avatar_url=None):
    """5-card bench row. Same cards as squad view. EMPTY for missing slots."""
    benched = [p for p in squad if p["key"] not in xi_keys]
    benched.sort(key=lambda p: p["ovr"], reverse=True)

    CW = 200
    CH = 250
    GAP = 20
    SIDE_PAD = 24
    header_h = 100
    footer_h = 64

    # Always 5 slots
    total_w = SIDE_PAD * 2 + MAX_BENCH_SLOTS * CW + (MAX_BENCH_SLOTS - 1) * GAP
    cards_y = header_h + 30
    H = cards_y + CH + 30 + footer_h

    canvas = Image.new("RGBA", (total_w, H), (0, 0, 0, 0))
    bg = _v_gradient(total_w, H, BG_TOP, BG_BOTTOM)
    canvas.paste(bg, (0, 0))

    # Subtle glow
    for bx, by, br, bc in [
        (total_w // 4, 50, 100, (100, 180, 255, 7)),
        (total_w * 3 // 4, H - 50, 120, (255, 130, 100, 4)),
    ]:
        blob = Image.new("RGBA", (br * 2, br * 2), (0, 0, 0, 0))
        ImageDraw.Draw(blob).ellipse([0, 0, br * 2 - 1, br * 2 - 1], fill=bc)
        blob = blob.filter(ImageFilter.GaussianBlur(50))
        canvas.alpha_composite(blob, (bx - br, by - br))

    d = ImageDraw.Draw(canvas)

    # ── Header — clean, no badges ───────────────────────────────────
    header_grad = _v_gradient(total_w, header_h, (10, 22, 38), (4, 10, 18))
    canvas.alpha_composite(header_grad, (0, 0))
    d = ImageDraw.Draw(canvas)
    d.rectangle([0, header_h - 3, total_w, header_h], fill=(40, 70, 110))

    logo_r = 34
    logo_cx = 52
    logo_cy = header_h // 2
    logo_url = E.get_team_logo(guild_id, user_id) or avatar_url
    logo_im = None
    if logo_url:
        from squad_card import fetch_avatar_sync
        raw = fetch_avatar_sync(logo_url)
        if raw:
            logo_im = circular(raw, logo_r * 2, ring_w=3, ring_colour=GLOW_BLUE)
    if logo_im is None:
        logo_im = circular(silhouette(logo_r * 2, SILHOUETTE), logo_r * 2, ring_w=3, ring_colour=GLOW_BLUE)
    canvas.alpha_composite(logo_im, (logo_cx - logo_im.width // 2, logo_cy - logo_im.height // 2))

    d = ImageDraw.Draw(canvas)
    team_display = team_name.upper()
    d.text([100, header_h // 2 - 26], team_display, font=FD(36), fill=(0, 0, 0, 100))
    d.text([98, header_h // 2 - 28], team_display, font=FD(36), fill=WHITE)
    d.text([99, header_h // 2 + 14], "B E N C H", font=F(14, bold=True), fill=GLOW_CORAL)

    # ── 5 cards in a clean row ──────────────────────────────────────
    cards_total_w = MAX_BENCH_SLOTS * CW + (MAX_BENCH_SLOTS - 1) * GAP
    cards_start_x = (total_w - cards_total_w) // 2

    for i in range(MAX_BENCH_SLOTS):
        x = cards_start_x + i * (CW + GAP)
        y = cards_y
        if i < len(benched):
            card = build_card(benched[i], CW, CH)
        else:
            card = build_card(None, CW, CH)
        paste_shadow(canvas, card, (x, y), blur=14, opacity=120, offset=(3, 8))

    d = ImageDraw.Draw(canvas)

    # ── Footer — same structure as squad card ───────────────────────
    foot_grad = _v_gradient(total_w, footer_h, (4, 10, 18), (8, 20, 36))
    canvas.alpha_composite(foot_grad, (0, H - footer_h))
    d = ImageDraw.Draw(canvas)
    d.rectangle([0, H - footer_h, total_w, H - footer_h + 3], fill=(40, 70, 110))
    fy = H - footer_h // 2
    f_label_y = fy - 14
    f_value_y = fy + 6

    sv = E.squad_value(squad)
    bal = E.get_balance(guild_id, user_id)
    bench_count = len(benched)

    text_centered(d, (total_w * 0.2, f_label_y), "BENCH", F(12, bold=True), T3)
    text_centered(d, (total_w * 0.2, f_value_y), f"{bench_count}/{MAX_BENCH_SLOTS}", FD(24), WHITE)

    text_centered(d, (total_w * 0.45, f_label_y), "SQUAD VALUE", F(12, bold=True), T3)
    text_centered(d, (total_w * 0.45, f_value_y), E.money(sv), FD(24), GLOW_BLUE)

    text_centered(d, (total_w * 0.75, f_label_y), "BUDGET", F(12, bold=True), T3)
    text_centered(d, (total_w * 0.75, f_value_y), E.money(bal), FD(24), GLOW_CORAL)

    buf = io.BytesIO()
    canvas.convert("RGB").save(buf, "PNG", optimize=True)
    buf.seek(0)
    return buf
