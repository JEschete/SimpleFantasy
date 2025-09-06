import random
from data.inventory import ITEMS, generate_affixed_equipment

# Base consumable drops (raised chances slightly)
LOOT_TABLES = {
    "GOBLIN": [("POTION", 0.45, (1,1)), ("ETHER", 0.20, (1,1))],
    "WOLF":   [("POTION", 0.40, (1,1)), ("HI_POTION",0.08,(1,1))],
    "SLIME":  [("ETHER", 0.35, (1,1)), ("HI_ETHER",0.06,(1,1))],
    "BAT":    [("POTION", 0.32, (1,1))],
    "GOLEM":  [("POTION", 0.55, (1,2)), ("HI_POTION",0.12,(1,1)), ("ETHER", 0.30,(1,1))]
}

# Equipment (separate so we can keep probabilities clear)
EQUIP_DROPS = {
    "GOBLIN": [("WOOD_SWORD", 0.06)],
    "WOLF":   [("LEATHER_ARM", 0.05)],
    "SLIME":  [("LEATHER_HELM", 0.05)],
    "BAT":    [("WOOD_SHIELD", 0.05)],
    "GOLEM":  [("BRONZE_ARM", 0.08), ("TOWER_SHIELD",0.04), ("POWER_SWORD",0.04)]
}

GOLD_ROLL = {
    "GOBLIN": (14, 32),
    "WOLF":   (10, 22),
    "SLIME":  (8, 18),
    "BAT":    (6, 16),
    "GOLEM":  (24, 55),
}

def roll_loot(enemies):
    items = {}
    gold = 0
    for e in enemies:
        species = getattr(e, "species", "GOBLIN")
        # consumables
        for item_id, chance, (lo, hi) in LOOT_TABLES.get(species, []):
            if random.random() < chance:
                qty = random.randint(lo, hi)
                items[item_id] = items.get(item_id, 0) + qty
        # equipment (each independent roll)
        for item_id, chance in EQUIP_DROPS.get(species, []):
            if random.random() < chance:
                affixed_id = generate_affixed_equipment(item_id)
                items[affixed_id] = items.get(affixed_id, 0) + 1
        # gold
        g_lo, g_hi = GOLD_ROLL.get(species, (5, 15))
        gold += random.randint(g_lo, g_hi)
    return items, gold
