# shop_ui.py
import pygame as pg
from typing import List, Optional, Tuple
from ui.ui_common import CELL, PAD, draw_panel, Draggable
from settings import BLACK, SILVER, GOLD, WHITE, draw_text, FONT, FONT_BIG
from data.inventory import ITEMS, item_price

_icon_cache: dict[str, pg.Surface] = {}
try:
    from world.ground import _icon_for
except ModuleNotFoundError:
    _icon_for = None

def _make_fallback_icon(item_id: str) -> pg.Surface:
    s = pg.Surface((CELL, CELL), pg.SRCALPHA)
    kind = ITEMS[item_id].kind
    color = {
        "consumable": (170, 60, 60),
        "spell_tome": (120, 70, 150),
        "equipment": (170, 140, 60),
    }.get(kind, (90, 120, 180))
    s.fill(color)
    pg.draw.rect(s, (0,0,0), s.get_rect(), 2, border_radius=6)
    draw_text(s, ITEMS[item_id].name[:2].upper(), 8, 6, WHITE)
    return s

Vec2 = Tuple[int,int]

class ShopUI:
    """
    Drag to buy: drag from shop grid → inventory grid.
    Selling is initiated by dropping from InventoryUI onto ShopUI area (handled by InventoryUI).
    """
    def __init__(self, pos: Vec2=(24, 380), cols: int=5, rows: int=3, title="Shop"):
        self.cols, self.rows = cols, rows
        self.pos = pos
        w = PAD*2 + CELL*cols
        h = PAD*2 + CELL*rows + 26
        self.rect = pg.Rect(pos[0], pos[1], w, h)
        self.grid_rect = pg.Rect(self.rect.x + PAD, self.rect.y + PAD + 20, CELL*cols, CELL*rows)
        self.title = title
        self.stock: List[str] = []   # list of item_ids (infinite stock by default)
        self.drag = Draggable()
        self.opened = False
        # gold handlers
        self.get_gold = lambda: 0
        self.add_gold = lambda n: None
        # buyer callback: f(item_id, qty)->bool
        self.try_add_to_inventory = None

    def set_stock(self, item_ids: List[str]):
        self.stock = item_ids[:self.cols*self.rows]

    def open(self): self.opened = True
    def close(self): self.opened = False

    def _slot_at(self, mouse: Vec2):
        if not self.grid_rect.collidepoint(mouse): return None
        lx, ly = mouse[0]-self.grid_rect.x, mouse[1]-self.grid_rect.y
        c, r = lx//CELL, ly//CELL
        if 0 <= c < self.cols and 0 <= r < self.rows:
            return int(c), int(r)
        return None

    def _build_tooltip_lines(self, item_id: str):
        idef = ITEMS[item_id]
        lines = [idef.name, f"Price: {item_price(item_id)}"]
        if idef.desc:
            lines.append(idef.desc)
        if idef.kind == "equipment" and idef.stats:
            stat_parts = []
            for k,v in idef.stats.items():
                stat_parts.append(f"{k[:3].upper()}+{v}")
            if stat_parts:
                lines.append(" ".join(stat_parts))
        if idef.kind == "spell_tome" and idef.unlock_spell:
            lines.append(f"Teaches {idef.unlock_spell}")
        return lines

    def _draw_tooltip(self, surf: pg.Surface, mouse: Vec2, item_id: str):
        lines = self._build_tooltip_lines(item_id)
        if not lines: return
        pad = 8
        w = max(FONT.size(l)[0] for l in lines) + pad*2
        h = (FONT.get_height()+2) * len(lines) + pad*2
        x, y = mouse
        x += 18; y += 12
        # keep on-screen
        if x + w > surf.get_width(): x = surf.get_width() - w - 4
        if y + h > surf.get_height(): y = surf.get_height() - h - 4
        rect = pg.Rect(x, y, w, h)
        pg.draw.rect(surf, (30,30,42), rect, border_radius=8)
        pg.draw.rect(surf, (90,90,120), rect, 2, border_radius=8)
        cy = y + pad
        for i, ln in enumerate(lines):
            col = GOLD if i == 0 else WHITE
            draw_text(surf, ln, x + pad, cy, col, FONT)
            cy += FONT.get_height() + 2

    def is_over(self, mouse: Vec2) -> bool:
        return self.rect.collidepoint(mouse)

    def _icon(self, item_id: str) -> pg.Surface:
        surf = _icon_cache.get(item_id)
        if surf: return surf
        if _icon_for:
            surf = _icon_for(item_id)
        else:
            surf = _make_fallback_icon(item_id)
        _icon_cache[item_id] = surf
        return surf

    def handle_event(self, ev: pg.event.Event):
        if not self.opened: return
        mouse = pg.mouse.get_pos()
        if ev.type == pg.MOUSEBUTTONDOWN and ev.button == 1:
            s = self._slot_at(mouse)
            if s:
                c, r = s
                idx = r*self.cols + c
                if 0 <= idx < len(self.stock):
                    iid = self.stock[idx]
                    rect = pg.Rect(self.grid_rect.x + c*CELL, self.grid_rect.y + r*CELL, CELL, CELL)
                    self.drag.begin({"src":"shop","c":c,"r":r,"id":iid,"count":1,"rect":rect,"icon":self._icon(iid)}, mouse)
        elif ev.type == pg.MOUSEBUTTONUP and ev.button == 1:
            p = self.drag.end()
            if p and p["src"] == "shop":
                # attempt purchase if dropped over inventory (caller passes callback)
                if self.try_add_to_inventory:
                    price = item_price(p["id"])
                    if self.get_gold() >= price and self.try_add_to_inventory(p["id"], 1):
                        self.add_gold(-price)  # purchase succeeds
                    # else: not enough gold or no space -> do nothing (item stays in shop)

        elif ev.type == pg.KEYDOWN and ev.key in (pg.K_ESCAPE, pg.K_q):
            self.close()

    def draw(self, surf: pg.Surface):
        if not self.opened: return
        draw_panel(surf, self.rect, self.title)
        draw_text(surf, f"Gold: {self.get_gold()}", self.rect.x + 10, self.rect.y + 2, GOLD)
        hover_item = None
        mouse = pg.mouse.get_pos()
        hover_slot = self._slot_at(mouse)
        for r in range(self.rows):
            for c in range(self.cols):
                cell = pg.Rect(self.grid_rect.x + c*CELL, self.grid_rect.y + r*CELL, CELL, CELL)
                pg.draw.rect(surf, BLACK, cell, border_radius=6)
                border_col = SILVER
                idx = r*self.cols + c
                if hover_slot and (c, r) == hover_slot and 0 <= idx < len(self.stock):
                    border_col = GOLD
                    hover_item = self.stock[idx]
                pg.draw.rect(surf, border_col, cell, 1, border_radius=6)
                if 0 <= idx < len(self.stock):
                    iid = self.stock[idx]
                    surf.blit(self._icon(iid), cell)
        # dragged from shop
        self.drag.draw(surf, pg.mouse.get_pos())
        # tooltip last (above drag icon)
        if hover_item:
            self._draw_tooltip(surf, mouse, hover_item)
