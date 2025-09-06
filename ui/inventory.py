# Deprecated legacy inventory module.
# Single source of truth is data.inventory.
# Kept only for backward compatibility with older imports.
from data.inventory import *  # type: ignore  # noqa

# Intentionally no __all__ (static analyzers complained about dynamic construction).
# Do not add local ItemDef / Inventory / ITEMS here to avoid conflicts.
def _use_potion(hero):
    old=hero.hp; hero.hp=clamp(hero.hp+40,0,hero.max_hp()); return f"Used Potion. +{hero.hp-old} HP."
def _use_ether(hero):
    old=hero.mp; hero.mp=clamp(hero.mp+24,0,hero.max_mp()); return f"Used Ether. +{hero.mp-old} MP."

ITEMS = {
    "POTION": ItemDef("POTION","Potion","consumable",price=30,use_effect=_use_potion,desc="+40 HP"),
    "ETHER":  ItemDef("ETHER","Ether","consumable",price=60,use_effect=_use_ether,desc="+24 MP"),

    # Basic gear (add more later)
    "WOOD_SWORD":  ItemDef("WOOD_SWORD","Wood Sword","equipment",price=80,slot="weapon",stats={"attack":+4}),
    "LEATHER_HELM":ItemDef("LEATHER_HELM","Leather Helm","equipment",price=60,slot="helm",stats={"defense":+2}),
    "LEATHER_ARM": ItemDef("LEATHER_ARM","Leather Armor","equipment",price=90,slot="armor",stats={"defense":+4,"hp":+10}),
    "WOOD_SHIELD": ItemDef("WOOD_SHIELD","Wood Shield","equipment",price=70,slot="shield",stats={"defense":+3}),

    # Spell tomes unlock spells when used/purchased
    "TOME_FIRE2": ItemDef("TOME_FIRE2","Tome: FIRE2","spell_tome",price=120,unlock_spell="FIRE2"),
    "TOME_THUNDER1": ItemDef("TOME_THUNDER1","Tome: THUNDER1","spell_tome",price=90,unlock_spell="THUNDER1"),
    "TOME_ICE1": ItemDef("TOME_ICE1","Tome: ICE1","spell_tome",price=90,unlock_spell="ICE1"),
}

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
        if idef.unlock_spell in hero.known_spells:
            return "You already know that spell."
        hero.inventory.take(item_id,1)
        hero.known_spells.append(idef.unlock_spell)
        return f"Learned {idef.unlock_spell}!"
    return "Cannot use that."

def equippable_for_slot(slot):
    return [k for k,v in ITEMS.items() if v.kind=="equipment" and v.slot==slot]

def item_name(item_id): return ITEMS[item_id].name
def item_price(item_id): return ITEMS[item_id].price
