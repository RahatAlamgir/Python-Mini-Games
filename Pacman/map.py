import json
import math
import os
import pygame

pygame.init()
pygame.mixer.init(frequency=44100, size=-16, channels=1, buffer=512)

CELL_SIZE = 20
HUD_HEIGHT = 60

COLOR_BG = (0, 0, 0)
COLOR_DOT = (255, 184, 151)
COLOR_POWER = (255, 255, 255)
COLOR_TEXT = (240, 240, 240)
COLOR_PACMAN = (255, 255, 0)
COLOR_SCORE_POPUP = (0, 255, 255)

COLOR_BTN = (33, 33, 150)
COLOR_BTN_HOVER = (60, 60, 220)
COLOR_BTN_TEXT = (255, 255, 255)

SAVE_FILE = "pacman_highscore.json"
DEFAULT_WALL_COLOR = (33, 33, 255)

PACMAN_SPEED = 2.5
GHOST_SPEED_NORMAL = 2.0
GHOST_SPEED_SCARED = 1.25
GHOST_SPEED_EYES = 4.0

def load_maps():
    if not os.path.exists("levels.json"):
        raise FileNotFoundError("levels.json was not found in the project root directory!")
    
    with open("levels.json", "r") as f:
        data = json.load(f)
    
    maps = []

    def parse_entry(entry):
        if isinstance(entry, dict):
            layout = entry.get("layout", entry.get("grid", []))
            raw_color = entry.get("color", DEFAULT_WALL_COLOR)
            color = tuple(raw_color) if isinstance(raw_color, list) else DEFAULT_WALL_COLOR
            return {"layout": layout, "color": color}
        elif isinstance(entry, list):
            return {"layout": entry, "color": DEFAULT_WALL_COLOR}
        return {"layout": [], "color": DEFAULT_WALL_COLOR}

    if isinstance(data, list):
        for item in data:
            maps.append(parse_entry(item))
    elif isinstance(data, dict):
        sorted_keys = sorted(data.keys(), key=lambda k: int(''.join(filter(str.isdigit, k))) if any(c.isdigit() for c in k) else k)
        for key in sorted_keys:
            maps.append(parse_entry(data[key]))

    return maps

ALL_MAPS = load_maps()

initial_grid_w = max(len(row) for row in ALL_MAPS[0]["layout"])
initial_grid_h = len(ALL_MAPS[0]["layout"])
screen = pygame.display.set_mode((initial_grid_w * CELL_SIZE, initial_grid_h * CELL_SIZE + HUD_HEIGHT))
pygame.display.set_caption("Pac-Man Arcade - Dynamic Levels")

img_sprites = pygame.image.load("sprites.png").convert_alpha() if os.path.exists("sprites.png") else None

def get_sprite(x, y, w=16, h=16):
    if img_sprites is None: return None
    rect = pygame.Rect(x, y, w, h)
    surf = pygame.Surface(rect.size, pygame.SRCALPHA)
    surf.blit(img_sprites, (0, 0), rect)
    return pygame.transform.scale(surf, (CELL_SIZE, CELL_SIZE))

SPRITE_PACMAN_RIGHT = [get_sprite(0, 0), get_sprite(16, 0), get_sprite(32, 0)]
SPRITE_PACMAN_LEFT = [get_sprite(0, 16), get_sprite(16, 16), get_sprite(32, 16)]
SPRITE_PACMAN_UP = [get_sprite(0, 32), get_sprite(16, 32), get_sprite(32, 32)]
SPRITE_PACMAN_DOWN = [get_sprite(0, 48), get_sprite(16, 48), get_sprite(32, 48)]
SPRITE_GHOSTS = [
    [get_sprite(0, 64), get_sprite(16, 64)], [get_sprite(0, 80), get_sprite(16, 80)],
    [get_sprite(0, 96), get_sprite(16, 96)], [get_sprite(0, 112), get_sprite(16, 112)]
]
SPRITE_SCARED = [get_sprite(128, 64), get_sprite(144, 64)]
SPRITE_FLASH = [get_sprite(160, 64), get_sprite(176, 64)]
SPRITE_EYES_RIGHT = get_sprite(128, 80)
SPRITE_EYES_LEFT = get_sprite(144, 80)
SPRITE_EYES_UP = get_sprite(160, 80)
SPRITE_EYES_DOWN = get_sprite(176, 80)
SPRITES_FRUIT = [get_sprite(32, 48), get_sprite(48, 48), get_sprite(64, 48), get_sprite(80, 48)]

