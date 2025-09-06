import pygame as pg
from settings import draw_text, WHITE, SILVER, GOLD, FONT, FONT_BIG, SCREEN_W, SCREEN_H

ATTR_OPTIONS = ["HP","+10","MP","+6","ATK","+2","MAG","+2","DEF","+1"]
STAT_CHOICES = ["HP","MP","ATK","MAG","DEF"]
MASTERY_CHOICES = ["FIRE","ICE","ELECTRIC","WATER","POISON"]

class TalentOverlay:
    def __init__(self, hero):
        self.hero = hero
        w, h = 640, 420
        self.rect = pg.Rect((SCREEN_W - w)//2, (SCREEN_H - h)//2, w, h)
        self.cursor_section = 0  # 0 attributes / 1 mastery
        self.attr_index = 0
        self.mast_index = 0

    def handle_key(self, key):
        if key in (pg.K_TAB,):
            self.cursor_section = 1 - self.cursor_section
        elif self.cursor_section == 0:
            if key in (pg.K_UP, pg.K_w):
                self.attr_index = (self.attr_index - 1) % len(STAT_CHOICES)
            elif key in (pg.K_DOWN, pg.K_s):
                self.attr_index = (self.attr_index + 1) % len(STAT_CHOICES)
            elif key in (pg.K_RETURN, pg.K_SPACE):
                if self.hero.invest_attribute(STAT_CHOICES[self.attr_index]):
                    pass
        else:
            if key in (pg.K_UP, pg.K_w):
                self.mast_index = (self.mast_index - 1) % len(MASTERY_CHOICES)
            elif key in (pg.K_DOWN, pg.K_s):
                self.mast_index = (self.mast_index + 1) % len(MASTERY_CHOICES)
            elif key in (pg.K_RETURN, pg.K_SPACE):
                if self.hero.invest_mastery(MASTERY_CHOICES[self.mast_index]):
                    pass

    def draw(self, surf: pg.Surface):
        pg.draw.rect(surf, (26,28,38), self.rect, border_radius=14)
        pg.draw.rect(surf, (80,80,110), self.rect, 2, border_radius=14)
        x = self.rect.x + 20
        y = self.rect.y + 16
        draw_text(surf, "Talent Panel", x, y, GOLD, FONT_BIG); y += 34
        draw_text(surf, f"Talent Points: {self.hero.talent_points}", x, y, WHITE, FONT); y += 28
        draw_text(surf, "Attributes", x, y, SILVER, FONT); y += 20
        for i, stat in enumerate(STAT_CHOICES):
            sel = (self.cursor_section == 0 and i == self.attr_index)
            col = GOLD if sel else WHITE
            draw_text(surf, f"{'> ' if sel else '  '}{stat}", x, y, col, FONT)
            y += 20
        y += 10
        draw_text(surf, "Elemental Mastery (+4 spell power each)", x, y, SILVER, FONT); y += 20
        for i, elem in enumerate(MASTERY_CHOICES):
            sel = (self.cursor_section == 1 and i == self.mast_index)
            col = GOLD if sel else WHITE
            rank = self.hero.spell_mastery.get(elem,0)
            draw_text(surf, f"{'> ' if sel else '  '}{elem} [{rank}]", x, y, col, FONT)
            y += 20
        y += 16
        draw_text(surf, "TAB switch section  ENTER spend  T/ESC close", x, y, SILVER, FONT)
