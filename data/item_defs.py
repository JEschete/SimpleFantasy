# =====================================
# === FILE: item_defs.py
# =====================================
import pygame as pg
from typing import Optional, Dict, Any

# Minimal item model. If you already have one, adapt the adapter at bottom.
class Item:
    __slots__ = ("id","name","type","stackable","max_stack","icon","meta")
    def __init__(self, id: str, name: str, type: str, stackable: bool=False, max_stack:int=1, icon: Optional[pg.Surface]=None, meta: Optional[Dict[str,Any]]=None):
        self.id = id
        self.name = name
        self.type = type            # e.g., 'weapon','armor_head','potion','misc'
        self.stackable = stackable
        self.max_stack = max_stack
        self.icon = icon
        self.meta = meta or {}

# Basic item registry
ITEMS: Dict[str, Item] = {}

def register(item: Item):
    ITEMS[item.id] = item
    return item

# Example placeholder icons (colored squares)

def _mk_icon(color):
    s = pg.Surface((48,48), pg.SRCALPHA)
    s.fill(color)
    pg.draw.rect(s, (0,0,0), s.get_rect(), 2)
    return s

# Example items
WEAPON_SWORD = register(Item("weapon_sword", "Iron Sword", "weapon", False, 1, _mk_icon((150, 150, 200)), {"atk": 5}))
HELMET_LEATHER = register(Item("helmet_leather", "Leather Cap", "armor_head", False, 1, _mk_icon((160, 110, 60)), {"def": 2}))
POTION_SMALL = register(Item("potion_small", "Small Potion", "potion", True, 5, _mk_icon((180, 40, 60)), {"heal": 30}))
GOLD_COIN = register(Item("gold_coin", "Gold Coin", "currency", True, 999, _mk_icon((220, 200, 60))))

# Helper to clone an item entry as an instance with count
class ItemStack:
    __slots__ = ("item","count")
    def __init__(self, item: Item, count: int=1):
        self.item = item
        self.count = count
    def split(self, n: int):
        n = min(n, self.count)
        self.count -= n
        return ItemStack(self.item, n)
    def can_stack_with(self, other: 'ItemStack') -> bool:
        return self.item.id == other.item.id and self.item.stackable
    def room_for(self, other: 'ItemStack') -> int:
        if not self.item.stackable: return 0
        return max(0, self.item.max_stack - self.count)