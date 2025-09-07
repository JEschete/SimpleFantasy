import pygame
import random
from typing import Optional  # NEW
from settings import *
from core.entities import Enemy
from ui.menu import Menu
from data.spells import get_spell
from data.inventory import use_item, ITEMS
from settings import type_multiplier
from core.loot import LOOT_TABLES, EQUIP_DROPS

def damage_from_attack(attacker_atk, defender_def):
    return max(1, attacker_atk + random.randint(4, 10) - defender_def)

class Battle:
    def __init__(self, hero, encounter_level):
        # Encounter composition tuned by hero level & party maturity.
        self.hero = hero
        self.turn = "PLAYER"
        self.log = []
        self.compact_log = False

        # --- NEW Encounter scaling / gating ---
        hero_lv = hero.level()
        party_high_lvl = sum(1 for m in getattr(hero, "party", [hero]) if m.level() > 2)
        allow_golem = (hero_lv >= 4) or (party_high_lvl > 2)
        allow_dragon = (hero_lv >= 10)

        # Max group size by hero level
        if hero_lv < 3:
            max_group = 2
        elif hero_lv < 5:
            max_group = 3
        elif hero_lv < 10:
            max_group = 4
        else:
            max_group = 5

        # Early game (tutorial feel): only level‑1 goblins
        enemies = []
        if hero_lv < 3:
            count = 1 if random.random() < 0.55 else 2
            for _ in range(count):
                enemies.append(Enemy("GOBLIN", level=1))
        else:
            # Build weighted species pool
            weights = []
            def add(spec, w):
                weights.append((spec, w))
            add("GOBLIN", 6)
            add("WOLF", 5)
            add("SLIME", 5)
            add("BAT", 4)
            if allow_golem:
                add("GOLEM", 2)
            if allow_dragon:
                add("DRAGON", 1)  # very rare
            # Normalize pick function
            total_w = sum(w for _, w in weights)
            def pick_species():
                r = random.random() * total_w
                acc = 0
                for sp, w in weights:
                    acc += w
                    if r <= acc:
                        return sp
                return weights[-1][0]

            # Group size distribution (bias smaller groups slightly)
            possible_sizes = list(range(1, max_group + 1))
            size_weights = [max(1, (max_group + 1 - s)) for s in possible_sizes]
            sw_total = sum(size_weights)
            r = random.random() * sw_total
            acc = 0
            group_size = 1
            for s, w in zip(possible_sizes, size_weights):
                acc += w
                if r <= acc:
                    group_size = s
                    break

            for _ in range(group_size):
                sp = pick_species()
                # Level variance (post early game). Avoid > hero_lv+2 for pacing.
                var = random.choice([-1, 0, 0, 1])
                lvl = clamp(hero_lv + var, 1, hero_lv + 2)
                # Slight downscale for GOLEM/DRAGON appearing early in their unlock range
                if sp == "GOLEM" and lvl < hero_lv:
                    lvl = hero_lv  # keep tough
                if sp == "DRAGON":
                    lvl = max(10, lvl + 1)  # ensure intimidating baseline
                enemies.append(Enemy(sp, lvl))

        self.enemies = enemies
        self.total_xp_yield = sum(e.xp_yield for e in self.enemies)
        self.cursor = 0
        self.shake_time = 0.0

        # PARTY: hero + companions (up to 3)
        self.companions = [m for m in getattr(hero, "party", [hero]) if m is not hero][:3]
        self.party = [self.hero] + self.companions
        self.active_index = 0  # whose turn within party round

        # Menus/state
        self.mode = "ROOT"  # ROOT / MAGIC / ITEMS
        self.menu_root: Optional[Menu] = None        # CHANGED (allow None)
        self.menu_magic: Optional[Menu] = None       # CHANGED
        self.menu_items: Optional[Menu] = None       # CHANGED
        self._rebuild_root_menu()

        self.victory_loot_done = False
        self.ran_away = False        # NEW: true if player fled
        # --- NEW: step animation state ---
        self.player_step_offset = 0.0
        self.player_step_target = 48.0   # how far hero steps forward
        self.player_step_speed = 240.0   # px/sec for in/out

    # ----- properties -----
    @property
    def active_actor(self):
        # Skip dead actors if any linger
        if self.active_index >= len(self.party):
            self.active_index = 0
        # ensure current points to a living member
        loops = 0
        while loops < len(self.party) and not self.party[self.active_index].is_alive():
            self.active_index = (self.active_index + 1) % len(self.party)
            loops += 1
        return self.party[self.active_index]

    def _rebuild_root_menu(self):
        # Menu rebuilt per active actor; hides unusable branches.
        a = self.active_actor
        items = ["Attack"]
        # Steal only if Thief (already enforced) — unchanged.
        if a.hero_class == "THIEF":
            items.append("Steal")
        # Magic only if actor has at least one castable spell (can_cast filter)
        castables = [sid for sid in a.known_spells if a.can_cast(sid)]
        if castables:
            items.append("Magic")
        items += ["Items", "Defend"]
        if a is self.hero:
            items.append("Run")
        self.menu_root = Menu(SCREEN_W // 2 + 50, 160, 360, items, title=None)

    # ---------- helpers ----------
    def alive_enemies(self):
        return [e for e in self.enemies if e.is_alive()]

    def target(self):
        alive = self.alive_enemies()
        if not alive:
            return None
        self.cursor %= len(alive)
        return alive[self.cursor]

    def _ensure_magic_menu(self) -> Menu:
        if self.menu_magic is None:
            a = self.active_actor
            legal = [sid for sid in a.known_spells if a.can_cast(sid)]
            items = []
            for sid in legal:
                sp = get_spell(sid)
                items.append(f"{sp['name']} ({sp['mp']})")
            if not items:
                items = ["(no spells)"]
            self.menu_magic = Menu(SCREEN_W // 2 + 50, 220, 360, items, title="Magic")
            self._magic_index_map = legal  # map displayed index -> spell id
        # Type narrowing for Pylance
        assert self.menu_magic is not None
        return self.menu_magic

    def _ensure_items_menu(self) -> Menu:
        if self.menu_items is None:
            # Shared party inventory (hero’s)
            entries = [f"{ITEMS[i].name} x{q}" for i, q in self.hero.inventory.all_items()]
            if not entries:
                entries = ["(empty)"]
            self.menu_items = Menu(SCREEN_W // 2 + 50, 220, 360, entries, title="Items")
        # Type narrowing for Pylance
        assert self.menu_items is not None
        return self.menu_items

    # --- party flow helpers ---
    def _advance_turn(self):
        # Rotates through living party; wraps to enemy phase when hero cycles.
        # If enemies all dead -> end
        if not self.alive_enemies():
            self.turn = "ENEMY"  # triggers end sequence path
            return
        # Move to next living party member
        start = self.active_index
        while True:
            self.active_index = (self.active_index + 1) % len(self.party)
            if self.party[self.active_index].is_alive():
                break
            if self.active_index == start:
                break
        # If wrapped to hero again -> enemies phase
        if self.active_index == 0:
            self.turn = "ENEMY"
        else:
            self.turn = "PLAYER"
            self.mode = "ROOT"
            self.menu_magic = None
            self.menu_items = None
            self._rebuild_root_menu()

    def _party_alive(self):
        return [m for m in self.party if m.is_alive()]

    def _turn_order_preview(self):
        actors = []
        for h in self._party_alive():
            actors.append(("P", h.name, h.agility()))
        for e in self.alive_enemies():
            actors.append(("E", e.species, e.agility))
        actors.sort(key=lambda x: x[2], reverse=True)
        return actors[:8]

    # ---------- actions ----------
    def player_attack(self):
        a = self.active_actor
        t = self.target()
        if not t:
            self.log.append("No target.")
            return
        dmg = damage_from_attack(a.attack(), 4 + t.level)
        t.hp = clamp(t.hp - dmg, 0, t.max_hp)
        if t.hp == 0:
            self.hero.quest.record_kill(t.species)
        self.log.append(f"{a.name} strikes {t.species} for {dmg}.")
        win_beep(700, 70)
        self.shake_time = 0.15
        self._advance_turn()

    def player_defend(self):
        a = self.active_actor
        a.defending = True
        self.log.append(f"{a.name} braces (DEFEND).")
        self._advance_turn()

    def player_run(self):
        # only hero can attempt run
        if self.active_actor is not self.hero:
            self.log.append("Only leader can Run.")
            return
        avg = max(1, sum(e.level for e in self.enemies) // len(self.enemies))
        chance = clamp(0.5 + 0.05 * (self.hero.level() - avg), 0.1, 0.95)
        if random.random() < chance:
            self.log.append("Party fled successfully!")
            self.ran_away = True
            # Clear enemies logically (no loot/xp)
            for e in self.enemies:
                e.hp = 0
            self.turn = "ENEMY"
        else:
            self.log.append("Could not flee!")
            self._advance_turn()

    # --- NEW: steal attempt (THIEF only) ---
    def player_steal(self):
        # Weighted table roll merges consumable + equipment loot pools.
        a = self.active_actor
        if a.hero_class != "THIEF":
            self.log.append("Cannot Steal.")
            return
        tgt = self.target()
        if not tgt:
            self.log.append("No target.")
            return
        # success chance: base 55% + (agility diff *1.5%) capped
        diff = a.agility() - (10 + tgt.level)
        chance = clamp(0.55 + diff * 0.015, 0.10, 0.90)
        if random.random() > chance:
            self.log.append("Steal failed.")
            self._advance_turn()
            return
        species = tgt.species
        pool = []
        for item_id, ch, _ in LOOT_TABLES.get(species, []):
            pool.append((item_id, ch))
        for item_id, ch in EQUIP_DROPS.get(species, []):
            pool.append((item_id, ch))
        if not pool:
            self.log.append("Nothing to steal.")
            self._advance_turn()
            return
        # weighted pick
        total = sum(c for _, c in pool)
        r = random.random() * total
        acc = 0
        picked = pool[0][0]
        for iid, ch in pool:
            acc += ch
            if r <= acc:
                picked = iid
                break
        self.hero.inventory.add(picked, 1)  # shared inventory
        self.log.append(f"Stole {picked}!")
        self._advance_turn()

    def cast_spell(self, spell_id: str):
        a = self.active_actor
        if not a.can_cast(spell_id):
            self.log.append("Cannot cast that.")
            return
        sp = get_spell(spell_id)
        if a.mp < sp["mp"]:
            self.log.append("Not enough MP.")
            win_beep(300, 120)
            return
        a.mp -= sp["mp"]

        # Healing (ally)
        if sp["target"] == "ally":
            before = a.hp
            a.hp = clamp(a.hp + sp["power"] + int(a.magic() * 0.6), 0, a.max_hp())
            self.log.append(f"{sp['name']} heals {a.hp - before} HP.")
            self._advance_turn()
            return

        # Target selection
        if sp["aoe"]:
            targets = self.alive_enemies()
        else:
            tgt = self.target()
            if not tgt:
                self.log.append("No target.")
                return
            targets = [tgt]

        apply = sp.get("apply_status")
        parts = []
        for t in targets:
            dmg = 0
            mult = 1.0  # ensure defined for logging (fix Pylance warning)
            if sp["power"] > 0:
                base = sp["power"] + int(a.magic() * 0.8) + random.randint(0, 6)
                # Mastery bonus
                if sp["type"]:
                    base += a.spell_mastery.get(sp["type"].upper(), 0) * 4
                    if hasattr(t, "type"):
                        mult = type_multiplier(sp["type"], t.type)
                dmg = max(1, int(base * mult))
                # Apply (enemies currently have no elemental resist stat)
                t.hp = clamp(t.hp - dmg, 0, t.max_hp)
                if t.hp == 0:
                    self.hero.quest.record_kill(t.species)
            # Status effect (offensive only)
            if apply and t.hp > 0:
                store = getattr(t, "status_effects", None)
                if store is not None:
                    sid = apply["id"]
                    store[sid] = {"dur": apply["dur"], "pot": apply["pot"]}
                    self.log.append(f"{sid} inflicted on {t.species}.")
            if dmg > 0:
                tag = f"{t.species}:{dmg}"
                if sp["type"] and mult != 1.0:
                    if mult > 1.0: tag += " (weak)"
                    elif mult < 1.0: tag += " (resist)"
                parts.append(tag)

        if parts:
            self.log.append(f"{sp['name']} → " + " | ".join(parts))
            win_beep(1000, 90)

        self.shake_time = 0.18
        self._advance_turn()

    def use_item_from_menu(self, item_id: str):
        # Shared inventory (classic style)
        msg = use_item(self.active_actor, item_id)
        self.log.append(msg)
        if "Used" in msg or "Learned" in msg:
            win_beep(1000, 90)
        self.menu_items = None
        self._advance_turn()

    # enemies_turn modified to target any living party member
    def enemies_turn(self):
        # Each living enemy picks a random living party target.
        total_log = []
        for e in self.alive_enemies():
            if not self._party_alive(): break
            target = random.choice(self._party_alive())
            dmg = damage_from_attack(e.attack, target.defense())
            if getattr(target, "defending", False):
                dmg = max(1, dmg // 2)
            target.hp = clamp(target.hp - dmg, 0, target.max_hp())
            total_log.append(f"{e.species}->{target.name}:{dmg}")
        if total_log:
            self.log.append("Enemies act: " + " | ".join(total_log))
            win_beep(500, 90)
        for m in self._party_alive():
            m.defending = False
        # Reset to first living party member
        self.active_index = 0
        self.turn = "PLAYER"
        self.mode = "ROOT"
        self.menu_magic = None
        self.menu_items = None
        self._rebuild_root_menu()

    def process_status_effects(self):
        # Tick hero
        self._tick_entity_status(self.hero, is_hero=True)
        # Tick enemies
        for e in self.alive_enemies():
            self._tick_entity_status(e, is_hero=False)

    def _tick_entity_status(self, ent, is_hero: bool):
        if not hasattr(ent, "status_effects"): return
        expired = []
        for sid, data in ent.status_effects.items():
            data["dur"] -= 1
            if sid == "POISON":
                amt = max(3, int((ent.max_hp if hasattr(ent,'max_hp') else ent.max_hp()) * 0.05))
                ent.hp = clamp(ent.hp - amt, 0, ent.max_hp if hasattr(ent,'max_hp') else ent.max_hp())
                if is_hero: self.log.append(f"Poison deals {amt} to you.")
            elif sid == "BURN":
                amt = max(4, int((ent.max_hp if hasattr(ent,'max_hp') else ent.max_hp()) * 0.06))
                ent.hp = clamp(ent.hp - amt, 0, ent.max_hp if hasattr(ent,'max_hp') else ent.max_hp())
            elif sid == "REGEN":
                amt = max(3, int((ent.max_hp if hasattr(ent,'max_hp') else ent.max_hp()) * 0.05))
                ent.hp = clamp(ent.hp + amt, 0, ent.max_hp if hasattr(ent,'max_hp') else ent.max_hp())
            elif sid == "SLOW":
                # Simple slow: reduce next enemy total damage (implemented in enemies_turn)
                pass
            if data["dur"] <= 0:
                expired.append(sid)
        for sid in expired:
            del ent.status_effects[sid]

    # ---------- flow & input ----------
    def update(self, dt):
        if self.shake_time > 0:
            self.shake_time -= dt
        # step anim based on PLAYER turn (active member)
        if self.turn == "PLAYER":
            self.player_step_offset = min(self.player_step_target,
                                          self.player_step_offset + self.player_step_speed * dt)
        else:
            self.player_step_offset = max(0.0,
                                          self.player_step_offset - self.player_step_speed * dt)

    def handle_input(self, key):
        # Toggle compact log
        if key == pygame.K_TAB:
            self.compact_log = not self.compact_log

        if self.turn != "PLAYER":
            return

        a = self.active_actor
        alive = self.alive_enemies()
        if not alive or not a.is_alive():
            return

        if key in (pygame.K_LEFT, pygame.K_a):
            self.cursor = (self.cursor - 1) % max(1, len(alive))
        elif key in (pygame.K_RIGHT, pygame.K_d):
            self.cursor = (self.cursor + 1) % max(1, len(alive))

        if self.mode == "ROOT":
            mr = self.menu_root
            if mr is None:
                self._rebuild_root_menu()
                mr = self.menu_root
            if mr is None:
                return
            if key in (pygame.K_UP, pygame.K_w):
                mr.move(-1)
            elif key in (pygame.K_DOWN, pygame.K_s):
                mr.move(+1)
            elif key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                sel_idx = mr.selected_index()
                if 0 <= sel_idx < len(mr.items):
                    label = mr.items[sel_idx]
                    if label == "Attack":
                        self.player_attack()
                    elif label == "Steal":
                        self.player_steal()
                    elif label == "Magic":
                        self.menu_magic = None
                        self._ensure_magic_menu()
                        self.mode = "MAGIC"
                    elif label == "Items":
                        self.menu_items = None
                        self._ensure_items_menu()
                        self.mode = "ITEMS"
                    elif label == "Defend":
                        self.player_defend()
                    elif label == "Run":
                        self.player_run()

        elif self.mode == "MAGIC":
            m = self._ensure_magic_menu()
            if key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                self.mode = "ROOT"
            elif key in (pygame.K_UP, pygame.K_w):
                m.move(-1)
            elif key in (pygame.K_DOWN, pygame.K_s):
                m.move(+1)
            elif key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                idx = m.selected_index()
                if hasattr(self, "_magic_index_map") and 0 <= idx < len(self._magic_index_map):
                    self.cast_spell(self._magic_index_map[idx])

        elif self.mode == "ITEMS":
            m = self._ensure_items_menu()
            if key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                self.mode = "ROOT"
            elif key in (pygame.K_UP, pygame.K_w):
                m.move(-1)
            elif key in (pygame.K_DOWN, pygame.K_s):
                m.move(+1)
            elif key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                items = self.hero.inventory.all_items()
                if items:
                    item_id, _ = items[m.selected_index()]
                    self.use_item_from_menu(item_id)

        if self.turn == "ENEMY":
            self.end_turn_sequence()

    def end_turn_sequence(self):
        # On victory: loot once; fleeing skips rewards.
        if self.alive_enemies():
            self.enemies_turn()
        else:
            if self.ran_away:
                # Skip loot/xp
                pass
            else:
                if not self.victory_loot_done:
                    from core.loot import roll_loot
                    items, gold = roll_loot(self.enemies)
                    if items:
                        for iid, qty in items.items():
                            self.hero.inventory.add(iid, qty)
                        self.log.append("Loot: " + ", ".join([f"{iid} x{q}" for iid, q in items.items()]))
                    if gold > 0:
                        self.hero.gil += gold
                        self.log.append(f"Found {gold} Gil.")
                    self.victory_loot_done = True
        self.process_status_effects()

    # ---------- drawing ----------
    def _draw_log(self, surf, rect):
        pygame.draw.rect(surf, (20, 20, 26), rect, border_radius=8)
        pad = 8
        inner_w = rect.w - 2 * pad
        lines = []
        for msg in self.log[-40:]:
            lines.extend(wrap_text(msg, FONT, inner_w))
        y = rect.y + pad
        hline = FONT.get_height() + 2
        lines = lines[-((rect.h - 2 * pad) // hline):]
        if self.compact_log:
            lines = lines[-6:]
        for ln in lines:
            draw_text(surf, ln, rect.x + pad, y, WHITE, FONT)
            y += hline

    def draw(self, surf):
        # ...existing background and panel code...
        surf.fill((12, 12, 16))
        left_rect = pygame.Rect(PANEL_MARGIN, 72, SCREEN_W // 2 - PANEL_MARGIN * 2,
                                SCREEN_H - 72 - LOG_HEIGHT - 12)
        right_rect = pygame.Rect(SCREEN_W // 2 + PANEL_MARGIN, 72, SCREEN_W // 2 - PANEL_MARGIN * 2,
                                 SCREEN_H - 72 - LOG_HEIGHT - 12)
        pygame.draw.rect(surf, (24, 24, 30), left_rect, border_radius=10)
        pygame.draw.rect(surf, (24, 24, 30), right_rect, border_radius=10)

        # Enemies
        alive = self.alive_enemies()
        spacing = 110
        base_x = left_rect.x + 90
        base_y = left_rect.y + 70
        shake_x = random.randint(-3, 3) if self.shake_time > 0 else 0
        for i, e in enumerate(alive):
            ex = base_x + shake_x
            ey = base_y + i * spacing
            e.draw(surf, ex, ey)
            e.hp_bar(surf, ex - 70, ey + 36, 160, 12)
            if i == (self.cursor % (len(alive) or 1)):
                pygame.draw.circle(surf, WHITE, (int(ex), int(ey)), 30, 2)

        # Active actor large bar
        a = self.active_actor
        hero_base_x = right_rect.x + int(right_rect.w * 0.35)
        hero_base_y = right_rect.y + right_rect.h // 2 + 20
        hero_draw_x = hero_base_x - int(self.player_step_offset)
        a.draw_at(surf, hero_draw_x, hero_base_y)
        a.hp_bar(surf, right_rect.x + 10, right_rect.y + 10, w=right_rect.w - 20, h=12)

        # Repositioned combat stats (unchanged logic)
        # Layout math (relative to right_rect.y):
        # +10 HP bar top
        # +12 HP bar height
        # +4  spacer
        # +10 MP bar height
        # +3  spacer
        # +4  XP bar height
        # +6  padding
        stats_y = right_rect.y + 10 + 12 + 4 + 10 + 3 + 4 + 6
        draw_text(surf,
                  f"{a.name} ATK:{a.attack()} MAG:{a.magic()} DEF:{a.defense()} Gil:{self.hero.gil}",
                  right_rect.x + 14, stats_y, WHITE, FONT)

        # --- NEW: companion mini HP bars ---
        if len(self.party) > 1:
            cy = right_rect.y + right_rect.h - 100
            for idx, c in enumerate(self.party):
                if c is a: continue  # skip active (already big)
                col = (60,140,220) if c.is_alive() else RED
                pct = c.hp / max(1, c.max_hp())
                w = right_rect.w - 40
                pygame.draw.rect(surf, (40,40,50), (right_rect.x + 20, cy, w, 10), border_radius=4)
                pygame.draw.rect(surf, col, (right_rect.x + 20, cy, int(w*pct), 10), border_radius=4)
                draw_text(surf, f"{c.name} {c.hp}/{c.max_hp()}", right_rect.x + 22, cy - 16, WHITE, FONT)
                cy += 34

        # --- NEW TURN ORDER BAR (horizontal along bottom of player field) ---
        order = self._turn_order_preview()
        bar_h = 54
        bar_rect = pygame.Rect(right_rect.x + 8,
                               right_rect.bottom - bar_h - 8,
                               right_rect.w - 16,
                               bar_h)
        pygame.draw.rect(surf, (30, 32, 42), bar_rect, border_radius=10)
        pygame.draw.rect(surf, (70, 72, 90), bar_rect, 1, border_radius=10)
        # Layout entries horizontally
        pad = 10
        entry_w = max(90, (bar_rect.w - pad*2) // max(1, len(order)))
        x = bar_rect.x + pad
        y_name = bar_rect.y + 8
        y_agi = bar_rect.y + 28
        for idx, (kind, name, agi) in enumerate(order):
            active = (name == a.name and idx == 0 and self.turn == "PLAYER")
            col_box = (55, 58, 76) if not active else (85, 90, 130)
            cell = pygame.Rect(x, bar_rect.y + 4, entry_w - 6, bar_h - 8)
            pygame.draw.rect(surf, col_box, cell, border_radius=6)
            pygame.draw.rect(surf, (110,110,140) if active else (70,70,90), cell, 1, border_radius=6)
            disp = "You" if name == self.hero.name else name[:10]
            draw_text(surf, disp, cell.x + 8, y_name, GOLD if active else WHITE, FONT_BIG)
            draw_text(surf, f"AGI:{agi}", cell.x + 8, y_agi, SILVER if active else WHITE, FONT)
            x += entry_w
            if x > bar_rect.right - entry_w // 2:
                break  # safety overflow guard

        # Menus (root guarded)
        if self.menu_root:
            self.menu_root.draw(surf, h=180)
        if self.mode == "MAGIC" and self.menu_magic is not None:
            self.menu_magic.draw(surf)
        elif self.mode == "ITEMS" and self.menu_items is not None:
            self.menu_items.draw(surf)

        # Log
        log_rect = pygame.Rect(PANEL_MARGIN, SCREEN_H - LOG_HEIGHT - 12,
                               SCREEN_W - PANEL_MARGIN * 2, LOG_HEIGHT)
        self._draw_log(surf, log_rect)

        # Victory / flee / defeat banners
        alive_en = self.alive_enemies()
        if not alive_en and not self.ran_away and self.hero.is_alive():
            draw_text(surf, "Victory! Press ENTER to return.", PANEL_MARGIN, 24, GOLD, FONT_BIG)
        elif self.ran_away and self.hero.is_alive():
            draw_text(surf, "You fled. Press ENTER to return.", PANEL_MARGIN, 24, SILVER, FONT_BIG)
        elif not any(p.is_alive() for p in self.party):
            draw_text(surf, "Defeat!", PANEL_MARGIN, 24, RED, FONT_BIG)
            draw_text(surf, "Press R to Reload or N New Game", PANEL_MARGIN, 52, RED, FONT)
