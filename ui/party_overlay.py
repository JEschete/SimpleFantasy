import pygame as pg
from settings import draw_text, WHITE, SILVER, GOLD, RED, FONT, FONT_BIG, SCREEN_W, SCREEN_H

class PartyOverlay:
    def __init__(self, game):
        self.g = game
        w, h = 720, 420
        self.rect = pg.Rect((SCREEN_W - w)//2, (SCREEN_H - h)//2, w, h)
        self.cursor = 0
        self.renaming = False
        self.name_buffer = ""
        self.info_lines = []
    # --- syncing ---
    def sync_from_party(self):
        self.cursor = min(self.cursor, len(self.g.party)-1)
    # --- input (called from InputController via global key routing) ---
    def handle_event(self, ev: pg.event.Event):
        if ev.type == pg.KEYDOWN:
            k = ev.key
            if self.renaming:
                if k == pg.K_ESCAPE:
                    self.renaming = False; self.name_buffer = ""
                elif k == pg.K_RETURN:
                    nm = self.name_buffer.strip()
                    if nm:
                        self.g.party[self.cursor].name = nm[:16]
                    self.renaming = False; self.name_buffer = ""
                elif k == pg.K_BACKSPACE:
                    self.name_buffer = self.name_buffer[:-1]
                else:
                    ch = getattr(ev, "unicode", "")
                    if ch and ch.isprintable() and ch not in "\r\n\t" and len(self.name_buffer) < 16:
                        if ch.isalnum() or ch in " -_":
                            self.name_buffer += ch
                return
            # not renaming
            if k in (pg.K_ESCAPE, pg.K_m):
                self.g.party_open = False
                self.g.overworld.movement_locked = False
                return
            if k in (pg.K_UP, pg.K_w):
                self.cursor = (self.cursor - 1) % len(self.g.party)
            elif k in (pg.K_DOWN, pg.K_s):
                self.cursor = (self.cursor + 1) % len(self.g.party)
            elif k == pg.K_r:
                self.renaming = True
                self.name_buffer = self.g.party[self.cursor].name
            elif k == pg.K_u:
                if self.cursor > 1:  # do not move hero (index 0); allow moving others above index 1
                    p = self.g.party
                    p[self.cursor-1], p[self.cursor] = p[self.cursor], p[self.cursor-1]
                    self.cursor -= 1
            elif k == pg.K_d:
                if self.cursor > 0 and self.cursor < len(self.g.party)-1:
                    p = self.g.party
                    p[self.cursor+1], p[self.cursor] = p[self.cursor], p[self.cursor+1]
                    self.cursor += 1
            elif k == pg.K_x:
                if self.cursor > 0:
                    # dismiss member (no refund)
                    del self.g.party[self.cursor]
                    for m in self.g.party:
                        m.party = self.g.party
                    self.cursor = min(self.cursor, len(self.g.party)-1)
    # --- drawing ---
    def draw(self, surf: pg.Surface):
        pg.draw.rect(surf, (22,24,34), self.rect, border_radius=14)
        pg.draw.rect(surf, (80,82,110), self.rect, 2, border_radius=14)
        x = self.rect.x + 20
        y = self.rect.y + 18
        draw_text(surf, "Party Management", x, y, GOLD, FONT_BIG); y += 34
        draw_text(surf, f"Members: {len(self.g.party)}/4 (Hire at Tavern)", x, y, SILVER, FONT); y += 28
        if not self.g.party:
            draw_text(surf, "(No party)", x, y, SILVER, FONT); return
        for i, m in enumerate(self.g.party):
            sel = (i == self.cursor)
            col = GOLD if sel else WHITE
            tag = "(Lead)" if i == 0 else ""
            draw_text(surf, f"{'> ' if sel else '  '}{m.name:<16} Lv {m.level():<2} {m.hero_class:<11} HP {m.hp}/{m.max_hp()} MP {m.mp}/{m.max_mp()} {tag}",
                      x, y, col, FONT)
            y += 22
        y += 12
        if self.renaming:
            draw_text(surf, "Renaming: (ENTER confirm / ESC cancel)", x, y, SILVER, FONT); y += 22
            draw_text(surf, self.name_buffer + "_", x, y, GOLD, FONT_BIG); y += 30
        else:
            draw_text(surf, "Keys: UP/DOWN select  R rename  U/D move  X dismiss (not lead)  M/ESC close", x, y, SILVER, FONT)
