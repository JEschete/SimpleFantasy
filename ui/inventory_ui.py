# inventory_ui.py
import pygame as pg
from typing import Optional, Tuple, Dict, List, Callable, Any
from ui.ui_common import CELL, PAD, draw_panel, Draggable
from settings import WHITE, SILVER, BLACK, draw_text, GOLD, FONT, FONT_BIG
from data.inventory import ITEMS, EQUIP_SLOTS, use_item
import time

Vec2 = Tuple[int,int]

# Helpers
def _stackable(item_id: str) -> bool:
    return ITEMS[item_id].kind in ("consumable", "spell_tome")

def _max_stack(item_id: str) -> int:
    return 99 if _stackable(item_id) else 1

def _icon(item_id: str) -> pg.Surface:
    # Lazy icon similar to ground
    from world.ground import _icon_for
    return _icon_for(item_id)

class Slot:
    def __init__(self):
        self.id: Optional[str] = None
        self.count: int = 0

    def is_empty(self) -> bool:
        return not self.id

class GridInventoryUI:
    """Grid presentation separate from the dict-based Inventory."""
    def __init__(self, cols: int, rows: int):
        self.cols = cols
        self.rows = rows
        self.slots: List[Slot] = [Slot() for _ in range(cols*rows)]

    def first_empty(self) -> Optional[int]:
        for i,s in enumerate(self.slots):
            if s.is_empty():
                return i
        return None

    def add_stack(self, item_id: str, qty: int) -> bool:
        # try stack onto existing
        if _stackable(item_id):
            for s in self.slots:
                if s.id == item_id and s.count < _max_stack(item_id):
                    room = _max_stack(item_id) - s.count
                    take = min(room, qty)
                    s.count += take
                    qty -= take
                    if qty == 0: return True
        # fill empty slots
        while qty > 0:
            idx = self.first_empty()
            if idx is None: return False
            s = self.slots[idx]
            s.id = item_id
            take = min(_max_stack(item_id), qty)
            s.count = take
            qty -= take
        return True

    def compact_counts(self) -> Dict[str,int]:
        counts: Dict[str,int] = {}
        for s in self.slots:
            if s.id:
                counts[s.id] = counts.get(s.id, 0) + s.count
        return counts

