from settings import *
from data.spells import get_spell
import random as _rnd

EQUIP_SLOTS = ["weapon","helm","armor","shield"]

class ItemDef:
    def __init__(self, id, name, kind, price=10, desc="", slot=None,
                 stats=None, use_effect=None, unlock_spell=None, value=0,
                 quality="COMMON", dynamic=False):
        self.id=id; self.name=name; self.kind=kind; self.price=price; self.desc=desc
        self.slot=slot; self.stats=stats or {}
        self.use_effect=use_effect
        self.unlock_spell=unlock_spell
        self.value=value
        self.quality = quality
        self.dynamic = dynamic  # NEW: generated at runtime

    def clone_with(self, new_id, new_name, added_stats, price_mult, quality):
        merged = dict(self.stats)
        for k, v in added_stats.items():
            merged[k] = merged.get(k, 0) + v
        return ItemDef(new_id, new_name, self.kind,
                       price=max(1, int(self.price * price_mult)),
                       desc=self.desc, slot=self.slot,
                       stats=merged, unlock_spell=self.unlock_spell,
                       quality=quality, dynamic=True)

def _use_potion(hero):
    old=hero.hp; hero.hp=clamp(hero.hp+40,0,hero.max_hp()); return f"Used Potion. +{hero.hp-old} HP."
def _use_ether(hero):
    old=hero.mp; hero.mp=clamp(hero.mp+24,0,hero.max_mp()); return f"Used Ether. +{hero.mp-old} MP."
# NEW higher tier
def _use_hi_potion(hero):
    old=hero.hp; hero.hp=clamp(hero.hp+120,0,hero.max_hp()); return f"Used Hi-Potion. +{hero.hp-old} HP."
def _use_mega_potion(hero):
    old=hero.hp; hero.hp=clamp(hero.hp+300,0,hero.max_hp()); return f"Used Mega-Potion. +{hero.hp-old} HP."
def _use_hi_ether(hero):
    old=hero.mp; hero.mp=clamp(hero.mp+60,0,hero.max_mp()); return f"Used Hi-Ether. +{hero.mp-old} MP."

# --- NEW: affix definitions ---
AFFIX_PREFIXES = [
    {"id":"STRONG","name":"Strong","stats":{"attack":+3},"price_mult":1.25,"weight":8},
    {"id":"ARCANE","name":"Arcane","stats":{"magic":+4,"attack":-1},"price_mult":1.30,"weight":7},
    {"id":"GUARDED","name":"Guarded","stats":{"defense":+4},"price_mult":1.28,"weight":6},
    {"id":"BLOODED","name":"Blooded","stats":{"hp":+18,"defense":-1},"price_mult":1.22,"weight":5},
]
AFFIX_SUFFIXES = [
    {"id":"OF_POWER","name":"of Power","stats":{"attack":+5,"defense":-2},"price_mult":1.45,"weight":5},
    {"id":"OF_WARDING","name":"of Warding","stats":{"defense":+6},"price_mult":1.50,"weight":5},
    {"id":"OF_INSIGHT","name":"of Insight","stats":{"magic":+6},"price_mult":1.55,"weight":4},
    {"id":"OF_VIGOR","name":"of Vigor","stats":{"hp":+30},"price_mult":1.40,"weight":4},
]

