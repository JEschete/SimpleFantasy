class Quest:
    def __init__(self, qid, name, desc, goal_species, goal_count, reward_xp=0, reward_gil=0):
        self.id = qid
        self.name = name
        self.desc = desc
        self.goal_species = goal_species
        self.goal_count = goal_count
        self.reward_xp = reward_xp
        self.reward_gil = reward_gil
        self.progress = 0
        self.completed = False
        self.turned_in = False

    def record_kill(self, species):
        if self.completed or self.turned_in: return
        if species == self.goal_species:
            self.progress = min(self.goal_count, self.progress + 1)
            if self.progress >= self.goal_count:
                self.completed = True

    def status_line(self):
        if self.turned_in: return f"{self.name}: (Finished)"
        if self.completed: return f"{self.name}: COMPLETE! ({self.progress}/{self.goal_count})"
        return f"{self.name}: {self.progress}/{self.goal_count}"

    def turn_in(self, hero):
        if not self.completed or self.turned_in: return None
        self.turned_in = True
        hero.gil += self.reward_gil
        xp_msgs = hero.add_xp(self.reward_xp)
        msg = f"Quest '{self.name}' rewards: {self.reward_xp} XP, {self.reward_gil} Gil."
        return [msg] + xp_msgs

    def to_dict(self):
        return {
            "progress": self.progress,
            "completed": self.completed,
            "turned_in": self.turned_in,
            "goal_species": self.goal_species,
            "goal_count": self.goal_count,
            "reward_xp": self.reward_xp,
            "reward_gil": self.reward_gil,
            "name": self.name,
            "desc": self.desc,
        }

    def load_dict(self, d):
        self.progress = d.get("progress", self.progress)
        self.completed = d.get("completed", self.completed)
        self.turned_in = d.get("turned_in", self.turned_in)

class QuestManager:
    def __init__(self):
        # Seed with a single starter quest; expandable later.
        self.quests = {
            "Q_GOB_01": Quest("Q_GOB_01",
                              "Cull Goblins",
                              "Defeat 5 Goblins menacing the road.",
                              "GOBLIN", 5, reward_xp=80, reward_gil=120)
        }

    def record_kill(self, species):
        for q in self.quests.values():
            q.record_kill(species)

    def turn_in_completed(self, hero):
        msgs = []
        for q in self.quests.values():
            if q.completed and not q.turned_in:
                got = q.turn_in(hero)
                if got:
                    msgs.extend(got)
        return msgs

    def all_status_lines(self):
        return [q.status_line() for q in self.quests.values()]

    def summary(self):
        done = sum(1 for q in self.quests.values() if q.turned_in)
        total = len(self.quests)
        return f"Quests: {done}/{total} finished"

    # --- NEW: persistence helpers ---
    def serialize(self):
        return {qid: q.to_dict() for qid, q in self.quests.items()}

    def load_state(self, data: dict):
        if not data: return
        for qid, qdata in data.items():
            if qid in self.quests:
                self.quests[qid].load_dict(qdata)
            else:
                # Future: unknown quest id -> could instantiate if definitions expand
                pass
