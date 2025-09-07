# main.py
import pygame, sys, time
from settings import *
from core.entities import Hero
from core.overworld import Overworld
from core.battle import Battle
from core.gamedata import save_game, load_game
from data.inventory import use_item, ITEMS, item_sell_price
from ui.shop import Shop
from ui.inventory_ui import InventoryUI
from world.ground import GroundManager
from ui.ui_overlays import CharacterSheet, JournalOverlay
from core.inputs import InputController
from ui.help_overlay import HelpOverlay
from ui.talent_overlay import TalentOverlay
from ui.tavern import Tavern
from ui.party_overlay import PartyOverlay
from ui.start_screen import StartScreen

class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Final Fantasy: Shapes & Spells")
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        self.clock = pygame.time.Clock()

        # Core entities/state
        self.hero = Hero()
        self.party = [self.hero]; self.hero.party = self.party
        self.overworld = Overworld(self.hero)
        self.battle: Battle | None = None

        # Start screen (refactored)
        self.start_screen = StartScreen(self)
        self.current_save_slot = 1
        self.base_hire_cost = 140

        # UI / overlays
        self.inv_ui = InventoryUI(self.hero, pos=(24, 24), cols=8, rows=4)
        self.inv_open = False
        self.shop = Shop()
        self.ground = GroundManager()
        self.char_sheet = CharacterSheet(self.hero); self.char_open = False
        self.journal = JournalOverlay(self.hero); self.journal_open = False
        self.help = HelpOverlay(); self.help_open = False
        self.talent = TalentOverlay(self.hero); self.talent_open = False
        self.tavern = Tavern(self); self.tavern_open = False
        self.party_ui = PartyOverlay(self); self.party_open = False

        self.auto_loot = False
        self.exit_confirm_until = 0.0
        self.hud_rect = pygame.Rect(12, 6, 480, 54)

        # overworld KO flag (outside battle)
        self.hero_dead = False

        # Wire shop / inventory
        self.shop.connect(
            get_gold=lambda: self.hero.gil,
            add_gold=lambda n: setattr(self.hero, "gil", max(0, self.hero.gil + n)),
            try_add_to_inventory=self._try_add_to_inventory
        )
        self.inv_ui.is_over_shop = lambda pos: self.shop.is_over(pos) and self.shop.opened
        self.inv_ui.on_sell = self._try_sell_stack
        self.inv_ui.on_drop_to_ground = self._drop_to_ground

        self.input = InputController(self)

    # ---------- Utility ----------
    @property
    def state(self):
        if self.start_screen.active: return "START"
        return "BATTLE" if self.battle else "OVERWORLD"

    def get_next_hire_cost(self):
        return int(self.base_hire_cost * (1 + 0.35 * (len(self.party)-1)))

    def _try_add_to_inventory(self, item_id: str, qty: int) -> bool:
        ok = self.inv_ui.grid.add_stack(item_id, qty)
        if ok: self.inv_ui.commit_to_hero()
        return ok

    def _try_sell_stack(self, item_id: str, qty: int):
        self.hero.gil += item_sell_price(item_id) * qty

    def _drop_to_ground(self, item_id: str, qty: int):
        drop_pos = (int(self.hero.x), int(self.hero.y + self.hero.w//2 + 28))
        self.ground.drop(drop_pos, item_id, qty, ttl=60.0)

    def _pickup_ground_at(self, pos):
        got = self.ground.pick_at(pos)
        if not got: return
        item_id, qty = got
        if not self._try_add_to_inventory(item_id, qty):
            self.ground.drop(pos, item_id, qty, ttl=45.0)
            if hasattr(self.overworld, "set_toast"): self.overworld.set_toast("Inventory full!")
        else:
            if hasattr(self.overworld, "set_toast"):
                self.overworld.set_toast(f"Picked {ITEMS[item_id].name} x{qty}")

    def _pickup_nearest_ground(self, radius=96):
        if not self.ground.items: return
        hx, hy = self.hero.x, self.hero.y
        nearest = None; best = radius*radius
        for g in self.ground.items:
            d2 = (g.pos.x-hx)**2 + (g.pos.y-hy)**2
            if d2 <= best:
                best = d2; nearest = g
        if nearest:
            self._pickup_ground_at((int(nearest.pos.x), int(nearest.pos.y)))

    # ---------- Start / New / Load ----------
    def start_new_game(self, cls: str, name: str, slot: int | None = None):
        self.hero = Hero(hero_class=cls, name=name or "Hero")
        def _equip(slot, iid):
            if iid in ITEMS:
                self.hero.inventory.add(iid, 1)
                self.hero.equipment[slot] = iid
        if cls == "FIGHTER":
            _equip("weapon", "WOOD_SWORD"); _equip("armor", "LEATHER_ARM")
        elif cls == "THIEF":
            _equip("weapon", "WOOD_SWORD")
        elif cls == "BLACK_MAGE":
            _equip("armor", "MAGE_ROBE")
        elif cls == "WHITE_MAGE":
            _equip("armor", "MAGE_ROBE")
        self.party = [self.hero]; self.hero.party = self.party
        self.overworld.hero = self.hero
        self.inv_ui.hero = self.hero
        self.char_sheet.hero = self.hero
        self.journal.hero = self.hero
        if slot is not None:
            self.current_save_slot = slot
        # Auto-save immediately
        save_game(self.hero, self.current_save_slot)
        if hasattr(self.overworld, "set_toast"):
            self.overworld.set_toast(f"New journey saved (Slot {self.current_save_slot}).")

    def load_save_slot(self, slot: int):
        msg = load_game(self.hero, slot)
        self.current_save_slot = slot
        self.party = getattr(self.hero, "party", [self.hero])
        self.hero.party = self.party
        self.overworld.hero = self.hero
        self.inv_ui.hero = self.hero
        self.char_sheet.hero = self.hero
        self.journal.hero = self.hero
        # --- refresh UIs so class / party layout reflect loaded data ---
        self.inv_ui.refresh_party_layout()
        self.party_ui.sync_from_party()
        if hasattr(self.overworld, "set_toast"): self.overworld.set_toast(msg)
        self.start_screen.deactivate()

    # ---------- Game Loop ----------
    def run(self):
        last = time.time()
        while True:
            now = time.time(); dt = now - last; last = now
            self.input.process_events()
            self.update(dt)
            self.draw()
            self.clock.tick(60)

    def update(self, dt):
        if self.state == "START":
            ng = self.start_screen.consume_new_game_request()
            if ng is not None:  # CHANGED
                cls, name, slot = ng
                if slot is None:
                    slot = self.current_save_slot
                self.start_new_game(cls, name, slot)
                self.start_screen.deactivate()
                return
            slot = self.start_screen.consume_load_request()
            if slot is not None:
                self.load_save_slot(slot)
            return

        keys = pygame.key.get_pressed()
        if self.battle:
            self.battle.update(dt)
        else:
            if not self.shop.opened:
                self.overworld.update(dt, keys)
                if (keys[pygame.K_RETURN] or keys[pygame.K_KP_ENTER]) and self.overworld.near_shop():
                    if not self.shop.opened:
                        self.inv_open = True
                        self.inv_ui.reload_from_hero()
                        self.shop.open()
                else:
                    enc = self.overworld.maybe_encounter()
                    if enc:
                        self.battle = enc
                        self.battle.log.append("An encounter appears!")
                        win_beep(800, 120)
        self.ground.update()
        if (not self.battle) and self.auto_loot and not self.shop.opened and not self.inv_open:
            for g in self.ground.items[:]:
                if (g.pos.x-self.hero.x)**2 + (g.pos.y-self.hero.y)**2 <= 110*110:
                    self._pickup_ground_at((int(g.pos.x), int(g.pos.y)))

        # --- update death state outside battle ---
        if not self.battle and self.state == "OVERWORLD":
            self.hero_dead = (self.hero.hp <= 0)
        else:
            self.hero_dead = False

    def draw(self):
        if self.state == "START":
            self.start_screen.draw(self.screen)
            pygame.display.flip()
            return
        if not self.battle:
            self.overworld.draw(self.screen)
            self.ground.draw(self.screen)
            if self.inv_open: self.inv_ui.draw(self.screen)
            if self.shop.opened: self.shop.draw(self.screen)
            if self.char_open: self.char_sheet.draw(self.screen)
            if self.journal_open: self.journal.draw(self.screen)
            if self.help_open: self.help.draw(self.screen)
            if self.talent_open: self.talent.draw(self.screen)
            if self.tavern_open: self.tavern.draw(self.screen)
            if self.party_open: self.party_ui.draw(self.screen)
            self._draw_overworld_stats_hud()
            # death overlay (draw after HUD so it sits on top)
            if self.hero_dead:
                self._draw_death_overlay()
        else:
            self.battle.draw(self.screen)
        pygame.display.flip()

    def _draw_overworld_stats_hud(self):
        if self.inv_open or self.char_open or self.journal_open or self.shop.opened: return
        h = self.hero; r = self.hud_rect
        # build first line with hero name
        line1 = f"{h.name} Lv {h.level()}  HP {h.hp}/{h.max_hp()}  MP {h.mp}/{h.max_mp()}"
        needed_w = FONT_BIG.size(line1)[0] + 32
        if needed_w > r.w:
            r.w = min(needed_w, SCREEN_W - 24)   # expand if necessary
        pygame.draw.rect(self.screen, (24,24,30), r, border_radius=10)
        pygame.draw.rect(self.screen, (60,60,80), r, 2, border_radius=10)
        draw_text(self.screen, line1, r.x + 10, r.y + 8, WHITE, FONT_BIG)
        draw_text(self.screen,
                  f"ATK {h.attack()}  MAG {h.magic()}  DEF {h.defense()}   Gil {h.gil}   [H] Help",
                  r.x + 10, r.y + 30, GOLD, FONT)

    def _draw_death_overlay(self):
        """Simple fail state outside battle; lets player revive via potion or reload."""
        surf = self.screen
        w, h = 520, 200
        rect = pygame.Rect((SCREEN_W - w)//2, (SCREEN_H - h)//2, w, h)
        overlay = pygame.Surface((w, h), pygame.SRCALPHA)
        overlay.fill((10, 0, 0, 180))
        surf.blit(overlay, rect)
        pygame.draw.rect(surf, (120, 30, 30), rect, 3, border_radius=14)
        draw_text(surf, "You have fallen...", rect.x + 24, rect.y + 26, GOLD, FONT_BIG)
        draw_text(surf, "R: Reload Save   N: New Game", rect.x + 24, rect.y + 70, WHITE, FONT_BIG)
        draw_text(surf, "Use a Potion (hotkey 1) to revive if available.", rect.x + 24, rect.y + 106, SILVER, FONT)
        draw_text(surf, "ESC: Quit Prompt (double press still works)", rect.x + 24, rect.y + 134, SILVER, FONT)

    # ---------- Input helpers (overworld hotkeys) ----------
    def handle_overworld_input(self, key):
        if key == pygame.K_F5:
            msg = save_game(self.hero, self.current_save_slot)
            self.overworld.set_toast(msg); win_beep(900, 90)
        elif key == pygame.K_F9:
            msg = load_game(self.hero, self.current_save_slot)
            self.overworld.set_toast(msg); win_beep(700, 90)
        elif key == pygame.K_p:
            msg = use_item(self.hero, "POTION"); self.overworld.set_toast(msg)
            if "Used" in msg: win_beep(1000, 90)
        elif key == pygame.K_e:
            msg = use_item(self.hero, "ETHER"); self.overworld.set_toast(msg)
            if "Used" in msg: win_beep(980, 90)

    # ---------- Misc ----------
    def restart_new_game(self):
        self.hero = Hero()
        self.party = [self.hero]; self.hero.party = self.party
        self.overworld.hero = self.hero
        self.inv_ui.hero = self.hero
        self.char_sheet.hero = self.hero
        self.journal.hero = self.hero
        self.battle = None
        if hasattr(self.overworld, "set_toast"):
            self.overworld.set_toast("Run restarted.")

    def handle_talent_key(self, key):
        if self.talent_open: self.talent.handle_key(key)

    def hire_companion(self, cls: str, cost: int):
        if len(self.party) >= 4: return "Party full."
        if self.hero.gil < cost: return "Not enough Gil."
        self.hero.gil -= cost
        comp = Hero(hero_class=cls.upper(), name=cls.title())
        if hasattr(comp, "prune_illegal_spells"): comp.prune_illegal_spells()
        comp.party = self.party
        self.party.append(comp)
        if hasattr(self.overworld, "set_toast"):
            self.overworld.set_toast(f"{comp.name} hired!")
        return "Hired."

    def unify_party_inventory(self):
        """
        Merge every companion's inventory into the leader's (shared) inventory.
        After this the companions' individual inventories are cleared (classic shared pool).
        """
        if not getattr(self.hero, "party", None): return
        leader_inv = self.hero.inventory
        for mem in self.hero.party[1:]:
            for iid, qty in list(mem.inventory.counts.items()):
                if qty > 0:
                    leader_inv.add(iid, qty)
            mem.inventory.counts.clear()

if __name__ == "__main__":
    try:
        Game().run()
    except Exception:
        pygame.quit()
        raise