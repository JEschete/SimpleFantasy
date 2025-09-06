import pygame
from settings import *

class Menu:
    def __init__(self, x, y, w, items, title=None):
        self.x, self.y, self.w = x, y, w
        self.items = items[:]  # list of strings
        self.title = title
        self.cursor = 0

    def move(self, dy):
        if not self.items: return
        self.cursor = (self.cursor + dy) % len(self.items)

    def selected_index(self): return self.cursor

    def draw(self, surf, h=None):
        # background
        if h is None: h = 24 + 24*len(self.items)
        pygame.draw.rect(surf, (28,28,36), (self.x, self.y, self.w, h), border_radius=8)
        y = self.y + 8
        if self.title:
            draw_text(surf, self.title, self.x + 10, y, WHITE, FONT_BIG)
            y += 26
        for i, txt in enumerate(self.items):
            prefix = ">" if i == self.cursor else " "
            draw_text(surf, f"{prefix} {txt}", self.x + 12, y, WHITE, FONT)
            y += 22
