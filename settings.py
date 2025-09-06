import pygame

pygame.font.init()

# ---- Screen / Layout ----
SCREEN_W, SCREEN_H = 1920, 1080
HUD_HEIGHT = 64
LOG_HEIGHT = 112
PANEL_MARGIN = 40

# ---- Fonts ----
FONT = pygame.font.SysFont(None, 22)
FONT_BIG = pygame.font.SysFont(None, 28)

# ---- Colors ----
BLACK = (0, 0, 0); WHITE = (255, 255, 255); GRAY = (60, 60, 60); DARK = (18, 18, 18)
RED = (220, 40, 40); CYAN = (40, 200, 220); YELLOW = (240, 220, 60); GREEN = (60, 200, 80)
BLUE = (80, 120, 220); PURPLE = (160, 80, 200); SILVER = (180, 180, 200)
POISON_COLOR = (120, 40, 140); GOLD = (240, 200, 80); MANA_COLOR = (90, 180, 255)

# ---- Gen-1 Types (intended) ----
GEN1_TYPES = [
    "NORMAL","FIRE","WATER","ELECTRIC","GRASS","ICE","FIGHTING","POISON","GROUND",
    "FLYING","PSYCHIC","BUG","ROCK","GHOST","DRAGON"
]

TYPE_COLORS = {
    "NORMAL": (200, 200, 200),
    "FIRE": RED, "WATER": (60, 140, 240), "ELECTRIC": YELLOW, "GRASS": (70, 200, 90),
    "ICE": CYAN, "FIGHTING": (200, 80, 60), "POISON": POISON_COLOR, "GROUND": (180, 140, 80),
    "FLYING": (160, 160, 240), "PSYCHIC": (240, 90, 160), "BUG": (120, 180, 60),
    "ROCK": (170, 160, 110), "GHOST": (130, 90, 180), "DRAGON": (90, 120, 200),
}

def get_type_color(t): return TYPE_COLORS.get(t, WHITE)

# Multipliers: attacker -> defender -> mult
# (Intended RBY: e.g., Ghost 2x vs Psychic, 0x vs Normal; Electric 0x vs Ground; Ground 0x vs Flying)
TYPE_CHART = {
    "NORMAL":   {"ROCK":0.5,"GHOST":0.0},
    "FIRE":     {"GRASS":2.0,"ICE":2.0,"BUG":2.0,"FIRE":0.5,"WATER":0.5,"ROCK":0.5,"DRAGON":0.5},
    "WATER":    {"FIRE":2.0,"GROUND":2.0,"ROCK":2.0,"WATER":0.5,"GRASS":0.5,"DRAGON":0.5},
    "ELECTRIC": {"WATER":2.0,"FLYING":2.0,"GROUND":0.0,"ELECTRIC":0.5,"GRASS":0.5,"DRAGON":0.5},
    "GRASS":    {"WATER":2.0,"GROUND":2.0,"ROCK":2.0,"FIRE":0.5,"GRASS":0.5,"POISON":0.5,"FLYING":0.5,"BUG":0.5,"DRAGON":0.5},
    "ICE":      {"GRASS":2.0,"GROUND":2.0,"FLYING":2.0,"DRAGON":2.0,"WATER":0.5,"ICE":0.5},
    "FIGHTING": {"NORMAL":2.0,"ICE":2.0,"ROCK":2.0,"POISON":0.5,"FLYING":0.5,"PSYCHIC":0.5,"BUG":0.5,"GHOST":0.0},
    "POISON":   {"GRASS":2.0,"BUG":2.0,"POISON":0.5,"GROUND":0.5,"ROCK":0.5,"GHOST":0.5},
    "GROUND":   {"FIRE":2.0,"ELECTRIC":2.0,"POISON":2.0,"ROCK":2.0,"FLYING":0.0,"GRASS":0.5,"BUG":0.5},
    "FLYING":   {"GRASS":2.0,"FIGHTING":2.0,"BUG":2.0,"ELECTRIC":0.5,"ROCK":0.5},
    "PSYCHIC":  {"FIGHTING":2.0,"POISON":2.0,"PSYCHIC":0.5},
    "BUG":      {"GRASS":2.0,"POISON":2.0,"PSYCHIC":2.0,"FIRE":0.5,"FIGHTING":0.5,"FLYING":0.5,"GHOST":0.5},
    "ROCK":     {"FIRE":2.0,"ICE":2.0,"FLYING":2.0,"BUG":2.0,"FIGHTING":0.5,"GROUND":0.5},
    "GHOST":    {"PSYCHIC":2.0,"NORMAL":0.0},
    "DRAGON":   {"DRAGON":2.0},
}

# ---- Spell MP Costs default (can be overridden per spell) ----
# Adjusted for steeper progression (previously 6/10/14/20)
RANK_COST = {1: 6, 2: 12, 3: 20, 4: 30}

# ---- Utilities ----
def clamp(v, lo, hi): return max(lo, min(hi, v))

def type_multiplier(attacker_type, defender_type):
    return TYPE_CHART.get(attacker_type, {}).get(defender_type, 1.0)

def draw_text(surf, text, x, y, color=WHITE, font=FONT):
    img = font.render(text, True, color); surf.blit(img, (x, y))

def wrap_text(text, font, max_width):
    words, lines, line = text.split(), [], ""
    for w in words:
        test = w if not line else f"{line} {w}"
        if font.size(test)[0] <= max_width: line = test
        else:
            if line: lines.append(line)
            line = w
    if line: lines.append(line)
    return lines

def win_beep(freq=600, dur=80):
    try:
        import winsound; winsound.Beep(int(freq), int(dur))
    except Exception:
        pass
