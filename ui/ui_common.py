# ui/ui_common.py
import pygame as pg
from typing import Optional, Tuple, Dict, Any
from settings import WHITE, BLACK, SILVER, GOLD, BLUE, draw_text

Vec2 = Tuple[int, int]
CELL = 56        # inventory/equipment cell size
PAD  = 8

def draw_panel(surf: pg.Surface, rect: pg.Rect, title: Optional[str] = None):
    pg.draw.rect(surf, (28, 28, 36), rect, border_radius=10)
    pg.draw.rect(surf, (64, 64, 80), rect, 2, border_radius=10)
    if title:
        draw_text(surf, title, rect.x + 8, rect.y - 22, SILVER)

class Draggable:
    """Generic drag payload carried by the mouse."""
    def __init__(self):
        self.payload: Optional[Dict[str, Any]] = None
        self.offset = (0, 0)

    def begin(self, payload: Dict[str, Any], mouse: Vec2):
        self.payload = payload
        r = payload["rect"]
        self.offset = mouse[0] - r.x, mouse[1] - r.y

    def end(self) -> Optional[Dict[str, Any]]:
        p = self.payload
        self.payload = None
        return p

    def draw(self, surf: pg.Surface, mouse: Vec2):
        if not self.payload: return
        icon = self.payload.get("icon")
        r = self.payload["rect"].copy()
        r.topleft = (mouse[0] - self.offset[0], mouse[1] - self.offset[1])
        if icon:
            surf.blit(icon, r)
        else:
            pg.draw.rect(surf, BLUE, r, border_radius=6)
            pg.draw.rect(surf, (0,0,0), r, 2, border_radius=6)
        cnt = self.payload.get("count", 1)
        if cnt > 1:
            draw_text(surf, str(cnt), r.right - 18, r.bottom - 20, WHITE)
