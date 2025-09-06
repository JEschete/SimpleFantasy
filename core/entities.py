import pygame
from settings import *
from data.inventory import Inventory, ITEMS, EQUIP_SLOTS
from data.spells import known_default_for, get_spell
from core.quest import QuestManager
import random

CLASS_ALLOWED_SCHOOLS = {
    # Empty sets mean physical classes with no arcane schools.
    "BLACK_MAGE": {"BLACK"},
    "WHITE_MAGE": {"WHITE"},
    "FIGHTER": set(),      # no magic
    "THIEF": set(),        # no magic (can Steal)
}

class Hero:
    def __init__(self, hero_class: str = "FIGHTER", name: str = "Hero"):
        # base stats
        self.base_level = 1
        self.xp = 0
        self.xp_to_next_level = 100
        self.base_hp = 120
        self.base_mp = 36
        self.base_attack = 14
        self.base_magic = 18
        self.base_defense = 6

        # current pools
        self.hp = self.base_hp
        self.mp = self.base_mp

        # overworld position
        self.x = SCREEN_W * 0.7
        self.y = SCREEN_H * 0.6
        self.w = 36; self.h = 48
        self.color = BLUE

        # effects / flags
        self.status_effects = {}
        self.defending = False

        # gear & inventory
        # CHANGED: add explicit value type (str | None) so Pylance accepts assigning item ids later.
        self.equipment: dict[str, str | None] = {slot: None for slot in EQUIP_SLOTS}
        self.inventory = Inventory()

        # identity / class
        self.hero_class = hero_class.upper()
        self.name = name

        # base agility & class adjustments (single authoritative block)
        self.base_agility = 12
        if self.hero_class == "BLACK_MAGE":
            self.base_magic += 8; self.base_mp += 14; self.base_defense -= 2; self.base_agility += 2
        elif self.hero_class == "WHITE_MAGE":
            self.base_magic += 6; self.base_mp += 16; self.base_defense -= 1; self.base_agility += 1
        elif self.hero_class == "THIEF":
            self.base_attack += 2; self.base_agility += 8; self.base_defense -= 1
        elif self.hero_class == "FIGHTER":
            self.base_attack += 4; self.base_defense += 2

        # party link
        self.party = [self]

        # starting spells (class-based)
        self.known_spells = known_default_for(self.hero_class)

        # currency / progression
        self.gil: int = 0          # <-- added (fix Pylance)
        self.quest = QuestManager()

        # talents / mastery
        self.talent_points = 0
        self.spell_mastery = {"FIRE":0,"ICE":0,"ELECTRIC":0,"WATER":0,"POISON":0}

    # ---- Effective stats (base + gear bonuses) ----
    def _gear_bonus(self, key):
        total = 0
        for _, item_id in self.equipment.items():
            if not item_id: continue
            total += ITEMS[item_id].stats.get(key, 0)
        return total

    def level(self): return self.base_level
    def max_hp(self): return self.base_hp + self._gear_bonus("hp")
    def max_mp(self): return self.base_mp + self._gear_bonus("mp")
    def attack(self): return self.base_attack + self._gear_bonus("attack")
    def magic(self): return self.base_magic + self._gear_bonus("magic")
    def defense(self): return self.base_defense + self._gear_bonus("defense")
    def agility(self): return self.base_agility + self._gear_bonus("agility")

    def is_alive(self): return self.hp > 0

    def resistance(self, elem: str) -> int:
        """Aggregate percentage resistance (can be negative)."""
        key = f"res_{elem.upper()}"
        total = 0
        for _, item_id in self.equipment.items():
            if not item_id: continue
            total += ITEMS[item_id].stats.get(key, 0)
        return total

    def level_up(self):
        self.base_level += 1
        self.xp -= self.xp_to_next_level
        self.xp_to_next_level = int(100 * (1.3 ** self.base_level))
        self.base_hp += 15; self.base_mp += 8
        self.base_attack += 3; self.base_magic += 4; self.base_defense += 1
        self.hp = self.max_hp(); self.mp = self.max_mp()
        self.talent_points += 1   # NEW: 1 point each level
        return f"Leveled up to {self.base_level}! (Talent +1)"

    def add_xp(self, amount):
        if not self.is_alive(): return []
        self.xp += amount; msgs=[]; leveled=False
        while self.xp >= self.xp_to_next_level:
            msgs.append(self.level_up()); leveled=True
        if leveled: win_beep(1200,200)
        return msgs

    # ---- Inventory helpers ----
    def draw(self, surf):
        rect = pygame.Rect(int(self.x - self.w/2), int(self.y - self.h/2), self.w, self.h)
        pygame.draw.rect(surf, self.color, rect, border_radius=6)
        pygame.draw.rect(surf, SILVER, (rect.right + 6, rect.top + 8, 8, rect.height-16), border_radius=3)
        if 'POISON' in self.status_effects:
            draw_text(surf, "PSN", rect.centerx - 12, rect.top - 20, POISON_COLOR, FONT_BIG)

    def draw_at(self, surf, x, y):
        rect = pygame.Rect(int(x - self.w/2), int(y - self.h/2), self.w, self.h)
        pygame.draw.rect(surf, self.color, rect, border_radius=6)
        pygame.draw.rect(surf, SILVER, (rect.right + 6, rect.top + 8, 8, rect.height-16), border_radius=3)
        if 'POISON' in self.status_effects:
            draw_text(surf, "PSN", rect.centerx - 12, rect.top - 20, POISON_COLOR, FONT_BIG)

    def hp_bar(self, surf, x, y, w=320, h=12):
        # HP bar
        hp_ratio = self.hp / self.max_hp()
        pygame.draw.rect(surf, GRAY, (x, y, w, h), border_radius=4)
        pygame.draw.rect(surf, BLUE, (x, y, int(w * hp_ratio), h), border_radius=4)

        # MP bar
        mp_h = 10
        pygame.draw.rect(surf, (40, 40, 60), (x, y + h + 4, w, mp_h), border_radius=3)
        pygame.draw.rect(surf, MANA_COLOR, (x, y + h + 4, int(w * (self.mp / self.max_mp())), mp_h), border_radius=3)

        # XP bar
        xp_ratio = self.xp / self.xp_to_next_level
        pygame.draw.rect(surf, (50, 20, 70), (x, y + h + 4 + mp_h + 3, w, 4), border_radius=2)
        pygame.draw.rect(surf, PURPLE, (x, y + h + 4 + mp_h + 3, int(w * xp_ratio), 4), border_radius=2)

        draw_text(surf, f"Lv:{self.level()} HP:{self.hp}/{self.max_hp()}  MP:{self.mp}/{self.max_mp()}  Gil:{self.gil}", x+6, y-20, WHITE, FONT_BIG)

    def invest_attribute(self, which: str) -> bool:
        if self.talent_points <= 0: return False
        if which == "HP": self.base_hp += 10
        elif which == "MP": self.base_mp += 6
        elif which == "ATK": self.base_attack += 2
        elif which == "MAG": self.base_magic += 2
        elif which == "DEF": self.base_defense += 1
        else: return False
        self.talent_points -= 1
        return True

    def invest_mastery(self, elem: str) -> bool:
        elem = elem.upper()
        if elem not in self.spell_mastery or self.talent_points <= 0: return False
        self.spell_mastery[elem] += 1
        self.talent_points -= 1
        return True

    # --- NEW: class spell gating ---
    def can_learn_spell(self, spell: dict) -> bool:
        school = spell.get("school")
        if not school: return False
        return school in CLASS_ALLOWED_SCHOOLS.get(self.hero_class, set())

    def can_cast(self, spell_id: str) -> bool:
        if spell_id not in self.known_spells: return False
        sp = get_spell(spell_id)
        return self.can_learn_spell(sp)

    def prune_illegal_spells(self):
        # Drops spells outside permitted school set.
        self.known_spells = [s for s in self.known_spells if self.can_cast(s)]

    def to_companion_dict(self):
        return {
            "name": self.name,
            "hero_class": self.hero_class,
            "base_level": self.base_level,
            "xp": self.xp,
            "xp_to_next_level": self.xp_to_next_level,
            "base_hp": self.base_hp,
            "base_mp": self.base_mp,
            "base_attack": self.base_attack,
            "base_magic": self.base_magic,
            "base_defense": self.base_defense,
            "base_agility": self.base_agility,
            "talent_points": self.talent_points,
            "spell_mastery": self.spell_mastery,
            "equipment": self.equipment,
            "known_spells": self.known_spells,
        }

    def apply_companion_dict(self, d: dict):
        self.name = d.get("name", self.name)
        self.base_level = d.get("base_level", self.base_level)
        self.xp = d.get("xp", self.xp)
        self.xp_to_next_level = d.get("xp_to_next_level", self.xp_to_next_level)
        self.base_hp = d.get("base_hp", self.base_hp)
        self.base_mp = d.get("base_mp", self.base_mp)
        self.base_attack = d.get("base_attack", self.base_attack)
        self.base_magic = d.get("base_magic", self.base_magic)
        self.base_defense = d.get("base_defense", self.base_defense)
        self.base_agility = d.get("base_agility", self.base_agility)
        self.talent_points = d.get("talent_points", self.talent_points)
        self.spell_mastery.update(d.get("spell_mastery", {}))
        self.equipment = d.get("equipment", self.equipment)
        self.known_spells = list(d.get("known_spells", self.known_spells))
        self.hp = self.max_hp()
        self.mp = self.max_mp()
        if hasattr(self, "prune_illegal_spells"):
            self.prune_illegal_spells()

