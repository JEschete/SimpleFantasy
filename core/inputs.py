import pygame, sys, time
from data.inventory import use_item
from core.gamedata import load_game

class InputController:
    def __init__(self, game):
        self.g = game  # reference to Game

    # ---- public entry ----
    def process_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit(0)
            if event.type == pygame.KEYDOWN:
                if self.g.state == "START":
                    self.g.start_screen.handle_key(event.key, getattr(event, "unicode", ""), event.mod)  # CHANGED
                    continue
                # Party overlay intercept (rename etc.)
                if getattr(self.g, "party_open", False):
                    self.g.party_ui.handle_event(event)
                    continue
                self._handle_keydown(event.key)

            if getattr(self.g, "tavern_open", False):
                if event.type == pygame.KEYDOWN:
                    self.g.tavern.handle_key(event.key)

            # Block other UI interactions while party overlay open
            if getattr(self.g, "party_open", False):
                continue

            # UI mouse routing (shop > inventory > world)
            if self.g.shop.opened:
                self.g.shop.handle_event(event)
                self.g.inv_ui.handle_event(event)
            elif self.g.inv_open:
                self.g.inv_ui.handle_event(event)
            else:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button in (1, 3):
                    self.g._pickup_ground_at(pygame.mouse.get_pos())
                if event.type == pygame.KEYDOWN and event.key == pygame.K_g:
                    self.g._pickup_nearest_ground()

    # ---- key handling ----
    def _handle_keydown(self, key):
        g = self.g
        if g.state == "START":
            # When reached (rare), send without unicode
            g.start_screen.handle_key(key, "")  # CHANGED
            return
        if key != pygame.K_ESCAPE and g.exit_confirm_until > 0:
            g.exit_confirm_until = 0.0

        if key == pygame.K_ESCAPE:
            self._handle_escape()
            return

        if g.state == "BATTLE":
            self._battle_key(key)
        elif g.state == "OVERWORLD":
            self._overworld_key(key)

    def _handle_escape(self):
        g = self.g
        if g.state == "START":
            g.start_screen.handle_key(pygame.K_ESCAPE, "")  # CHANGED
            return
        # START screen: ESC on main menu quits, elsewhere returns to main
        if g.state == "START":
            if g.start_menu_mode in ("NEW","LOAD"):
                g.start_menu_mode = "MAIN"
                return
        if getattr(g, "party_open", False):
            g.party_open = False; g.overworld.movement_locked = False; return
        if getattr(g, "tavern_open", False):
            g.tavern_open = False; g.overworld.movement_locked = False; g.exit_confirm_until = 0.0; return
        if getattr(g, "talent_open", False):
            g.talent_open = False; g.overworld.movement_locked = False; g.exit_confirm_until = 0.0; return
        if g.help_open:
            g.help_open = False; g.exit_confirm_until = 0.0; return
        if g.shop.opened:
            g.shop.close(); g.exit_confirm_until = 0.0; return
        if g.inv_open:
            g.inv_open = False; g.exit_confirm_until = 0.0; return
        if g.char_open:
            g.char_open = False; g.exit_confirm_until = 0.0; return
        if g.journal_open:
            g.journal_open = False; g.exit_confirm_until = 0.0; return
        now = time.time()
        if now < g.exit_confirm_until:
            pygame.quit(); sys.exit(0)
        g.exit_confirm_until = now + 3.0
        if hasattr(g.overworld, "set_toast"):
            g.overworld.set_toast("Press ESC again to quit.")

    # ---- overworld keys ----
    def _overworld_key(self, key):
        g = self.g

        # --- NEW: death state handling ---
        if getattr(g, "hero_dead", False):
            # Limited keys while dead
            if key == pygame.K_r:
                msg = load_game(g.hero, g.current_save_slot)
                if hasattr(g.overworld, "set_toast"): g.overworld.set_toast(msg)
                g.hero_dead = (g.hero.hp <= 0)
                return
            if key == pygame.K_n:
                g.restart_new_game()
                if hasattr(g.overworld, "set_toast"): g.overworld.set_toast("New run started.")
                g.hero_dead = False
                return
            if key == pygame.K_1:
                if g.hero.inventory.qty("POTION") > 0:
                    msg = use_item(g.hero, "POTION")  # removed inner import
                    if hasattr(g.overworld, "set_toast"): g.overworld.set_toast(msg)
                    if g.hero.hp > 0: g.hero_dead = False
                return
            # Ignore all other keys except ESC (handled elsewhere)
            return

        if getattr(g, "talent_open", False) and key not in (pygame.K_t, pygame.K_ESCAPE):
            g.handle_talent_key(key)
            return

        if key == pygame.K_i:
            # Force merge inventories before opening shared pool UI.
            if g.shop.opened: g.shop.close()
            # NEW: unify party inventory into leader before showing UI
            g.unify_party_inventory()
            g.inv_open = not g.inv_open
            if g.inv_open:
                g.inv_ui.reload_from_hero()
                g.inv_ui.refresh_party_layout()   # NEW: ensure paper dolls reflect party
            return
        if key == pygame.K_c:
            if g.shop.opened: g.shop.close()
            g.char_open = not g.char_open
            if g.char_open: g.inv_open = False
            return
        if key == pygame.K_j:
            if g.shop.opened: g.shop.close()
            g.journal_open = not g.journal_open
            return
        if key == pygame.K_l:
            g.auto_loot = not g.auto_loot
            if hasattr(g.overworld, "set_toast"):
                g.overworld.set_toast(f"Auto-Loot {'ON' if g.auto_loot else 'OFF'}")
            return
        if key == pygame.K_1:
            if g.hero.inventory.qty("POTION") > 0:
                msg = use_item(g.hero, "POTION")  # removed inner import
                g.overworld.set_toast(msg)
            return
        if key == pygame.K_2:
            if g.hero.inventory.qty("ETHER") > 0:
                msg = use_item(g.hero, "ETHER")  # removed inner import
                g.overworld.set_toast(msg)
            return
        if key == pygame.K_h:
            # toggle help (exclusive)
            if g.help_open:
                g.help_open = False
            else:
                g.help_open = True
                g.inv_open = False
                g.char_open = False
                g.journal_open = False
                if g.shop.opened: g.shop.close()
            return
        if key == pygame.K_t:
            if getattr(g, "talent_open", False):
                g.talent_open = False
                g.overworld.movement_locked = False  # NEW
            else:
                g.talent_open = True
                g.overworld.movement_locked = True   # NEW
                g.help_open = False
                g.inv_open = False
                g.char_open = False
                g.journal_open = False
                if g.shop.opened: g.shop.close()
            return
        if key == pygame.K_y:
            if g.overworld.near_tavern():
                g.tavern_open = not getattr(g, "tavern_open", False)
                g.overworld.movement_locked = g.tavern_open
            return
        if key == pygame.K_m:
            # Toggle party management
            g.party_open = not getattr(g, "party_open", False)
            if g.party_open:
                g.overworld.movement_locked = True
                g.help_open = g.inv_open = g.char_open = g.journal_open = g.talent_open = False
                if g.shop.opened: g.shop.close()
                g.tavern_open = False
                g.party_ui.sync_from_party()
            else:
                g.overworld.movement_locked = False
            return
        # delegate remaining (F5/F9/P/E) to saved method
        g.handle_overworld_input(key)

    # ---- battle keys ----
    def _battle_key(self, key):
        b = self.g.battle
        if not b: return
        alive = b.alive_enemies()
        # Treat defeat as all party dead
        party_alive = any(p.is_alive() for p in [self.g.hero] + b.companions)

        if not party_alive:
            if key == pygame.K_r:
                msg = load_game(self.g.hero)
                if hasattr(self.g.overworld, "set_toast"): self.g.overworld.set_toast(msg)
                self.g.battle = None
            elif key == pygame.K_n:
                self.g.restart_new_game()
                if hasattr(self.g.overworld, "set_toast"): self.g.overworld.set_toast("New run started.")
                self.g.battle = None
            return

        if (not alive) or b.ran_away:
            if key == pygame.K_RETURN:
                if (not b.ran_away) and not b.victory_loot_done:
                    # XP share: all living party members
                    xp_gain = b.total_xp_yield
                    if xp_gain > 0:
                        living = [m for m in [self.g.hero] + b.companions if m.is_alive()]
                        share = max(1, xp_gain // max(1, len(living)))
                        for m in living:
                            msgs = m.add_xp(share)
                            if m is self.g.hero:
                                b.log.append(f"{m.name} +{share} XP")
                                b.log.extend(msgs)
                            else:
                                b.log.append(f"{m.name} +{share} XP")
                        q_msgs = self.g.hero.quest.turn_in_completed(self.g.hero)
                        for m in q_msgs: b.log.append(m)
                self.g.battle = None
            return

        # Ongoing
        b.handle_input(key)