class InventoryUI:
    """
    Inventory + Paper-doll equipment. Works against hero.inventory.counts
    and hero.equipment transparently.
    """
    def __init__(self, hero, pos: Vec2=(24,24), cols: int=8, rows: int=4):
        # ...existing initial field setup unchanged until layout pieces...
        self.hero = hero
        self.grid = GridInventoryUI(cols, rows)
        self.pos = pos
        self.footer_h = 132
        self._doll_w = 200
        self._doll_gap = 24
        self.stat_sheet_w = 210
        self.selected_member_index = 0  # NEW: which party member stats are shown

        # placeholder rects (real sizes set in refresh_party_layout)
        self.rect = pg.Rect(pos[0], pos[1], 800, 480)
        self.grid_rect = pg.Rect(self.rect.x + PAD, self.rect.y + PAD + 20, CELL*cols, CELL*rows)
        self.footer_y = self.grid_rect.bottom + 8
        self.paper_rects: list[pg.Rect] = []   # NEW: one per party member
        self.stats_rect = pg.Rect(0, 0, self.stat_sheet_w, self.grid_rect.h)

        self.drag = Draggable()
        self.open = False

        # Double-click tracking
        self._last_click_time = 0.0
        self._last_click_slot: Optional[int] = None
        self._double_click_interval = 0.40

        # Hover tracking
        self._hover_item_id: Optional[str] = None
        self._hover_rect: Optional[pg.Rect] = None

        # Callback targets (annotated so callable assignment is OK)
        self.is_over_shop: Optional[Callable[[Tuple[int,int]], bool]] = None
        self.on_sell: Optional[Callable[[str,int], None]] = None
        self.on_drop_to_ground: Optional[Callable[[str,int], None]] = None

        self.reload_from_hero()
        # (removed previous un-annotated assignments)
        self.is_over_shop = None; self.on_sell = None; self.on_drop_to_ground = None

        self.refresh_party_layout()  # NEW final layout pass

    # --- NEW: dynamic layout based on party size ---
    def refresh_party_layout(self):
        party = getattr(self.hero, "party", [self.hero])
        party_size = len(party)
        cols = self.grid.cols
        rows = self.grid.rows
        title_h = 20
        grid_h = CELL * rows

        # Left: inventory grid
        grid_w = CELL * cols
        dolls_total_w = party_size * self._doll_w + (party_size - 1) * self._doll_gap if party_size > 0 else 0
        body_w = PAD*2 + grid_w + 32 + dolls_total_w + 16 + self.stat_sheet_w
        body_h = PAD*2 + title_h + grid_h + self.footer_h
        self.rect.w = body_w
        self.rect.h = body_h

        self.grid_rect = pg.Rect(self.rect.x + PAD,
                                 self.rect.y + PAD + title_h,
                                 grid_w, grid_h)
        self.footer_y = self.grid_rect.bottom + 8

        # Paper dolls laid out to right of grid
        start_x = self.grid_rect.right + 32
        self.paper_rects = []
        for i in range(party_size):
            r = pg.Rect(start_x + i * (self._doll_w + self._doll_gap),
                        self.grid_rect.y,
                        self._doll_w,
                        grid_h)
            self.paper_rects.append(r)

        # Stat sheet placed after last doll
        stats_x = (self.paper_rects[-1].right + 16) if self.paper_rects else (self.grid_rect.right + 16)
        self.stats_rect = pg.Rect(stats_x, self.grid_rect.y, self.stat_sheet_w, grid_h)

    # ----- sync -----
    def reload_from_hero(self):
        # fill grid from counts
        self.grid = GridInventoryUI(self.grid.cols, self.grid.rows)
        for item_id, qty in self.hero.inventory.counts.items():
            self.grid.add_stack(item_id, qty)

    def commit_to_hero(self):
        self.hero.inventory.counts = self.grid.compact_counts()
        # equipment already applied directly as we mutate hero.equipment

    # ----- hit tests -----
    def _grid_slot_at(self, mouse: Vec2):
        if not self.grid_rect.collidepoint(mouse): return None
        lx, ly = mouse[0]-self.grid_rect.x, mouse[1]-self.grid_rect.y
        c, r = lx//CELL, ly//CELL
        if 0 <= c < self.grid.cols and 0 <= r < self.grid.rows:
            return int(c), int(r)
        return None

    def _equip_slot_at(self, mouse: Vec2):
        """Return (member_index, slot_index, rect) if mouse over an equipment slot, else None.
        Uses identical geometry to draw() so hit areas align perfectly.
        """
        party = getattr(self.hero, "party", [self.hero])
        for m_idx, doll in enumerate(self.paper_rects):
            if not doll.collidepoint(mouse):
                continue
            for i, _slot_name in enumerate(EQUIP_SLOTS):
                # Same layout math as in draw()
                col = 0 if (i % 2) == 0 else 1
                row = 0 if i < 2 else 1
                slot_x = doll.x + 18 + col * (CELL + 32)
                slot_y = doll.y + 18 + row * (CELL + 46)
                rrect = pg.Rect(slot_x, slot_y, CELL, CELL)
                if rrect.collidepoint(mouse):
                    return m_idx, i, rrect
        return None

    # ----- drag helpers -----
    def _begin_drag_from_grid(self, c: int, r: int, mouse: Vec2):
        idx = r*self.grid.cols + c
        s = self.grid.slots[idx]
        if s.is_empty(): return
        rect = pg.Rect(self.grid_rect.x + c*CELL, self.grid_rect.y + r*CELL, CELL, CELL)
        if s.id is not None:
            self.drag.begin({"src":"grid","c":c,"r":r,"id":s.id,"count":s.count,"rect":rect,"icon":_icon(s.id)}, mouse)
            # remove from slot (lift whole stack)
            s.id = None; s.count = 0

    def _begin_drag_from_equip(self, member_index: int, slot_index: int, erect: pg.Rect, mouse: Vec2):
        party = getattr(self.hero, "party", [self.hero])
        if member_index >= len(party): return
        member = party[member_index]
        slot_name = EQUIP_SLOTS[slot_index]
        item_id = member.equipment.get(slot_name)
        if not item_id: return
        self.drag.begin(
            {"src": "equip", "member": member_index, "slot_index": slot_index,
             "id": item_id, "count": 1, "rect": erect, "icon": _icon(item_id)},
            mouse
        )
        member.equipment[slot_name] = None
        self.selected_member_index = member_index  # focus stats on this member

    def _cancel_drag(self):
        p = self.drag.end()
        if not p: return
        if p["src"] == "grid":
            self.grid.add_stack(p["id"], p["count"])
        elif p["src"] == "equip":
            slot_name = EQUIP_SLOTS[p["slot_index"]]  # FIX: was p["eidx"]
            if self.hero.equipment.get(slot_name) is None:
                self.hero.equipment[slot_name] = p["id"]
            else:
                self.grid.add_stack(p["id"], 1)
        self.commit_to_hero()

    # --- NEW: restored drop handler (was missing) ---
    def _drop_payload(self, mouse: Vec2):
        p = self.drag.end()
        if not p: return
        party = getattr(self.hero, "party", [self.hero])

        # Try equip on paper doll slot
        equip_hit = self._equip_slot_at(mouse)
        if equip_hit:
            m_idx, slot_idx, _ = equip_hit
            if 0 <= m_idx < len(party):
                member = party[m_idx]
                slot_name = EQUIP_SLOTS[slot_idx]
                idef = ITEMS.get(p["id"])
                if idef and idef.kind == "equipment":
                    can_equip = (idef.slot == slot_name)
                    # NEW dual wield: thieves can place a weapon into shield slot as offhand
                    if (not can_equip and
                        member.hero_class == "THIEF" and
                        slot_name == "shield" and
                        idef.slot == "weapon"):
                        can_equip = True
                    if can_equip:
                        prev = member.equipment.get(slot_name)
                        member.equipment[slot_name] = p["id"]
                        if prev:
                            self.grid.add_stack(prev, 1)
                        self.commit_to_hero()
                        self.selected_member_index = m_idx
                        return
        # Inventory grid (always allowed)
        grid_hit = self._grid_slot_at(mouse)
        if grid_hit:
            self.grid.add_stack(p["id"], p["count"])
            self.commit_to_hero()
            return

        # Sell (shop area)
        if self.is_over_shop and self.is_over_shop(mouse) and self.on_sell:
            self.on_sell(p["id"], p["count"])
            self.commit_to_hero()
            return

        # Drop to ground (fallback)
        if self.on_drop_to_ground:
            self.on_drop_to_ground(p["id"], p["count"])
            self.commit_to_hero()

    # --- NEW: double-click use/equip logic ---
    def _try_use_slot_item(self, idx: int):
        if idx < 0 or idx >= len(self.grid.slots): return
        slot = self.grid.slots[idx]
        if not slot.id: return
        item_id = slot.id
        idef = ITEMS[item_id]
        party = getattr(self.hero, "party", [self.hero])
        target_member = party[self.selected_member_index] if party else self.hero

        if idef.kind == "consumable" or idef.kind == "spell_tome":
            msg = use_item(target_member, item_id)
            # Remove one unit if used/learned
            if msg.startswith("Used") or msg.startswith("Learned"):
                slot.count -= 1
                if slot.count <= 0:
                    slot.id = None
            self.commit_to_hero()
            return

        if idef.kind == "equipment" and idef.slot:
            # Equip to selected member if slot matches
            target_slot = idef.slot
            prev = target_member.equipment.get(target_slot)
            # NEW dual wield logic:
            # If weapon and primary weapon occupied, thief can use shield slot as offhand.
            if (idef.slot == "weapon"
                and prev
                and target_member.hero_class == "THIEF"):
                off_prev = target_member.equipment.get("shield")
                # allow if shield slot empty OR currently holds a non-weapon (any item) -> we replace it
                if off_prev is None or ITEMS[off_prev].slot != "weapon":
                    target_slot = "shield"
                    prev = off_prev
            target_member.equipment[target_slot] = item_id
            # Remove equipped piece from inventory
            slot.count -= 1
            if slot.count <= 0:
                slot.id = None
            # Return previous gear (if any) to inventory
            if prev:
                self.grid.add_stack(prev, 1)
            self.commit_to_hero()

    # --- NEW: tooltip helper ---
    def _build_tooltip_lines(self, item_id: str) -> List[str]:
        idef = ITEMS[item_id]
        lines = [idef.name]
        if idef.kind == "equipment":
            if idef.stats:
                stat_parts = []
                for k, v in idef.stats.items():
                    if k.startswith("res_"):
                        stat_parts.append(f"{k[4:].upper()} RES {v:+d}%")
                    else:
                        stat_parts.append(f"{k[:3].upper()}{v:+d}")
                if stat_parts:
                    lines.append(" ".join(stat_parts))
        if idef.desc:
            lines.append(idef.desc)
        if idef.kind == "spell_tome" and idef.unlock_spell:
            lines.append(f"Teaches {idef.unlock_spell}")
        lines.append(f"Value: {idef.price} Gil")
        return lines

    def _draw_tooltip(self, surf: pg.Surface):
        if not self._hover_item_id or not self._hover_rect: return
        lines = self._build_tooltip_lines(self._hover_item_id)
        if not lines: return
        pad = 8
        w = max(FONT.size(l)[0] for l in lines) + pad*2
        h = (FONT.get_height()+2)*len(lines) + pad*2
        x = self._hover_rect.right + 12
        y = self._hover_rect.top - 4
        if x + w > surf.get_width(): x = surf.get_width() - w - 4
        if y + h > surf.get_height(): y = surf.get_height() - h - 4
        rect = pg.Rect(x, y, w, h)
        pg.draw.rect(surf, (32,32,44), rect, border_radius=8)
        pg.draw.rect(surf, (90,90,120), rect, 2, border_radius=8)
        cy = rect.y + pad
        for i, ln in enumerate(lines):
            col = GOLD if i == 0 else WHITE
            draw_text(surf, ln, rect.x + pad, cy, col, FONT)
            cy += FONT.get_height()+2

    # ----- events & draw -----
    def handle_event(self, ev: pg.event.Event):
        mouse = pg.mouse.get_pos()
        self._hover_item_id = None; self._hover_rect = None
        if ev.type == pg.MOUSEBUTTONDOWN and ev.button == 1:
            slot = self._grid_slot_at(mouse)
            if slot:
                # ...existing grid double-click logic unchanged...
                c, r = slot
                idx = r*self.grid.cols + c
                now = time.time()
                if self._last_click_slot == idx and (now - self._last_click_time) <= self._double_click_interval:
                    self._try_use_slot_item(idx)
                    self._last_click_slot = None
                    self._last_click_time = 0.0
                    return
                self._last_click_slot = idx
                self._last_click_time = now
                self._begin_drag_from_grid(c, r, mouse)
                return
            e = self._equip_slot_at(mouse)
            if e:
                m_idx, slot_idx, erect = e
                self._begin_drag_from_equip(m_idx, slot_idx, erect, mouse)
                return
            # Click on doll header to select member (stat focus)
            for i, doll in enumerate(self.paper_rects):
                header_rect = pg.Rect(doll.x, doll.y - 24, doll.w, 24)
                if header_rect.collidepoint(mouse):
                    self.selected_member_index = i
                    return
        elif ev.type == pg.MOUSEBUTTONUP and ev.button == 1:
            self._drop_payload(mouse)
        elif ev.type == pg.KEYDOWN and ev.key == pg.K_ESCAPE:
            if self.drag.payload:
                self._cancel_drag()
                return
            self.open = False
        elif ev.type == pg.KEYDOWN and ev.key in (pg.K_TAB,):
            # Cycle selected member
            party = getattr(self.hero, "party", [self.hero])
            if party:
                self.selected_member_index = (self.selected_member_index + 1) % len(party)

    # ----- hover gather extended to all dolls -----
    def _gather_hover(self):
        if self.drag.payload: return
        mouse = pg.mouse.get_pos()
        gs = self._grid_slot_at(mouse)
        if gs:
            c, r = gs
            slot = self.grid.slots[r*self.grid.cols + c]
            if slot.id:
                self._hover_item_id = slot.id
                self._hover_rect = pg.Rect(self.grid_rect.x + c*CELL, self.grid_rect.y + r*CELL, CELL, CELL)
                return
        e = self._equip_slot_at(mouse)
        if e:
            m_idx, slot_idx, erect = e
            party = getattr(self.hero, "party", [self.hero])
            if m_idx < len(party):
                member = party[m_idx]
                item_id = member.equipment.get(EQUIP_SLOTS[slot_idx])
                if item_id:
                    self._hover_item_id = item_id
                    self._hover_rect = erect

    # ----- stat sheet shows selected member -----
    def _draw_stat_sheet(self, surf: pg.Surface):
        party = getattr(self.hero, "party", [self.hero])
        if not party: return
        if self.selected_member_index >= len(party):
            self.selected_member_index = 0
        h = party[self.selected_member_index]
        pg.draw.rect(surf, (28,28,38), self.stats_rect, border_radius=10)
        pg.draw.rect(surf, (64,64,80), self.stats_rect, 1, border_radius=10)
        x = self.stats_rect.x + 12
        y = self.stats_rect.y + 12
        draw_text(surf, f"Stats: {h.name}", x, y, GOLD); y += 26
        def ln(label, base, total):
            gear = total - base
            draw_text(surf, f"{label}: {total} ({base}{'+'+str(gear) if gear>0 else ''})", x, y, WHITE)
        ln("ATK", h.base_attack, h.attack()); y += 18
        ln("MAG", h.base_magic, h.magic()); y += 18
        ln("DEF", h.base_defense, h.defense()); y += 18
        ln("AGI", h.base_agility, h.agility()); y += 22
        res_labels = ["FIRE","ICE","ELECTRIC","POISON"]
        shown = False
        for rname in res_labels:
            val = h.resistance(rname)
            if val:
                if not shown:
                    draw_text(surf, "Resists:", x, y, SILVER); y += 18
                    shown = True
                draw_text(surf, f" {rname[:3]} {val:+d}%", x+4, y, WHITE); y += 18
        if not shown:
            draw_text(surf, "Resists: (none)", x, y, SILVER); y += 18
        y += 6
        draw_text(surf, f"Talent Pts: {h.talent_points}", x, y, GOLD)

    # ----- draw with multiple paper dolls -----
    def draw(self, surf: pg.Surface):
        self._gather_hover()
        draw_panel(surf, self.rect, "Inventory (Shared)")
        # Inventory grid
        for r in range(self.grid.rows):
            for c in range(self.grid.cols):
                cell = pg.Rect(self.grid_rect.x + c*CELL, self.grid_rect.y + r*CELL, CELL, CELL)
                pg.draw.rect(surf, BLACK, cell, border_radius=6)
                pg.draw.rect(surf, SILVER, cell, 1, border_radius=6)
                s = self.grid.slots[r*self.grid.cols + c]
                if s.id:
                    surf.blit(_icon(s.id), cell)
                    if s.count > 1:
                        draw_text(surf, str(s.count), cell.right - 18, cell.bottom - 20, WHITE)

        # Paper dolls for each party member
        party = getattr(self.hero, "party", [self.hero])
        for m_idx, (member, doll) in enumerate(zip(party, self.paper_rects)):
            draw_panel(surf, doll, None)
            # Header (click to select)
            name_col = GOLD if m_idx == self.selected_member_index else SILVER
            draw_text(surf, member.name, doll.x + 8, doll.y - 20, name_col, FONT_BIG)
            # Slots (2x2)
            for i, slot_name in enumerate(EQUIP_SLOTS):
                col = 0 if (i % 2) == 0 else 1
                row = 0 if i < 2 else 1
                slot_x = doll.x + 18 + col * (CELL + 32)
                slot_y = doll.y + 18 + row * (CELL + 46)
                rrect = pg.Rect(slot_x, slot_y, CELL, CELL)
                pg.draw.rect(surf, BLACK, rrect, border_radius=6)
                pg.draw.rect(surf, SILVER, rrect, 1, border_radius=6)
                item_id = member.equipment.get(slot_name)
                if item_id:
                    surf.blit(_icon(item_id), rrect)
                label = slot_name.capitalize()
                # NEW: show Offhand for thieves dual wield slot
                if member.hero_class == "THIEF" and slot_name == "shield":
                    label = "Offhand"
                lx = rrect.centerx - FONT.size(label)[0] // 2
                draw_text(surf, label, lx, rrect.bottom + 4, SILVER)

        # Stat sheet (selected member)
        self._draw_stat_sheet(surf)

        # Footer (shared inventory summary uses leader stats)
        pg.draw.line(surf, (70,70,88), (self.rect.x + 10, self.footer_y - 6),
                     (self.rect.right - 10, self.footer_y - 6), 1)
        lead = self.hero
        summary1 = f"Lv {lead.level()}  HP {lead.hp}/{lead.max_hp()}  MP {lead.mp}/{lead.max_mp()}"
        summary2 = f"ATK {lead.attack()}  MAG {lead.magic()}  DEF {lead.defense()}   Gil {lead.gil}"
        draw_text(surf, summary1, self.rect.x + 14, self.footer_y, WHITE)
        draw_text(surf, summary2, self.rect.x + 14, self.footer_y + 18, GOLD)

        # Drag payload
        self.drag.draw(surf, pg.mouse.get_pos())
        # Tooltip
        self._draw_tooltip(surf)
