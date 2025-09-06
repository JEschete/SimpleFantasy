from settings import GEN1_TYPES, RANK_COST

# Each spell: id -> {name,type,rank,mp,power,aoe,target}
# Rank2 = AoE, Rank3 = strong ST, Rank4 = strong AoE

def _s(name, t, r, p=None, power=18, aoe=False, target="enemy", school="BLACK"):
    return {"id":name, "name":name, "type":t, "rank":r,
            "mp": p if p is not None else RANK_COST.get(r, 6),
            "power": power, "aoe": aoe, "target": target, "school": school}

def _status(id_, mp, status_id, dur, potency=0, target="enemy", school="BLACK"):
    return {"id":id_, "name":id_, "type":None, "rank":1, "mp":mp, "power":0,
            "aoe":False, "target":target,
            "apply_status":{"id":status_id,"dur":dur,"pot":potency},
            "school": school}

SPELLS = {
    # BLACK magic (offense / status)
    "FIRE1": _s("FIRE1","FIRE",1,power=20,school="BLACK"),
    "FIRE2": _s("FIRE2","FIRE",2,power=18,aoe=True,school="BLACK"),
    "FIRE3": _s("FIRE3","FIRE",3,power=34,school="BLACK"),
    "FIRE4": _s("FIRE4","FIRE",4,power=30,aoe=True,school="BLACK"),

    "WATER1": _s("WATER1","WATER",1,power=20,school="BLACK"),
    "WATER2": _s("WATER2","WATER",2,power=18,aoe=True,school="BLACK"),

    "THUNDER1": _s("THUNDER1","ELECTRIC",1,power=20,school="BLACK"),
    "THUNDER2": _s("THUNDER2","ELECTRIC",2,power=18,aoe=True,school="BLACK"),

    "ICE1": _s("ICE1","ICE",1,power=20,school="BLACK"),
    "ICE2": _s("ICE2","ICE",2,power=18,aoe=True,school="BLACK"),

    "POISON1": _status("POISON1", 10, "POISON", 5, potency=5, school="BLACK"),
    "BURN1":   _status("BURN1",   10, "BURN",   5, potency=6, school="BLACK"),
    "SLOW1":   _status("SLOW1",    8, "SLOW",   4, potency=20, school="BLACK"),

    # WHITE magic (restoration / support)
    "CURE1": {"id":"CURE1","name":"CURE1","type":None,"rank":1,"mp":8,"power":26,
              "aoe":False,"target":"ally","school":"WHITE"},
    "REGEN1": _status("REGEN1", 10, "REGEN", 5, potency=5, target="ally", school="WHITE"),
}

# Per-class defaults
DEFAULT_CLASS_KNOWN = {
    "BLACK_MAGE": ["FIRE1"],
    "WHITE_MAGE": ["CURE1"],
    # Others start with none (can still learn allowed schools if any in future)
}

def get_spell(spell_id): return SPELLS[spell_id]
def known_default_for(hero_class: str):
    return list(DEFAULT_CLASS_KNOWN.get(hero_class.upper(), []))
def all_spell_ids(): return list(SPELLS.keys())
