# shop.py
import pygame as pg
import random, time
from settings import GOLD, WHITE, SILVER, draw_text
from ui.shop_ui import ShopUI
from data.inventory import ITEMS, item_price

def _today():
    return int(time.time() // 86400)

class Shop:
    """
    Randomized daily shop:
      - First open each real-world day auto-rolls stock.
      - Press R to reroll (first reroll per day free, afterwards 50 Gil).
    """
    def __init__(self):
        self.ui = ShopUI(pos=(24, 420), cols=5, rows=2, title="Shop")
        self.opened = False
        # Daily / reroll tracking
        self._last_roll_day: int | None = None
        self._last_free_reroll_day: int | None = None
        # Gold callbacks (wired via connect)
        self.ui.get_gold = lambda: 0
        self.ui.add_gold = lambda n: None
        self.ui.try_add_to_inventory = None

    # -------- stock rolling --------
    def _roll_stock(self):
        cap = self.ui.cols * self.ui.rows  # 10
        # Build category pools
        consumables = [i for i, d in ITEMS.items() if d.kind == "consumable"]
        tomes       = [i for i, d in ITEMS.items() if d.kind == "spell_tome"]
        gear        = [i for i, d in ITEMS.items() if d.kind == "equipment" and not getattr(d, "dynamic", False)]
        rng = random.Random(time.time())
        rng.shuffle(consumables); rng.shuffle(tomes); rng.shuffle(gear)
        stock: list[str] = []
        # Baseline targets (adjust if pools small)
        def take(src, n):
            for iid in src[:n]:
                if iid not in stock:
                    stock.append(iid)
        take(consumables, min(3, len(consumables)))
        take(tomes, min(2, len(tomes)))
        take(gear, min(5, len(gear)))
        # Fill remainder with mixed pool
        mixed = consumables + tomes + gear
        rng.shuffle(mixed)
        for iid in mixed:
            if len(stock) >= cap: break
            if iid not in stock:
                stock.append(iid)
        stock = stock[:cap]
        self.ui.set_stock(stock)
        self._last_roll_day = _today()

    def _ensure_today_stock(self):
        if self._last_roll_day != _today():
            self._roll_stock()

    def _attempt_reroll(self):
        day = _today()
        free = (self._last_free_reroll_day != day)
        cost = 0 if free else 50
        if self.ui.get_gold() < cost:
            return  # not enough gold
        if cost:
            self.ui.add_gold(-cost)
        else:
            self._last_free_reroll_day = day
        self._roll_stock()

    # -------- lifecycle --------
    def open(self):
        self.opened = True
        self._ensure_today_stock()
        self.ui.open()

    def close(self):
        self.opened = False
        self.ui.close()

    # -------- events / draw --------
    def handle_event(self, ev):
        if not self.opened: return
        # Reroll key
        if ev.type == pg.KEYDOWN and ev.key == pg.K_r:
            self._attempt_reroll()
            return
        self.ui.handle_event(ev)

    def draw(self, surf):
        if not self.opened: return
        self.ui.draw(surf)
        # Hint / status line
        x = self.ui.rect.x
        y = self.ui.rect.bottom + 6
        day = _today()
        free_available = (self._last_free_reroll_day != day)
        msg = "R: Reroll stock (FREE)" if free_available else "R: Reroll stock (50 Gil)"
        draw_text(surf, msg, x + 4, y, SILVER)

    # Wiring from Game (gold + inventory handlers)
    def connect(self, get_gold, add_gold, try_add_to_inventory):
        self.ui.get_gold = get_gold
        self.ui.add_gold = add_gold
        self.ui.try_add_to_inventory = try_add_to_inventory

    def is_over(self, pos):
        return self.ui.is_over(pos)