def draw_maze(surface, maze, color_wall=(33, 33, 255)):
    grid_h = len(maze)

    def is_w(gx, gy):
        if 0 <= gy < grid_h and 0 <= gx < len(maze[gy]):
            return maze[gy][gx] == "W"
        return False

    for margin, radius in [(1, 6), (4, 3)]:
        for y, row in enumerate(maze):
            for x, char in enumerate(row):
                if char != "W":
                    continue

                rx, ry = x * CELL_SIZE, y * CELL_SIZE + HUD_HEIGHT
                top = not is_w(x, y - 1)
                bot = not is_w(x, y + 1)
                left = not is_w(x - 1, y)
                right = not is_w(x + 1, y)
                r = radius
                m = margin

                # Straight Edges
                if top:
                    x1 = rx + (r if left else m)
                    x2 = rx + CELL_SIZE - (r if right else m)
                    pygame.draw.line(surface, color_wall, (x1, ry + m), (x2, ry + m), 1)
                if bot:
                    x1 = rx + (r if left else m)
                    x2 = rx + CELL_SIZE - (r if right else m)
                    pygame.draw.line(surface, color_wall, (x1, ry + CELL_SIZE - m), (x2, ry + CELL_SIZE - m), 1)
                if left:
                    y1 = ry + (r if top else m)
                    y2 = ry + CELL_SIZE - (r if bot else m)
                    pygame.draw.line(surface, color_wall, (rx + m, y1), (rx + m, y2), 1)
                if right:
                    y1 = ry + (r if top else m)
                    y2 = ry + CELL_SIZE - (r if bot else m)
                    pygame.draw.line(surface, color_wall, (rx + CELL_SIZE - m, y1), (rx + CELL_SIZE - m, y2), 1)

                # Outer Corners
                if top and left:
                    pygame.draw.arc(surface, color_wall, (rx + m, ry + m, (r - m) * 2, (r - m) * 2), math.pi / 2, math.pi, 1)
                if top and right:
                    pygame.draw.arc(surface, color_wall, (rx + CELL_SIZE - r * 2 + m, ry + m, (r - m) * 2, (r - m) * 2), 0, math.pi / 2, 1)
                if bot and left:
                    pygame.draw.arc(surface, color_wall, (rx + m, ry + CELL_SIZE - r * 2 + m, (r - m) * 2, (r - m) * 2), math.pi, 3 * math.pi / 2, 1)
                if bot and right:
                    pygame.draw.arc(surface, color_wall, (rx + CELL_SIZE - r * 2 + m, ry + CELL_SIZE - r * 2 + m, (r - m) * 2, (r - m) * 2), 3 * math.pi / 2, 2 * math.pi, 1)

                # Inner Fillets
                if not top and not left and not is_w(x - 1, y - 1):
                    pygame.draw.arc(surface, color_wall, (rx - m, ry - m, m * 2, m * 2), 3 * math.pi / 2, 2 * math.pi, 1)
                if not top and not right and not is_w(x + 1, y - 1):
                    pygame.draw.arc(surface, color_wall, (rx + CELL_SIZE - m, ry - m, m * 2, m * 2), math.pi, 3 * math.pi / 2, 1)
                if not bot and not left and not is_w(x - 1, y + 1):
                    pygame.draw.arc(surface, color_wall, (rx - m, ry + CELL_SIZE - m, m * 2, m * 2), 0, math.pi / 2, 1)
                if not bot and not right and not is_w(x + 1, y + 1):
                    pygame.draw.arc(surface, color_wall, (rx + CELL_SIZE - m, ry + CELL_SIZE - m, m * 2, m * 2), math.pi / 2, math.pi, 1)

    for y, row in enumerate(maze):
        for x, char in enumerate(row):
            if char == "G":
                rx, ry = x * CELL_SIZE, y * CELL_SIZE + HUD_HEIGHT
                pygame.draw.line(surface, (255, 182, 193), (rx, ry + CELL_SIZE // 2), (rx + CELL_SIZE, ry + CELL_SIZE // 2), 2)