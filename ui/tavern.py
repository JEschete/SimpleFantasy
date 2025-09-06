import pygame as pg
from settings import draw_text, WHITE, SILVER, GOLD, RED, FONT, FONT_BIG, SCREEN_W, SCREEN_H

# Second numeric (legacy base cost) kept but ignored; real cost is dynamic via game.get_next_hire_cost().
HIRE_OPTIONS = [
    ("FIGHTER", 150, "Front-line power."),
    ("BLACK_MAGE", 160, "Offensive magic."),
    ("WHITE_MAGE", 160, "Healing magic."),
    ("THIEF", 150, "High agility; can Steal."),
]

class Tavern:
    def __init__(self, game):
        self.g = game
        w, h = 520, 300
        self.rect = pg.Rect((SCREEN_W - w)//2, (SCREEN_H - h)//2, w, h)
        self.cursor = 0

    def handle_key(self, key):
        if key in (pg.K_UP, pg.K_w):
            self.cursor = (self.cursor - 1) % len(HIRE_OPTIONS)
        elif key in (pg.K_DOWN, pg.K_s):
            self.cursor = (self.cursor + 1) % len(HIRE_OPTIONS)
        elif key in (pg.K_RETURN, pg.K_SPACE):
            if len(self.g.party) >= 4:
                if hasattr(self.g.overworld, "set_toast"): self.g.overworld.set_toast("Party full.")
                return
            cls, _, _ = HIRE_OPTIONS[self.cursor]
            if any(m.hero_class == cls for m in self.g.party[1:]):
                if hasattr(self.g.overworld, "set_toast"): self.g.overworld.set_toast("Already hired.")
                return
            cost = self.g.get_next_hire_cost()
            if self.g.hero.gil < cost:
                if hasattr(self.g.overworld, "set_toast"): self.g.overworld.set_toast("Not enough Gil.")
                return
            self.g.hire_companion(cls, cost)

    def draw(self, surf: pg.Surface):
        pg.draw.rect(surf, (28,30,40), self.rect, border_radius=14)
        pg.draw.rect(surf, (80,80,110), self.rect, 2, border_radius=14)
        x = self.rect.x + 18
        y = self.rect.y + 16
        draw_text(surf, "Tavern - Hire Allies", x, y, GOLD, FONT_BIG); y += 30
        next_cost = self.g.get_next_hire_cost()
        draw_text(surf, f"Gil: {self.g.hero.gil}  (Next Hire: {next_cost} Gil)", x, y, GOLD, FONT); y += 26
        draw_text(surf, f"Party {len(self.g.party)}/4", self.rect.x + 360, self.rect.y + 16, SILVER, FONT)

        if len(self.g.party) >= 4:
            draw_text(surf, "Party is full. ESC/Y to close.", self.rect.x + 18, self.rect.y + 70, SILVER, FONT)
            return

        hero_gil = self.g.hero.gil
        for i, (cls, _, desc) in enumerate(HIRE_OPTIONS):
            already = any(m.hero_class == cls for m in self.g.party[1:])
            sel = (i == self.cursor)
            if already:
                col = SILVER
                status = "(Hired)"
            else:
                affordable = hero_gil >= next_cost
                col = GOLD if sel and affordable else (RED if not affordable else WHITE)
                status = f"{next_cost} Gil"
            draw_text(
                surf,
                f"{'> ' if sel else '  '}{cls:<11} {status:<10} {desc}",
                self.rect.x + 22,
                self.rect.y + 70 + i*24,
                col,
                FONT
            )
        y += 12
        draw_text(surf, "UP/DOWN select  ENTER hire  Y/ESC close", x, y, SILVER, FONT)
