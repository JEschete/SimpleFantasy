import pygame as pg
from settings import draw_text, WHITE, SILVER, GOLD, FONT_BIG, FONT, PANEL_MARGIN, SCREEN_W, SCREEN_H
from data.inventory import EQUIP_SLOTS, ITEMS

class CharacterSheet:
    def __init__(self, hero):
        self.hero = hero
        self.rect = pg.Rect(PANEL_MARGIN, 90, 560, 380)

    def draw(self, surf):
        pg.draw.rect(surf, (24,24,32), self.rect, border_radius=12)
        pg.draw.rect(surf, (70,70,90), self.rect, 2, border_radius=12)
        x, y = self.rect.x + 16, self.rect.y + 16
        h = self.hero
        draw_text(surf, "Character Sheet", x, y, GOLD, FONT_BIG); y += 36
        draw_text(surf, f"Level: {h.level()}  XP: {h.xp}/{h.xp_to_next_level}", x, y); y += 22
        draw_text(surf, f"HP: {h.hp}/{h.max_hp()}  MP: {h.mp}/{h.max_mp()}", x, y); y += 22
        draw_text(surf, f"ATK: {h.attack()}  MAG: {h.magic()}  DEF: {h.defense()}", x, y); y += 22
        draw_text(surf, f"Gil: {h.gil}", x, y, GOLD); y += 30
        draw_text(surf, "Equipment:", x, y, SILVER); y += 24
        for slot in EQUIP_SLOTS:
            item_id = h.equipment.get(slot)
            name = ITEMS[item_id].name if item_id else "(none)"
            draw_text(surf, f"{slot.capitalize():>7}: {name}", x+12, y); y += 20
        y += 10
        draw_text(surf, h.quest.summary(), x, y, SILVER)

class JournalOverlay:
    def __init__(self, hero):
        self.hero = hero
        self.rect = pg.Rect(PANEL_MARGIN, 490, 560, 300)

    def draw(self, surf):
        pg.draw.rect(surf, (24,24,30), self.rect, border_radius=12)
        pg.draw.rect(surf, (70,70,90), self.rect, 2, border_radius=12)
        x, y = self.rect.x + 16, self.rect.y + 16
        draw_text(surf, "Journal", x, y, GOLD, FONT_BIG); y += 34
        lines = self.hero.quest.all_status_lines()
        if not lines:
            draw_text(surf, "(No quests)", x, y, SILVER); return
        for ln in lines:
            draw_text(surf, ln, x, y, WHITE); y += 20
