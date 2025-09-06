# ground.py
import time
import pygame as pg
from typing import List, Optional, Tuple, Dict
from settings import draw_text, WHITE
from data.inventory import ITEMS

CELL = 56

def _icon_for(item_id: str) -> pg.Surface:
    """Temporary square icon keyed by item kind + first letters."""
    # quick placeholder icon: colored square with 2-letter tag
    s = pg.Surface((CELL, CELL), pg.SRCALPHA)
    kind = ITEMS[item_id].kind
    color = {"consumable": (170, 60, 60),
             "spell_tome": (120, 70, 150),
             "equipment": (170, 140, 60)}.get(kind, (90, 120, 180))
    s.fill(color)
    pg.draw.rect(s, (0,0,0), s.get_rect(), 2, border_radius=6)
    tag = ITEMS[item_id].name[:2].upper()
    draw_text(s, tag, 8, 6, WHITE)
    return s

class GroundItem:
    def __init__(self, pos: Tuple[int,int], item_id: str, count: int, ttl: float=60.0):
        self.pos = pg.Vector2(*pos)
        self.item_id = item_id
        self.count = count
        self.spawn = time.time()
        self.ttl = ttl
        self.rect = pg.Rect(int(self.pos.x) - CELL//2, int(self.pos.y) - CELL//2, CELL, CELL)
        self.icon = _icon_for(item_id)

    @property
    def expired(self) -> bool:
        return (time.time() - self.spawn) >= self.ttl

class GroundManager:
    def __init__(self):
        self.items: List[GroundItem] = []

    def drop(self, pos: Tuple[int,int], item_id: str, count: int=1, ttl: float=60.0):
        self.items.append(GroundItem(pos, item_id, count, ttl))

    def update(self):
        self.items = [g for g in self.items if not g.expired]

    def draw(self, surf: pg.Surface):
        for g in self.items:
            surf.blit(g.icon, g.rect)
            if g.count > 1:
                draw_text(surf, f"x{g.count}", g.rect.x + 6, g.rect.y + CELL - 18, WHITE)

    def pick_at(self, pos: Tuple[int,int]) -> Optional[Tuple[str,int]]:
        for i, g in enumerate(self.items):
            if g.rect.collidepoint(pos):
                self.items.pop(i)
                return (g.item_id, g.count)
        return None
