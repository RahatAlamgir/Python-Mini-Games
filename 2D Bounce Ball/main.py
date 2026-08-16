import sys
import json
import os
import math
import random
import pygame

# --- CONSTANTS ---
GRID_WIDTH = 100
GRID_HEIGHT = 60
TILE_SIZE = 40

WORLD_WIDTH = GRID_WIDTH * TILE_SIZE    # 4000 px
WORLD_HEIGHT = GRID_HEIGHT * TILE_SIZE  # 2400 px

SCREEN_WIDTH = 1024
SCREEN_HEIGHT = 768
FPS = 60

# --- GAME STATES ---
STATE_MENU = "MENU"
STATE_LEVEL_SELECT = "LEVEL_SELECT"
STATE_GAME = "GAME"
STATE_PAUSE = "PAUSE"

# --- COLORS ---
COLOR_BG = (15, 18, 26)
COLOR_WALL_FALLBACK = (65, 75, 90)
COLOR_SPIKE_FILL = (220, 40, 40)
COLOR_SPIKE_OUTLINE = (140, 20, 20)
COLOR_WATER_SURFACE = (60, 160, 255, 180)
COLOR_WATER_DEEP = (20, 80, 180, 150)
COLOR_PLATFORM_FALLBACK = (180, 140, 60)
COLOR_PLAYER = (255, 215, 0)
COLOR_EXIT_FALLBACK = (50, 220, 100)
COLOR_TEXT = (0, 0, 0)
COLOR_OUTLINE = (255, 255, 255)
COLOR_BTN = (40, 50, 75)
COLOR_BTN_HOVER = (70, 90, 130)
COLOR_BTN_BORDER = (90, 120, 170)

# --- TEXT OUTLINE HELPER ---
def render_outlined_text(font, text, text_color=COLOR_TEXT, outline_color=COLOR_OUTLINE, outline_width=2):
    base_surf = font.render(text, True, text_color)
    outline_surf = font.render(text, True, outline_color)
    
    w = base_surf.get_width() + outline_width * 2
    h = base_surf.get_height() + outline_width * 2
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    
    for dx in range(-outline_width, outline_width + 1):
        for dy in range(-outline_width, outline_width + 1):
            if dx != 0 or dy != 0:
                surf.blit(outline_surf, (dx + outline_width, dy + outline_width))
                
    surf.blit(base_surf, (outline_width, outline_width))
    return surf

# --- TILESET LOADER ---
class SciFiTileset:
    def __init__(self, filename="sci-fy1.png"):
        self.tiles = {}
        self.loaded = False
        if os.path.exists(filename):
            try:
                sheet = pygame.image.load(filename).convert_alpha()
                sw, sh = sheet.get_size()
                tw, th = sw // 8, sh // 8

                def slice_tile(col, row):
                    rect = pygame.Rect(col * tw, row * th, tw, th)
                    sub = sheet.subsurface(rect)
                    return pygame.transform.scale(sub, (TILE_SIZE, TILE_SIZE))

                self.tiles["wall"] = slice_tile(0, 1)
                self.tiles["platform"] = slice_tile(3, 1)
                self.tiles["exit"] = slice_tile(2, 1)
                self.loaded = True
            except Exception as e:
                print(f"Failed to process tilesheet image: {e}")

# --- UI BUTTON CLASS ---
class Button:
    def __init__(self, x, y, width, height, text, action_id):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.action_id = action_id
        self.is_hovered = False

    def update(self, mouse_pos):
        self.is_hovered = self.rect.collidepoint(mouse_pos)

    def draw(self, surface, font):
        bg_color = COLOR_BTN_HOVER if self.is_hovered else COLOR_BTN
        pygame.draw.rect(surface, bg_color, self.rect, border_radius=8)
        pygame.draw.rect(surface, COLOR_BTN_BORDER, self.rect, width=2, border_radius=8)

        txt_surf = render_outlined_text(font, self.text, COLOR_TEXT, COLOR_OUTLINE, outline_width=2)
        txt_rect = txt_surf.get_rect(center=self.rect.center)
        surface.blit(txt_surf, txt_rect)

# --- CAMERA CLASS ---
class Camera:
    def __init__(self, width, height):
        self.rect = pygame.Rect(0, 0, width, height)

    def update(self, target_x, target_y):
        x = target_x - SCREEN_WIDTH // 2
        y = target_y - SCREEN_HEIGHT // 2
        x = max(0, min(x, WORLD_WIDTH - SCREEN_WIDTH))
        y = max(0, min(y, WORLD_HEIGHT - SCREEN_HEIGHT))
        self.rect.x = int(x)
        self.rect.y = int(y)

    def apply_rect(self, rect):
        return rect.move(-self.rect.x, -self.rect.y)

    def apply_pos(self, pos):
        return (int(pos[0] - self.rect.x), int(pos[1] - self.rect.y))

