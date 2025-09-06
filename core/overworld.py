import pygame, random
from settings import *
from core.battle import Battle

class Overworld:
    """
    Lightweight overworld controller: handles player movement, a shop zone,
    random encounters, and on-screen toasts.
    """
    def __init__(self, hero):
        self.hero = hero
        self.speed = 220.0  # px/sec
        self.toast = ""
        self.toast_timer = 0.0
        self._moving = False

        # Simple zones
        self.shop_rect = pygame.Rect(80, 96, 180, 120)
        # "Grass" area where encounters can occur
        self.grass_rect = pygame.Rect(60, 360, SCREEN_W - 120, 260)
        self.tavern_rect = pygame.Rect(300, 96, 220, 120)  # NEW tavern zone

        # Encounter control
        self._encounter_cooldown = 0.0  # seconds
        self.movement_locked = False    # NEW

    # ----- UI helpers -----
    def set_toast(self, msg: str, dur: float = 2.2):
        self.toast = msg or ""
        self.toast_timer = dur

    def near_shop(self) -> bool:
        hx, hy, w, h = self.hero.x - self.hero.w/2, self.hero.y - self.hero.h/2, self.hero.w, self.hero.h
        return pygame.Rect(hx, hy, w, h).colliderect(self.shop_rect)

    def near_tavern(self) -> bool:
        hx, hy, w, h = self.hero.x - self.hero.w/2, self.hero.y - self.hero.h/2, self.hero.w, self.hero.h
        return pygame.Rect(hx, hy, w, h).colliderect(self.tavern_rect)

    # ----- Loop -----
    def update(self, dt: float, keys):
        # Allow timers (toast/cooldowns) to tick even if locked
        if not self.movement_locked:
            dx = dy = 0.0
            if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                dx -= 1
            if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                dx += 1
            if keys[pygame.K_UP] or keys[pygame.K_w]:
                dy -= 1
            if keys[pygame.K_DOWN] or keys[pygame.K_s]:
                dy += 1
            self._moving = (dx != 0) or (dy != 0)
            if self._moving:
                # Normalize
                mag = (dx * dx + dy * dy) ** 0.5
                if mag > 0:
                    dx /= mag; dy /= mag
                self.hero.x += dx * self.speed * dt
                self.hero.y += dy * self.speed * dt

            # Clamp to screen
            m = 24
            self.hero.x = clamp(self.hero.x, m, SCREEN_W - m)
            self.hero.y = clamp(self.hero.y, m + HUD_HEIGHT, SCREEN_H - m)
        else:
            self._moving = False  # ensure no encounters while locked

        # Toast + cooldown always tick
        if self.toast_timer > 0:
            self.toast_timer -= dt
            if self.toast_timer <= 0:
                self.toast = ""
        if self._encounter_cooldown > 0:
            self._encounter_cooldown = max(0.0, self._encounter_cooldown - dt)

    def maybe_encounter(self):
        """
        Called from main loop after update(). Returns a Battle or None.
        Requires: moving, within grass, and cooldown elapsed.
        """
        if self._encounter_cooldown > 0:
            return None
        # Check if hero is in grass
        hx, hy, w, h = self.hero.x - self.hero.w/2, self.hero.y - self.hero.h/2, self.hero.w, self.hero.h
        in_grass = pygame.Rect(hx, hy, w, h).colliderect(self.grass_rect)

        if self._moving and in_grass:
            # ~2–3% per poll; tuned to feel like classic JRPG step chance
            if random.random() < 0.025:
                self._encounter_cooldown = 1.5
                # Encounter level near hero level
                enc_lvl = max(1, self.hero.level() + random.choice([-1, 0, 0, 1]))
                return Battle(self.hero, enc_lvl)
        return None

    def draw(self, surf):
        surf.fill((10, 12, 14))

        # Simple world tiles
        pygame.draw.rect(surf, (32, 32, 40), (0, HUD_HEIGHT, SCREEN_W, SCREEN_H - HUD_HEIGHT))
        # Grass where encounters happen
        pygame.draw.rect(surf, (26, 60, 26), self.grass_rect, border_radius=10)
        draw_text(surf, "Tall Grass", self.grass_rect.x + 6, self.grass_rect.y - 18, GREEN, FONT)

        # Shop area
        pygame.draw.rect(surf, (40, 30, 18), self.shop_rect, border_radius=10)
        pygame.draw.rect(surf, (120, 90, 40), self.shop_rect, 2, border_radius=10)
        draw_text(surf, "SHOP", self.shop_rect.x + 10, self.shop_rect.y + 8, GOLD, FONT_BIG)
        draw_text(surf, "Press [ENTER] to talk", self.shop_rect.x + 10, self.shop_rect.y + 34, WHITE, FONT)

        # NEW Tavern area
        pygame.draw.rect(surf, (26, 30, 55), self.tavern_rect, border_radius=10)
        pygame.draw.rect(surf, (90, 110, 200), self.tavern_rect, 2, border_radius=10)
        draw_text(surf, "TAVERN", self.tavern_rect.x + 10, self.tavern_rect.y + 8, CYAN, FONT_BIG)
        draw_text(surf, "Press [Y] to hire", self.tavern_rect.x + 10, self.tavern_rect.y + 34, WHITE, FONT)

        # Hero
        self.hero.draw(surf)

        # HUD / Toast
        if self.toast:
            pad = 10
            msg_w = FONT_BIG.size(self.toast)[0] + pad * 2
            x = PANEL_MARGIN
            y = SCREEN_H - LOG_HEIGHT - 18 - 40
            pygame.draw.rect(surf, (20, 20, 26), (x, y, msg_w, 36), border_radius=8)
            draw_text(surf, self.toast, x + pad, y + 8, WHITE, FONT_BIG)