ITEMS = {
    # ...existing lower tier consumables...
    "POTION": ItemDef("POTION","Potion","consumable",price=30,use_effect=_use_potion,desc="+40 HP"),
    "ETHER":  ItemDef("ETHER","Ether","consumable",price=60,use_effect=_use_ether,desc="+24 MP"),

    # NEW higher-tier consumables
    "HI_POTION":   ItemDef("HI_POTION","Hi-Potion","consumable",price=120,use_effect=_use_hi_potion,desc="+120 HP",quality="UNCOMMON"),
    "MEGA_POTION": ItemDef("MEGA_POTION","Mega-Potion","consumable",price=300,use_effect=_use_mega_potion,desc="+300 HP",quality="RARE"),
    "HI_ETHER":    ItemDef("HI_ETHER","Hi-Ether","consumable",price=140,use_effect=_use_hi_ether,desc="+60 MP",quality="UNCOMMON"),

    # ...existing base gear...
    "WOOD_SWORD":   ItemDef("WOOD_SWORD","Wood Sword","equipment",price=80,slot="weapon",stats={"attack":+4}),
    "LEATHER_HELM": ItemDef("LEATHER_HELM","Leather Helm","equipment",price=60,slot="helm",stats={"defense":+2}),
    "LEATHER_ARM":  ItemDef("LEATHER_ARM","Leather Armor","equipment",price=90,slot="armor",stats={"defense":+4,"hp":+10}),
    "WOOD_SHIELD":  ItemDef("WOOD_SHIELD","Wood Shield","equipment",price=70,slot="shield",stats={"defense":+3}),

    # NEW equipment with trade-offs / qualities
    "BRONZE_ARM":  ItemDef("BRONZE_ARM","Bronze Armor","equipment",price=180,slot="armor",
                           stats={"defense":+10,"magic":-3},quality="UNCOMMON",
                           desc="+DEF, reduces MAG"),
    "MAGE_ROBE":   ItemDef("MAGE_ROBE","Mage Robe","equipment",price=210,slot="armor",
                           stats={"magic":+8,"defense":-2,"hp":-5},quality="UNCOMMON",
                           desc="+MAG, lowers DEF & HP"),
    "POWER_SWORD": ItemDef("POWER_SWORD","Power Sword","equipment",price=250,slot="weapon",
                           stats={"attack":+8,"defense":-2,"magic":-1},quality="RARE",
                           desc="High ATK, slight DEF/MAG penalty"),
    "TOWER_SHIELD":ItemDef("TOWER_SHIELD","Tower Shield","equipment",price=230,slot="shield",
                           stats={"defense":+12,"attack":-2,"magic":-2},quality="RARE",
                           desc="Massive DEF, hurts ATK & MAG"),

    # Spell tomes
    "TOME_FIRE2":      ItemDef("TOME_FIRE2","Tome: FIRE2","spell_tome",price=120,unlock_spell="FIRE2"),
    "TOME_THUNDER1":   ItemDef("TOME_THUNDER1","Tome: THUNDER1","spell_tome",price=90,unlock_spell="THUNDER1"),
    "TOME_ICE1":       ItemDef("TOME_ICE1","Tome: ICE1","spell_tome",price=90,unlock_spell="ICE1"),

    # NEW: Status spell tomes
    "TOME_POISON1": ItemDef("TOME_POISON1","Tome: POISON1","spell_tome",price=110,unlock_spell="POISON1"),
    "TOME_BURN1":   ItemDef("TOME_BURN1","Tome: BURN1","spell_tome",price=110,unlock_spell="BURN1"),
    "TOME_SLOW1":   ItemDef("TOME_SLOW1","Tome: SLOW1","spell_tome",price=95, unlock_spell="SLOW1"),
    "TOME_REGEN1":  ItemDef("TOME_REGEN1","Tome: REGEN1","spell_tome",price=140,unlock_spell="REGEN1"),

    # NEW: gear with resistances / negatives
    "EMBER_CLOAK":  ItemDef("EMBER_CLOAK","Ember Cloak","equipment",price=260,slot="armor",
                            stats={"defense":+2,"magic":+4,"res_FIRE":15,"res_ICE":-10},quality="UNCOMMON",
                            desc="+FIRE RES -ICE RES"),
    "FROST_RING":   ItemDef("FROST_RING","Frost Ring","equipment",price=220,slot="helm",
                            stats={"magic":+3,"res_ICE":18,"res_FIRE":-8},quality="UNCOMMON",
                            desc="+ICE RES -FIRE RES"),
    "WARD_SHIELD":  ItemDef("WARD_SHIELD","Ward Shield","equipment",price=300,slot="shield",
                            stats={"defense":+6,"res_FIRE":8,"res_ICE":8,"res_ELECTRIC":8},quality="RARE",
                            desc="Balanced elemental ward"),
}