# --- PLAYER CLASS ---
class BallPlayer:
    def __init__(self, x, y):
        self.radius = 14
        self.reset(x, y)

    def reset(self, x, y):
        self.x = float(x)
        self.y = float(y)
        self.vx = 0.0
        self.vy = 0.0
        self.is_grounded = False
        self.in_water = False
        self.standing_platform = None

    @property
    def rect(self):
        return pygame.Rect(
            int(self.x - self.radius),
            int(self.y - self.radius),
            self.radius * 2,
            self.radius * 2
        )

    def update(self, keys, walls, moving_platforms, waters):
        self.in_water = any(self.rect.colliderect(w) for w in waters)

        gravity = 0.25 if self.in_water else 0.65
        accel = 0.4 if self.in_water else 0.8
        max_speed = 3.5 if self.in_water else 7.0
        friction = 0.85 if self.in_water else 0.92

        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.vx -= accel
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.vx += accel

        self.vx *= friction
        self.vx = max(-max_speed, min(max_speed, self.vx))

        if keys[pygame.K_SPACE] or keys[pygame.K_UP] or keys[pygame.K_w]:
            if self.is_grounded:
                self.vy = -11.5
                self.is_grounded = False
                self.standing_platform = None
            elif self.in_water:
                self.vy = -4.5

        self.vy += gravity
        if self.in_water:
            self.vy = min(self.vy, 3.0)

        # 1. Horizontal Movement & Carrying Logic
        platform_vx = self.standing_platform.vx if self.standing_platform else 0.0
        total_vx = self.vx + platform_vx

        self.x += total_vx
        player_r = self.rect

        # Check side collisions with walls
        for solid in walls:
            if player_r.colliderect(solid):
                if total_vx > 0:
                    self.x = solid.left - self.radius
                elif total_vx < 0:
                    self.x = solid.right + self.radius
                self.vx = 0

        # Check side collisions with platforms other than the one currently standing on
        for platform in moving_platforms:
            if platform != self.standing_platform and player_r.colliderect(platform.rect):
                if total_vx > 0:
                    self.x = platform.rect.left - self.radius
                elif total_vx < 0:
                    self.x = platform.rect.right + self.radius
                self.vx = 0

        # 2. Vertical Movement & Landing Logic
        self.y += self.vy
        player_r = self.rect
        self.is_grounded = False
        self.standing_platform = None

        # Moving platform landing
        for platform in moving_platforms:
            solid = platform.rect
            if player_r.colliderect(solid):
                if self.vy >= 0 and (player_r.bottom - self.vy) <= solid.top + 10:
                    self.y = solid.top - self.radius
                    self.vy = 0
                    self.is_grounded = True
                    self.standing_platform = platform
                elif self.vy < 0 and (player_r.top - self.vy) >= solid.bottom - 8:
                    self.y = solid.bottom + self.radius
                    self.vy = 0

        # Static wall landing
        for solid in walls:
            if player_r.colliderect(solid):
                if self.vy > 0:
                    self.y = solid.top - self.radius
                    self.vy = 0
                    self.is_grounded = True
                elif self.vy < 0:
                    self.y = solid.bottom + self.radius
                    self.vy = 0

    def draw(self, surface, camera):
        pos = camera.apply_pos((self.x, self.y))
        pygame.draw.circle(surface, COLOR_PLAYER, pos, self.radius)
        pygame.draw.circle(
            surface,
            (255, 255, 200),
            (pos[0] - self.radius // 3, pos[1] - self.radius // 3),
            self.radius // 3
        )

# --- MOVING PLATFORM CLASS ---
class MovingPlatform:
    def __init__(self, x, y, width, height, travel_distance=240, speed=2):
        self.start_x = x
        self.rect = pygame.Rect(x, y, width, height)
        self.travel_distance = travel_distance
        self.speed = speed
        self.direction = 1

    @property
    def vx(self):
        return self.speed * self.direction

    def update(self, walls):
        self.rect.x += int(self.vx)

        for wall in walls:
            if self.rect.colliderect(wall):
                if self.direction > 0:
                    self.rect.right = wall.left
                elif self.direction < 0:
                    self.rect.left = wall.right
                self.direction *= -1
                break

        if abs(self.rect.x - self.start_x) >= self.travel_distance:
            self.direction *= -1

    def draw(self, surface, camera, tileset):
        draw_rect = camera.apply_rect(self.rect)
        if tileset and tileset.loaded:
            scaled_tile = pygame.transform.scale(tileset.tiles["platform"], (TILE_SIZE, self.rect.height))
            for offset_x in range(0, self.rect.width, TILE_SIZE):
                surface.blit(scaled_tile, (draw_rect.x + offset_x, draw_rect.y))
        else:
            pygame.draw.rect(surface, COLOR_PLATFORM_FALLBACK, draw_rect, border_radius=4)

# --- FULL 100x60 LEVEL GENERATOR ---
def ensure_levels_file_exists(filename="levels.json"):
    if os.path.exists(filename):
        return

    levels = []
    for level_idx in range(10):
        grid = [["." for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]

        # Perimeter walls (100x60 border)
        for c in range(GRID_WIDTH):
            grid[0][c] = "#"
            grid[GRID_HEIGHT - 1][c] = "#"
        for r in range(GRID_HEIGHT):
            grid[r][0] = "#"
            grid[r][GRID_WIDTH - 1] = "#"

        # Start and Exit locations grid-aligned
        grid[5][3] = "P"
        grid[55][96] = "E"

        # Multi-level horizontal platforms
        floors = [8, 18, 28, 38, 48, 56]
        for f_idx, f_y in enumerate(floors):
            is_reverse = (f_idx % 2 == 1)
            gap_start = 4 if is_reverse else 82
            gap_end = 18 if is_reverse else 96

            for c in range(1, GRID_WIDTH - 1):
                if not (gap_start <= c <= gap_end):
                    grid[f_y][c] = "#"

        # Populate features
        for f_y in floors:
            for c in range(8, 82, 10):
                choice = random.choice(["spikes", "water", "moving", "clear"])
                if choice == "spikes":
                    for s_x in range(c, c + 3):
                        grid[f_y - 1][s_x] = "S"
                elif choice == "water":
                    for w_y in range(f_y - 2, f_y):
                        for w_x in range(c, c + 5):
                            grid[w_y][w_x] = "W"
                elif choice == "moving":
                    for clear_x in range(c, c + 4):
                        grid[f_y][clear_x] = "."
                    grid[f_y][c] = "M"

        levels.append(["".join(row) for row in grid])

    with open(filename, "w") as f:
        json.dump({"levels": levels}, f, indent=2)

# --- GAME ENGINE ---
class BounceGame:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Sci-Fi Bounce Ball - 100x60 World")
        self.clock = pygame.time.Clock()
        self.font_large = pygame.font.SysFont("Arial", 42, bold=True)
        self.font_medium = pygame.font.SysFont("Arial", 26, bold=True)
        self.font_small = pygame.font.SysFont("Arial", 18, bold=True)

        self.tileset = SciFiTileset("sci-fy1.png")
        self.camera = Camera(SCREEN_WIDTH, SCREEN_HEIGHT)

        ensure_levels_file_exists("levels.json")
        self.levels = self.load_levels("levels.json")

        self.state = STATE_MENU
        self.current_level_idx = 0
        self.water_anim_timer = 0.0

        self.player = None
        self.walls = []
        self.spikes = []
        self.waters = []
        self.moving_platforms = []
        self.exit_rect = None

        self.init_menus()
        self.parse_level(self.current_level_idx)

    def load_levels(self, filepath):
        with open(filepath, "r") as f:
            data = json.load(f)
            return data["levels"]

    def init_menus(self):
        cx = SCREEN_WIDTH // 2
        self.main_buttons = [
            Button(cx - 110, 280, 220, 50, "PLAY GAME", "play"),
            Button(cx - 110, 350, 220, 50, "SELECT LEVEL", "level_select"),
            Button(cx - 110, 420, 220, 50, "QUIT", "quit")
        ]

        self.level_buttons = []
        for i in range(10):
            row = i // 5
            col = i % 5
            bx = cx - 270 + (col * 110)
            by = 300 + (row * 80)
            self.level_buttons.append(Button(bx, by, 90, 60, f"Lvl {i+1}", f"lvl_{i}"))

        self.level_back_btn = Button(cx - 100, 500, 200, 45, "BACK TO MENU", "back_to_menu")

        self.pause_buttons = [
            Button(cx - 110, 250, 220, 45, "RESUME", "resume"),
            Button(cx - 110, 310, 220, 45, "RESTART LEVEL", "restart"),
            Button(cx - 110, 370, 220, 45, "LEVEL SELECT", "level_select"),
            Button(cx - 110, 430, 220, 45, "MAIN MENU", "back_to_menu"),
            Button(cx - 110, 490, 220, 45, "QUIT", "quit")
        ]

    def parse_level(self, idx):
        self.walls.clear()
        self.spikes.clear()
        self.waters.clear()
        self.moving_platforms.clear()

        grid = self.levels[idx]
        start_pos = (160, 160)

        for row_idx, row in enumerate(grid):
            for col_idx, char in enumerate(row):
                x = col_idx * TILE_SIZE
                y = row_idx * TILE_SIZE
                rect = pygame.Rect(x, y, TILE_SIZE, TILE_SIZE)

                if char == "#":
                    self.walls.append(rect)
                elif char == "S":
                    self.spikes.append(rect)
                elif char == "W":
                    self.waters.append(rect)
                elif char == "M":
                    self.moving_platforms.append(
                        MovingPlatform(x, y, TILE_SIZE * 2, TILE_SIZE // 2)
                    )
                elif char == "P":
                    start_pos = (x + TILE_SIZE // 2, y + TILE_SIZE // 2)
                elif char == "E":
                    self.exit_rect = rect

        if self.player is None:
            self.player = BallPlayer(start_pos[0], start_pos[1])
        else:
            self.player.reset(start_pos[0], start_pos[1])

    def trigger_action(self, action_id):
        if action_id == "play":
            self.state = STATE_GAME
        elif action_id == "level_select":
            self.state = STATE_LEVEL_SELECT
        elif action_id == "back_to_menu":
            self.state = STATE_MENU
        elif action_id == "resume":
            self.state = STATE_GAME
        elif action_id == "restart":
            self.parse_level(self.current_level_idx)
            self.state = STATE_GAME
        elif action_id.startswith("lvl_"):
            lvl_num = int(action_id.split("_")[1])
            self.current_level_idx = lvl_num
            self.parse_level(self.current_level_idx)
            self.state = STATE_GAME
        elif action_id == "quit":
            pygame.quit()
            sys.exit()

    def handle_events(self):
        mouse_pos = pygame.mouse.get_pos()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE or event.key == pygame.K_p:
                    if self.state == STATE_GAME:
                        self.state = STATE_PAUSE
                    elif self.state == STATE_PAUSE:
                        self.state = STATE_GAME
                    elif self.state == STATE_LEVEL_SELECT:
                        self.state = STATE_MENU

                elif event.key == pygame.K_r and self.state == STATE_GAME:
                    self.parse_level(self.current_level_idx)

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.state == STATE_MENU:
                    for btn in self.main_buttons:
                        if btn.rect.collidepoint(mouse_pos):
                            self.trigger_action(btn.action_id)
                elif self.state == STATE_LEVEL_SELECT:
                    for btn in self.level_buttons:
                        if btn.rect.collidepoint(mouse_pos):
                            self.trigger_action(btn.action_id)
                    if self.level_back_btn.rect.collidepoint(mouse_pos):
                        self.trigger_action(self.level_back_btn.action_id)
                elif self.state == STATE_PAUSE:
                    for btn in self.pause_buttons:
                        if btn.rect.collidepoint(mouse_pos):
                            self.trigger_action(btn.action_id)

        if self.state == STATE_MENU:
            for btn in self.main_buttons:
                btn.update(mouse_pos)
        elif self.state == STATE_LEVEL_SELECT:
            for btn in self.level_buttons:
                btn.update(mouse_pos)
            self.level_back_btn.update(mouse_pos)
        elif self.state == STATE_PAUSE:
            for btn in self.pause_buttons:
                btn.update(mouse_pos)

        return True

    def update(self):
        if self.state != STATE_GAME:
            return

        self.water_anim_timer += 0.08
        keys = pygame.key.get_pressed()

        for platform in self.moving_platforms:
            platform.update(self.walls)

        self.player.update(keys, self.walls, self.moving_platforms, self.waters)
        self.camera.update(self.player.x, self.player.y)

        # Spike collision
        for spike in self.spikes:
            spike_box = spike.inflate(-12, -12)
            if self.player.rect.colliderect(spike_box):
                self.parse_level(self.current_level_idx)
                return

        # Exit portal collision
        if self.exit_rect and self.player.rect.colliderect(self.exit_rect.inflate(-8, -8)):
            self.current_level_idx += 1
            if self.current_level_idx >= len(self.levels):
                self.current_level_idx = 0
            self.parse_level(self.current_level_idx)

    def draw_world(self):
        self.screen.fill(COLOR_BG)

        # 1. DRAW WATER
        water_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        for w in self.waters:
            if self.camera.rect.colliderect(w):
                r = self.camera.apply_rect(w)
                pygame.draw.rect(water_surface, COLOR_WATER_DEEP, r)
                wave_offset = math.sin(self.water_anim_timer + r.x * 0.05) * 3
                surf_rect = pygame.Rect(r.x, r.y + int(wave_offset), r.width, 6)
                pygame.draw.rect(water_surface, COLOR_WATER_SURFACE, surf_rect)

        self.screen.blit(water_surface, (0, 0))

        # 2. DRAW WALLS
        for wall in self.walls:
            if self.camera.rect.colliderect(wall):
                r = self.camera.apply_rect(wall)
                if self.tileset.loaded:
                    self.screen.blit(self.tileset.tiles["wall"], r)
                else:
                    pygame.draw.rect(self.screen, COLOR_WALL_FALLBACK, r, border_radius=3)

        # 3. DRAW SPIKES
        for spike in self.spikes:
            if self.camera.rect.colliderect(spike):
                r = self.camera.apply_rect(spike)
                pts = [(r.left, r.bottom), (r.centerx, r.top + 2), (r.right, r.bottom)]
                pygame.draw.polygon(self.screen, COLOR_SPIKE_FILL, pts)
                pygame.draw.polygon(self.screen, COLOR_SPIKE_OUTLINE, pts, width=2)

        # 4. DRAW MOVING PLATFORMS
        for platform in self.moving_platforms:
            if self.camera.rect.colliderect(platform.rect):
                platform.draw(self.screen, self.camera, self.tileset)

        # 5. DRAW EXIT PORTAL
        if self.exit_rect and self.camera.rect.colliderect(self.exit_rect):
            r = self.camera.apply_rect(self.exit_rect)
            if self.tileset.loaded:
                self.screen.blit(self.tileset.tiles["exit"], r)
            else:
                pygame.draw.ellipse(self.screen, COLOR_EXIT_FALLBACK, r)

        # 6. DRAW PLAYER BALL
        self.player.draw(self.screen, self.camera)

        # 7. DRAW HUD
        hud_str = f"Level: {self.current_level_idx + 1} / {len(self.levels)}   |   P / ESC: Pause   |   R: Restart"
        hud_surf = render_outlined_text(self.font_small, hud_str, COLOR_TEXT, COLOR_OUTLINE, outline_width=2)
        self.screen.blit(hud_surf, (16, 12))

    def draw(self):
        if self.state in (STATE_GAME, STATE_PAUSE):
            self.draw_world()

        if self.state == STATE_MENU:
            self.screen.fill(COLOR_BG)
            title_surf = render_outlined_text(self.font_large, "BOUNCE BALL: SCI-FI", COLOR_TEXT, COLOR_OUTLINE, outline_width=2)
            title_rect = title_surf.get_rect(center=(SCREEN_WIDTH // 2, 160))
            self.screen.blit(title_surf, title_rect)

            for btn in self.main_buttons:
                btn.draw(self.screen, self.font_medium)

        elif self.state == STATE_LEVEL_SELECT:
            self.screen.fill(COLOR_BG)
            title_surf = render_outlined_text(self.font_large, "SELECT LEVEL", COLOR_TEXT, COLOR_OUTLINE, outline_width=2)
            title_rect = title_surf.get_rect(center=(SCREEN_WIDTH // 2, 160))
            self.screen.blit(title_surf, title_rect)

            for btn in self.level_buttons:
                btn.draw(self.screen, self.font_medium)
            self.level_back_btn.draw(self.screen, self.font_medium)

        elif self.state == STATE_PAUSE:
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((10, 12, 18, 180))
            self.screen.blit(overlay, (0, 0))

            panel_rect = pygame.Rect(SCREEN_WIDTH // 2 - 160, 140, 320, 440)
            pygame.draw.rect(self.screen, (25, 30, 45), panel_rect, border_radius=12)
            pygame.draw.rect(self.screen, COLOR_BTN_BORDER, panel_rect, width=2, border_radius=12)

            title_surf = render_outlined_text(self.font_large, "PAUSED", COLOR_TEXT, COLOR_OUTLINE, outline_width=2)
            title_rect = title_surf.get_rect(center=(SCREEN_WIDTH // 2, 190))
            self.screen.blit(title_surf, title_rect)

            for btn in self.pause_buttons:
                btn.draw(self.screen, self.font_medium)

        pygame.display.flip()

    def run(self):
        running = True
        while running:
            running = self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(FPS)

        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    game = BounceGame()
    game.run()