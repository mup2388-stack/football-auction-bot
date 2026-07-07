"""
embed_colors.py — the ONE source of truth for embed accent colors.

Consolidates the bot's old rainbow (9 random hexes) into a tight 5-color
semantic palette so every embed reads as one premium product.

Taste-Skill rule: one accent across the whole page; no random color swaps.
Impeccable rule: never pure black; tinted neutrals.

Plain ints (not discord.Color) so this module has no hard dependencies and
stays unit-testable.  discord.Embed(color=C.AMBER) accepts raw ints fine.
"""


class C:
    """Embed colour tokens. Use these instead of raw 0x hex literals."""

    # Primary accent — money, stats, premium, headings
    AMBER    = 0xFFBA46

    # Success — SOLD, squad complete, wins
    EMERALD  = 0x2ECC71

    # Error / negative — red cards, incomplete, loss
    CRIMSON  = 0xE74C3C

    # Neutral — secondary info, lists, archives
    SLATE    = 0x5B5B6B

    # League / tournament — standings, fixtures, brackets
    OBSIDIAN = 0x1C1C26

    # Soft positive — phase set, info confirmations
    TEAL     = 0x1ABC9C

    # Yellow / red card accents (for stat rows)
    YELLOW   = 0xF1C40F
    RED      = 0xE74C3C

    # ── semantic helpers ──────────────────────────────────
    @staticmethod
    def success(ok: bool):
        """Green if ok else red."""
        return C.EMERALD if ok else C.CRIMSON
