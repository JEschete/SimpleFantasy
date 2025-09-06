import pygame
from settings import draw_text, GOLD, WHITE, SILVER, CYAN, FONT, FONT_BIG
from core.gamedata import list_saves

class StartScreen:
    def __init__(self, game):
        self.g = game
        self.active = True
        self.mode = "MAIN"          # MAIN / NEW_CLASS / NEW_NAME / LOAD
        self.main_index = 0
        self.classes = ["FIGHTER","THIEF","BLACK_MAGE","WHITE_MAGE"]
        self.class_index = 0
        self.pending_class = None
        self.name_buffer = ""
        self.load_index = 0
        self.saves = list_saves()
        self.cached_saves = self.saves  # NEW alias to satisfy legacy references
        self._req_new_game: 'None | tuple[str,str,int|None]' = None  # CHANGED: always triple
        self._req_load_slot = None
        self.slot_index = 0          # NEW: slot picker index

    # ----- requests -----
    def consume_new_game_request(self) -> 'None | tuple[str,str,int|None]':  # CHANGED annotation
        r = self._req_new_game
        self._req_new_game = None
        return r
    def consume_load_request(self):
        r = self._req_load_slot
        self._req_load_slot = None
        return r
    def deactivate(self): self.active = False

    # ----- input -----
    def handle_key(self, key, ch: str = "", mods: int = 0):
        """key = event.key, ch = event.unicode (may be ''), mods = event.mod"""
        if not self.active: return
        if self.mode == "MAIN":
            if key in (pygame.K_UP, pygame.K_w): self.main_index = (self.main_index - 1) % 3
            elif key in (pygame.K_DOWN, pygame.K_s): self.main_index = (self.main_index + 1) % 3
            elif key in (pygame.K_RETURN, pygame.K_SPACE):
                if self.main_index == 0:
                    self.mode = "NEW_CLASS"
                elif self.main_index == 1:
                    self.saves = list_saves()
                    self.mode = "LOAD"
                else:
                    pygame.quit(); raise SystemExit
        elif self.mode == "NEW_CLASS":
            if key == pygame.K_ESCAPE:
                self.mode = "MAIN"
            elif key in (pygame.K_UP, pygame.K_w):
                self.class_index = (self.class_index - 1) % len(self.classes)
            elif key in (pygame.K_DOWN, pygame.K_s):
                self.class_index = (self.class_index + 1) % len(self.classes)
            elif key in (pygame.K_RETURN, pygame.K_SPACE):
                self.pending_class = self.classes[self.class_index]
                self.name_buffer = "Hero"
                self.mode = "NEW_NAME"
        elif self.mode == "NEW_NAME":
            if key == pygame.K_ESCAPE:
                self.mode = "NEW_CLASS"
            elif key == pygame.K_BACKSPACE:
                self.name_buffer = self.name_buffer[:-1]
            elif key == pygame.K_RETURN:
                # Move to slot selection instead of starting immediately
                self.mode = "NEW_SLOT"
                self.saves = list_saves()
                self.slot_index = 0
            else:
                # NEW: use unicode so Shift produces capitals; restrict to printable
                if ch and ch.isprintable() and ch not in "\r\n\t" and len(self.name_buffer) < 14:
                    # Optional: limit charset (letters, digits, space, - _)
                    if ch.isalnum() or ch in " -_":
                        self.name_buffer += ch
        elif self.mode == "NEW_SLOT":
            if key == pygame.K_ESCAPE:
                self.mode = "NEW_NAME"
            elif key in (pygame.K_UP, pygame.K_w):
                self.slot_index = (self.slot_index - 1) % len(self.saves)
            elif key in (pygame.K_DOWN, pygame.K_s):
                self.slot_index = (self.slot_index + 1) % len(self.saves)
            elif key in (pygame.K_RETURN, pygame.K_SPACE):
                cls = self.pending_class or self.classes[self.class_index]
                name = (self.name_buffer.strip() or "Hero")[:14]
                slot = self.saves[self.slot_index][0]
                self._req_new_game = (cls, name, slot)  # always triple
        elif self.mode == "LOAD":
            if key == pygame.K_ESCAPE:
                self.mode = "MAIN"
            elif key in (pygame.K_UP, pygame.K_w):
                self.load_index = (self.load_index - 1) % 3
            elif key in (pygame.K_DOWN, pygame.K_s):
                self.load_index = (self.load_index + 1) % 3
            elif key == pygame.K_RETURN:
                slot = self.saves[self.load_index][0]
                self._req_load_slot = slot

    # ----- drawing -----
    def draw(self, surf):
        surf.fill((14,16,24))
        draw_text(surf, "FINAL FANTASY: SHAPES & SPELLS", 480, 140, GOLD, FONT_BIG)
        if self.mode == "MAIN":
            opts = ["New Game","Load Game","Quit"]
            for i,opt in enumerate(opts):
                col = GOLD if i == self.main_index else WHITE
                draw_text(surf, f"{'> ' if i==self.main_index else '  '}{opt}", 520, 260 + i*42, col, FONT_BIG)
            draw_text(surf, "UP/DOWN select  ENTER confirm", 520, 260 + 42*3 + 20, SILVER, FONT)
        elif self.mode == "NEW_CLASS":
            draw_text(surf, "Choose Class (ENTER select):", 480, 230, SILVER, FONT_BIG)
            for i, cls in enumerate(self.classes):
                col = GOLD if i == self.class_index else WHITE
                draw_text(surf, f"{'> ' if i==self.class_index else '  '}{cls}", 500, 270 + i*28, col, FONT)
            draw_text(surf, "ESC back", 500, 270 + len(self.classes)*28 + 36, SILVER, FONT)
        elif self.mode == "NEW_NAME":
            draw_text(surf, f"Class: {self.pending_class}", 500, 250, SILVER, FONT_BIG)
            draw_text(surf, f"Enter Name:", 500, 300, SILVER, FONT)
            draw_text(surf, self.name_buffer + "_", 500, 330, CYAN, FONT_BIG)
            draw_text(surf, "ENTER choose save slot  BACKSPACE delete  ESC back", 500, 380, SILVER, FONT)
        elif self.mode == "NEW_SLOT":
            draw_text(surf, f"New Game: {self.pending_class} / {self.name_buffer}", 440, 210, GOLD, FONT_BIG)
            draw_text(surf, "Select Save Slot (ENTER confirm / ESC back)", 440, 244, SILVER, FONT)
            self.saves = list_saves()
            for i,(slot,present,meta) in enumerate(self.saves):
                y = 290 + i*70
                rect = pygame.Rect(420, y-18, 640, 60)
                pygame.draw.rect(surf, (30,34,48), rect, border_radius=10)
                pygame.draw.rect(surf, GOLD if i==self.slot_index else (70,70,90), rect, 2, border_radius=10)
                if present and meta:
                    draw_text(surf,
                              f"Slot {slot}: {meta['name']}  Lv {meta['level']}  {meta['class']} (Overwrite)",
                              rect.x + 20, y, WHITE, FONT_BIG)
                else:
                    draw_text(surf, f"Slot {slot}: (Empty)", rect.x + 20, y, SILVER, FONT_BIG)
        elif self.mode == "LOAD":
            draw_text(surf, "Load Game (ENTER load, ESC back)", 440, 220, SILVER, FONT_BIG)
            self.saves = list_saves()
            for i,(slot,present,meta) in enumerate(self.saves):
                y = 270 + i*74
                rect = pygame.Rect(420, y-14, 640, 60)
                pygame.draw.rect(surf, (30,34,48), rect, border_radius=10)
                pygame.draw.rect(surf, GOLD if i==self.load_index else (70,70,90), rect, 2, border_radius=10)
                if present and meta:
                    draw_text(surf,
                              f"Slot {slot}: {meta['name']}  Lv {meta['level']}  {meta['class']}",
                              rect.x + 20, y, WHITE, FONT_BIG)
                else:
                    draw_text(surf, f"Slot {slot}: (Empty)", rect.x + 20, y, SILVER, FONT_BIG)