# --- NEW: buy/sell helpers ---
def item_buy_price(item_id): return ITEMS[item_id].price
def item_sell_price(item_id): return max(1, int(item_buy_price(item_id) * 0.45))
# Backwards compatibility
def item_price(item_id): return item_buy_price(item_id)

# --- Affix generation utilities ---
def _pick_affix(table):
    total = sum(a["weight"] for a in table)
    r = _rnd.uniform(0, total)
    acc = 0
    for a in table:
        acc += a["weight"]
        if r <= acc:
            return a
    return None

def generate_affixed_equipment(base_id: str) -> str:
    base = ITEMS[base_id]
    if base.kind != "equipment":
        return base_id
    # 50% prefix, 50% suffix (independent)
    prefix = _pick_affix(AFFIX_PREFIXES) if _rnd.random() < 0.5 else None
    suffix = _pick_affix(AFFIX_SUFFIXES) if _rnd.random() < 0.5 else None
    if not prefix and not suffix:
        return base_id
    parts_stats = {}
    price_mult = 1.0
    name_parts = []
    if prefix:
        for k,v in prefix["stats"].items():
            parts_stats[k] = parts_stats.get(k,0) + v
        price_mult *= prefix["price_mult"]
        name_parts.append(prefix["name"])
    name_parts.append(base.name)
    if suffix:
        for k,v in suffix["stats"].items():
            parts_stats[k] = parts_stats.get(k,0) + v
        price_mult *= suffix["price_mult"]
        name_parts.append(suffix["name"])
    new_name = " ".join(name_parts)
    # quality escalation
    q_score = price_mult
    if q_score >= 2.2 or (prefix and suffix):
        quality = "RARE"
    elif q_score >= 1.4:
        quality = "UNCOMMON"
    else:
        quality = base.quality
    new_id = base_id
    if prefix: new_id += f"#P{prefix['id']}"
    if suffix: new_id += f"#S{suffix['id']}"
    if new_id in ITEMS:
        return new_id
    ITEMS[new_id] = base.clone_with(new_id, new_name, parts_stats, price_mult, quality)
    return new_id

class Inventory:
    def __init__(self):
        self.counts = {}     # item_id -> qty

    def add(self, item_id, qty=1):
        self.counts[item_id] = self.counts.get(item_id,0) + qty

    def take(self, item_id, qty=1):
        if self.counts.get(item_id,0) >= qty:
            self.counts[item_id]-=qty
            if self.counts[item_id]<=0: del self.counts[item_id]
            return True
        return False

    def qty(self, item_id): return self.counts.get(item_id,0)

    def all_items(self):  # list of (id, qty)
        return sorted(self.counts.items())

def use_item(hero, item_id):
    idef = ITEMS[item_id]
    if hero.inventory.qty(item_id)<=0: return "None left."
    if idef.kind=="consumable" and idef.use_effect:
        hero.inventory.take(item_id,1)
        return idef.use_effect(hero)
    if idef.kind=="spell_tome" and idef.unlock_spell:
        sp = get_spell(idef.unlock_spell)
        # NEW: class restriction
        if not hero.can_learn_spell(sp):
            return "Your class cannot learn that."
        if idef.unlock_spell in hero.known_spells:
            return "You already know that spell."
        hero.inventory.take(item_id,1)
        hero.known_spells.append(idef.unlock_spell)
        return f"Learned {idef.unlock_spell}!"
    return "Cannot use that."

def equippable_for_slot(slot):
    return [k for k,v in ITEMS.items() if v.kind=="equipment" and v.slot==slot]

def item_name(item_id): return ITEMS[item_id].name
