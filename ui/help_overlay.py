import pygame as pg
from settings import draw_text, WHITE, SILVER, GOLD, FONT, FONT_BIG, SCREEN_W, SCREEN_H, wrap_text

HELP_LINES = [
    "Overworld:",
    "  Move: Arrow Keys / WASD",
    "  I Inventory   C Character   J Journal   H Help",
    "  L Toggle Auto-Loot   G Pick Nearest Item   Click Pick Item",
    "  1 Use Potion   2 Use Ether   P Potion   E Ether",
    "  ENTER Talk / Open Shop (when near)   ESC Close / Quit (double press)",
    "  F5 Save   F9 Load",
    "  Shop: R Reroll Stock (first reroll each day FREE, then 50 Gil)",
    "",
    "Battle:",
    "  Arrow Keys / WASD: Navigate targets / menus",
    "  ENTER / SPACE: Confirm   ESC / BACKSPACE: Back",
    "  TAB: Toggle Compact Log",
    "",
    "General:",
    "  Auto-Loot picks items in radius periodically.",
    "  Double-click inventory equipment to equip; double-click equipped slot to unequip.",
    "  Drag items to shop to sell; drag from shop to buy.",
    "",
    "  T Talent Panel (spend points on attributes / masteries)",
    "",
    "Classes: Fighter (no magic), Thief (Steal), Black Mage (black magic), White Mage (white magic)",
    "Thief: Steal command in battle (chance for extra item).",
    "",
    "  M Party Management (rename, reorder, dismiss)",
    "",
    "Press H or ESC to close."
]

class HelpOverlay:
    def __init__(self):
        self.max_width = 860          # initial target width (can shrink if screen smaller)
        self.side_pad = 20
        self.top_pad = 18
        self.line_h = 22
        self.section_gap = 8
        w = min(self.max_width, SCREEN_W - 120)
        self.rect = pg.Rect((SCREEN_W - w)//2, (SCREEN_H - 520)//2, w, 520)  # height recomputed each draw

    def _compute_wrapped(self):
        inner_w = self.rect.w - self.side_pad*2
        wrapped = []
        for raw in HELP_LINES:
            if raw == "":
                wrapped.append("")  # blank spacer line
                continue
            if raw.endswith(":"):
                wrapped.append(raw)  # headings stay single line
                continue
            # normal text: wrap
            for ln in wrap_text(raw, FONT, inner_w):
                wrapped.append(ln)
        return wrapped

    def draw(self, surf: pg.Surface):
        # Re-wrap & adjust height dynamically
        lines = self._compute_wrapped()
        # compute needed height
        content_h = self.top_pad + 38  # title block
        for ln in lines:
            content_h += self.line_h
        content_h += 18  # bottom padding
        max_h = SCREEN_H - 120
        self.rect.h = min(content_h, max_h)

        # background
        pg.draw.rect(surf, (22,24,32), self.rect, border_radius=14)
        pg.draw.rect(surf, (80,80,105), self.rect, 2, border_radius=14)

        x = self.rect.x + self.side_pad
        y = self.rect.y + self.top_pad
        draw_text(surf, "Help / Keybinds", x, y, GOLD, FONT_BIG)
        y += 38

        for ln in lines:
            if y + self.line_h > self.rect.bottom - 12:
                # stop if overflow (should not normally happen unless screen very small)
                break
            if ln == "":
                y += self.line_h
                continue
            col = SILVER if ln.endswith(":") else WHITE
            draw_text(surf, ln, x, y, col, FONT)
            y += self.line_h