class Enemy:
    # species: Goblin, Wolf, Slime, Bat, Golem... each has a primary type
    SPECIES = [
        ("GOBLIN","FIGHTING"),
        ("WOLF","NORMAL"),
        ("SLIME","POISON"),
        ("BAT","FLYING"),
        ("GOLEM","ROCK"),
        ("DRAGON","DRAGON"),  # NEW high‑level foe (>=10)
    ]

    def __init__(self, kind, level=1):
        self.species = kind
        self.type = dict(self.SPECIES)[kind]

        base_hp = {
            "GOBLIN":60,"WOLF":54,"SLIME":52,"BAT":48,"GOLEM":72,
            "DRAGON":140,  # NEW
        }[kind]
        base_atk = {
            "GOBLIN":14,"WOLF":12,"SLIME":10,"BAT":11,"GOLEM":13,
            "DRAGON":22,   # NEW
        }[kind]
        self.level = level
        self.max_hp = base_hp + 6*level
        self.hp = self.max_hp
        self.attack = base_atk + 2*level
        self.xp_yield = 16 + level * 5
        self.status_effects = {}
        self.agility = 10 + level  # NEW: simple initiative stat

    def is_alive(self): return self.hp > 0

    def draw(self, surf, x, y, r=24):
        col = get_type_color(self.type)
        pygame.draw.circle(surf, col, (int(x), int(y)), r)
        pygame.draw.circle(surf, DARK, (int(x), int(y)), r, 2)
        if 'POISON' in self.status_effects:
            draw_text(surf, "PSN", x - 12, y - r - 20, POISON_COLOR, FONT_BIG)

    def hp_bar(self, surf, x, y, w=140, h=12):
        ratio = clamp(self.hp / self.max_hp, 0, 1)
        pygame.draw.rect(surf, GRAY, (x, y, w, h), border_radius=3)
        pygame.draw.rect(surf, get_type_color(self.type), (x, y, int(w*ratio), h), border_radius=3)
        draw_text(surf, f"L{self.level} {self.species} {self.hp}/{self.max_hp}", x, y-18, WHITE, FONT)
        pygame.draw.rect(surf, get_type_color(self.type), (x, y, int(w*ratio), h), border_radius=3)
        draw_text(surf, f"L{self.level} {self.species} {self.hp}/{self.max_hp}", x, y-18, WHITE, FONT)
