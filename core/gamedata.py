import json, os
from data.inventory import EQUIP_SLOTS, ITEMS, ItemDef

SAVE_FILE = "ff_save.json"  # legacy
SAVE_SLOTS = {
    1: "ff_save_slot1.json",
    2: "ff_save_slot2.json",
    3: "ff_save_slot3.json",
}

def _slot_path(slot: int) -> str:
    return SAVE_SLOTS.get(slot, SAVE_SLOTS[1])

def _collect_dynamic_items(hero):
    """Collect dynamic (affixed) items across whole party."""
    needed_ids = set()
    party = getattr(hero, "party", [hero])
    for member in party:
        for iid in getattr(member.inventory, "counts", {}).keys():
            if iid in ITEMS and getattr(ITEMS[iid], "dynamic", False):
                needed_ids.add(iid)
        for _, iid in member.equipment.items():
            if iid and iid in ITEMS and getattr(ITEMS[iid], "dynamic", False):
                needed_ids.add(iid)
    out = []
    for iid in needed_ids:
        idef = ITEMS[iid]
        out.append({
            "id": idef.id,
            "name": idef.name,
            "kind": idef.kind,
            "price": idef.price,
            "desc": idef.desc,
            "slot": idef.slot,
            "stats": idef.stats,
            "unlock_spell": idef.unlock_spell,
            "quality": idef.quality,
        })
    return out

def _rebuild_dynamic_items(dynamic_list):
    for d in dynamic_list:
        iid = d["id"]
        if iid in ITEMS:  # already present
            continue
        ITEMS[iid] = ItemDef(
            d["id"], d.get("name", iid), d.get("kind", "equipment"),
            price=d.get("price", 10), desc=d.get("desc",""),
            slot=d.get("slot"), stats=d.get("stats", {}), unlock_spell=d.get("unlock_spell"),
            quality=d.get("quality","COMMON"), dynamic=True
        )

def save_game(hero, slot: int = 1):
    companions = []
    if hasattr(hero, "party"):
        for m in hero.party[1:]:
            companions.append(m.to_companion_dict())
    data = {
        "level": hero.level(),
        "xp": hero.xp,
        "xp_to_next_level": hero.xp_to_next_level,
        "base_hp": hero.base_hp, "hp": hero.hp,
        "base_mp": hero.base_mp, "mp": hero.mp,
        "base_attack": hero.base_attack, "base_magic": hero.base_magic, "base_defense": hero.base_defense,
        "equipment": hero.equipment,
        "inventory": hero.inventory.counts,
        "known_spells": hero.known_spells,
        "gil": hero.gil,
        "x": hero.x, "y": hero.y,
        "talent_points": hero.talent_points,
        "spell_mastery": hero.spell_mastery,
        "quests": hero.quest.serialize(),
        "dynamic_items": _collect_dynamic_items(hero),
        "hero_class": getattr(hero, "hero_class", "FIGHTER"),
        "base_agility": getattr(hero, "base_agility", 12),
        "hero_name": getattr(hero, "name", "Hero"),
        "companions": companions,          # NEW
        "version": 5
    }
    with open(_slot_path(slot), "w") as f: json.dump(data, f)
    return f"Saved slot {slot}."

def load_game(hero, slot: int = 1):
    path = _slot_path(slot)
    if not os.path.exists(path): return "No save file."
    with open(path,"r") as f: data=json.load(f)
    _rebuild_dynamic_items(data.get("dynamic_items", []))

    # --- APPLY CLASS FIRST (so later gating uses correct class) ---
    saved_class = data.get("hero_class", getattr(hero, "hero_class", "FIGHTER"))
    saved_class = (saved_class or "FIGHTER").upper()
    hero.hero_class = saved_class

    # core level / stats
    hero.base_level = int(data.get("level", hero.level()))
    hero.xp = int(data.get("xp", hero.xp))
    hero.xp_to_next_level = int(data.get("xp_to_next_level", hero.xp_to_next_level))
    hero.base_hp = int(data.get("base_hp", hero.base_hp)); hero.hp = int(data.get("hp", hero.hp))
    hero.base_mp = int(data.get("base_mp", hero.base_mp)); hero.mp = int(data.get("mp", hero.mp))
    hero.base_attack = int(data.get("base_attack", hero.base_attack))
    hero.base_magic  = int(data.get("base_magic", hero.base_magic))
    hero.base_defense= int(data.get("base_defense", hero.base_defense))
    hero.equipment = {k: data.get("equipment", {}).get(k) for k in EQUIP_SLOTS}
    hero.inventory.counts = dict(data.get("inventory", {}))
    hero.known_spells = list(data.get("known_spells", hero.known_spells))
    hero.gil = int(data.get("gil", hero.gil))
    hero.x = float(data.get("x", hero.x)); hero.y = float(data.get("y", hero.y))

    hero.base_agility = int(data.get("base_agility", getattr(hero,"base_agility",12)))
    hero.name = data.get("hero_name", getattr(hero, "name", "Hero"))

    # --- NEW loads ---
    hero.talent_points = int(data.get("talent_points", hero.talent_points))
    hero.spell_mastery.update(data.get("spell_mastery", {}))
    hero.quest.load_state(data.get("quests", {}))

    # Rebuild party companions (overwrite hero.party)
    comps = data.get("companions", [])
    hero.party = [hero]
    for cdat in comps[:3]:
        try:
            from core.entities import Hero as _H
            comp = _H(hero_class=cdat.get("hero_class","FIGHTER"), name=cdat.get("name","Ally"))
            comp.apply_companion_dict(cdat)
            comp.party = hero.party
            hero.party.append(comp)
        except Exception:
            continue

    # --- CLASS SPELL VALIDATION / DEFAULTS ---
    if hasattr(hero, "prune_illegal_spells"):
        before = set(hero.known_spells)
        hero.prune_illegal_spells()
        # If everything was stripped (e.g., class changed or prior bad save), seed defaults
        if not hero.known_spells:
            try:
                from data.spells import known_default_for
                hero.known_spells = known_default_for(hero.hero_class)
            except Exception:
                pass
        # (Optional) could log difference if needed; skipped for brevity

    return f"Loaded slot {slot}."

def list_saves():
    """Return list of (slot, present, meta_dict_or_None)."""
    out = []
    for slot, path in SAVE_SLOTS.items():
        if os.path.exists(path):
            try:
                with open(path,"r") as f: d=json.load(f)
                out.append((slot, True, {
                    "name": d.get("hero_name","Hero"),
                    "level": d.get("level",1),
                    "class": d.get("hero_class","FIGHTER")
                }))
            except Exception:
                out.append((slot, True, None))
        else:
            out.append((slot, False, None))
    return out
