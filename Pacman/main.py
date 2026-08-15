import json
import math
import os
import random
import sys
import numpy as np
import pygame

from map import (
    screen, HUD_HEIGHT, CELL_SIZE,
    COLOR_BG, COLOR_DOT, COLOR_POWER, COLOR_TEXT, COLOR_PACMAN, SAVE_FILE,
    ALL_MAPS, PACMAN_SPEED, draw_maze,
    SPRITE_PACMAN_LEFT, SPRITE_PACMAN_UP, SPRITE_PACMAN_DOWN, SPRITE_PACMAN_RIGHT,
    SPRITES_FRUIT
)
from ghost import Ghost
from Ui import Button, FloatingScore, font_ui, font_large

def generate_tone(frequency, duration, volume=0.2, wave_type="sine"):
    sample_rate = 44100
    n_samples = int(sample_rate * duration)
    t = np.linspace(0, duration, n_samples, False)
    wave = np.sin(2 * np.pi * frequency * t) if wave_type == "sine" else np.sign(np.sin(2 * np.pi * frequency * t))
    audio = wave * volume * 32767
    return pygame.mixer.Sound(audio.astype(np.int16).tobytes())

snd_waka = generate_tone(440, 0.05, volume=0.15, wave_type="square")
snd_power = generate_tone(880, 0.2, volume=0.25, wave_type="square")
snd_eat_ghost = generate_tone(600, 0.2, volume=0.3, wave_type="sine")
snd_eat_fruit = generate_tone(1000, 0.3, volume=0.3, wave_type="square")
snd_death = generate_tone(150, 0.4, volume=0.3, wave_type="square")

clock = pygame.time.Clock()

class Pacman:
    def __init__(self, gx, gy):
        self.start_gx, self.start_gy = gx, gy
        self.reset()

    def reset(self):
        self.x = self.start_gx * CELL_SIZE + CELL_SIZE // 2
        self.y = self.start_gy * CELL_SIZE + CELL_SIZE // 2
        self.dir_x, self.dir_y = 0, 0
        self.next_dir = (0, 0)
        self.anim_frame = 0
        self.anim_timer = 0

    def update(self, maze, grid_w, grid_h, ghost_house_tiles):
        center_x = (int(self.x) // CELL_SIZE) * CELL_SIZE + CELL_SIZE // 2
        center_y = (int(self.y) // CELL_SIZE) * CELL_SIZE + CELL_SIZE // 2

        if abs(self.x - center_x) < 2 and abs(self.y - center_y) < 2 and self.next_dir != (0, 0):
            gx = int(self.x) // CELL_SIZE + self.next_dir[0]
            gy = int(self.y) // CELL_SIZE + self.next_dir[1]
            if 0 <= gx < grid_w and 0 <= gy < grid_h and maze[gy][gx] != "W" and (gx, gy) not in ghost_house_tiles:
                self.x, self.y = center_x, center_y
                self.dir_x, self.dir_y = self.next_dir
                self.next_dir = (0, 0)

        next_x = self.x + self.dir_x * PACMAN_SPEED
        next_y = self.y + self.dir_y * PACMAN_SPEED
        check_gx = int(next_x + self.dir_x * 8) // CELL_SIZE
        check_gy = int(next_y + self.dir_y * 8) // CELL_SIZE

        if check_gx < 0:
            self.x = (grid_w - 1) * CELL_SIZE
            return
        elif check_gx >= grid_w:
            self.x = 0
            return

        if 0 <= check_gy < grid_h and maze[check_gy][check_gx] != "W" and (check_gx, check_gy) not in ghost_house_tiles:
            self.x, self.y = next_x, next_y
            self.anim_timer += 1
            if self.anim_timer % 4 == 0:
                self.anim_frame = (self.anim_frame + 1) % 3

    def get_grid_pos(self):
        return int(self.x) // CELL_SIZE, int(self.y) // CELL_SIZE

    def draw(self, surface):
        px, py = self.x - CELL_SIZE // 2, self.y - CELL_SIZE // 2 + HUD_HEIGHT
        sprites = (SPRITE_PACMAN_LEFT if self.dir_x == -1 else 
                  (SPRITE_PACMAN_UP if self.dir_y == -1 else 
                  (SPRITE_PACMAN_DOWN if self.dir_y == 1 else SPRITE_PACMAN_RIGHT)))
        sprite = sprites[self.anim_frame] if sprites and sprites[self.anim_frame] else None
        if sprite:
            surface.blit(sprite, (px, py))
        else:
            pygame.draw.circle(surface, COLOR_PACMAN, (int(self.x), int(self.y) + HUD_HEIGHT), CELL_SIZE // 2 - 2)

class Game:
    def __init__(self):
        self.state = "MENU"
        self.high_score = self.load_high_score()
        self.floating_scores = []
        self.current_level = 0
        self.gate_tiles = []
        self.ghost_house_tiles = set()
        self.wall_color = (33, 33, 255)
        self.setup_buttons()
        self.reset_game()

    def setup_buttons(self):
        sw = self.screen_width if hasattr(self, 'screen_width') else ALL_MAPS[0]["layout"][0].__len__() * CELL_SIZE
        sh = self.screen_height if hasattr(self, 'screen_height') else ALL_MAPS[0]["layout"].__len__() * CELL_SIZE + HUD_HEIGHT

        cx = sw // 2 - 100
        cy = sh // 2 - 40
        
        self.btn_new_game = Button(cx, cy, 200, 40, "NEW GAME", self.start_new_game)
        self.btn_select_lvl = Button(cx, cy + 50, 200, 40, "SELECT LEVEL", lambda: setattr(self, 'state', 'LEVEL_SELECT'))
        self.btn_exit = Button(cx, cy + 100, 200, 40, "EXIT GAME", sys.exit)
        self.menu_buttons = [self.btn_new_game, self.btn_select_lvl, self.btn_exit]

        self.lvl_buttons = []
        for idx in range(len(ALL_MAPS)):
            b_y = cy - 30 + (idx * 45)
            self.lvl_buttons.append(Button(cx, b_y, 200, 40, f"MAP {idx + 1}", lambda i=idx: self.start_level(i)))
        
        back_y = cy - 30 + (len(ALL_MAPS) * 45)
        self.lvl_buttons.append(Button(cx, back_y, 200, 40, "BACK", lambda: setattr(self, 'state', 'MENU')))

        self.pause_buttons = [
            Button(cx, cy, 200, 40, "RESUME", lambda: setattr(self, 'state', 'PLAYING')),
            Button(cx, cy + 50, 200, 40, "MAIN MENU", lambda: setattr(self, 'state', 'MENU')),
            Button(cx, cy + 100, 200, 40, "EXIT GAME", sys.exit)
        ]

    def start_new_game(self):
        self.current_level = 0
        self.reset_game()
        self.state = "PLAYING"

    def start_level(self, lvl):
        self.current_level = lvl
        self.reset_game()
        self.state = "PLAYING"

    def parse_maze(self):
        level_entry = ALL_MAPS[self.current_level]
        layout = level_entry["layout"]
        self.wall_color = level_entry["color"]

        self.grid_height = len(layout)
        self.grid_width = max(len(row) for row in layout)
        
        self.screen_width = self.grid_width * CELL_SIZE
        self.screen_height = self.grid_height * CELL_SIZE + HUD_HEIGHT
        
        global screen
        screen = pygame.display.set_mode((self.screen_width, self.screen_height))

        self.pac_start = (1, 1)
        self.ghost_starts = [None] * 4
        self.ghost_house_tiles = set()
        self.valid_food_locs = []
        self.gate_tiles = []

        for y, row in enumerate(layout):
            for x, char in enumerate(row):
                if char == "P":
                    self.pac_start = (x, y)
                elif char == "G":
                    self.ghost_house_tiles.add((x, y))
                    self.gate_tiles.append((x, y))
                elif char in ("1", "2", "3", "4"):
                    idx = int(char) - 1
                    self.ghost_starts[idx] = (x, y)
                    self.ghost_house_tiles.add((x, y))
                elif char == "M":
                    self.ghost_house_tiles.add((x, y))
                elif char in (".", "o"):
                    self.valid_food_locs.append((x, y))

        if self.gate_tiles:
            gate_y = self.gate_tiles[0][1]
            for gy in range(gate_y, min(self.grid_height, gate_y + 4)):
                for gx in range(self.grid_width):
                    if gx < len(layout[gy]) and layout[gy][gx] in (" ", "1", "2", "3", "4", "G", "M") and 8 < gx < 19:
                        self.ghost_house_tiles.add((gx, gy))

        if self.gate_tiles:
            gate_center_x = self.gate_tiles[0][0]
            gate_center_y = self.gate_tiles[0][1]
        else:
            gate_center_x = self.grid_width // 2
            gate_center_y = self.grid_height // 2
        
        for i in range(4):
            if self.ghost_starts[i] is None:
                spawn_x = gate_center_x + (i % 2)
                spawn_y = gate_center_y + 2
                self.ghost_starts[i] = (spawn_x, spawn_y)
                self.ghost_house_tiles.add((spawn_x, spawn_y))

        self.setup_buttons()

    def load_high_score(self):
        if os.path.exists(SAVE_FILE):
            try:
                with open(SAVE_FILE, "r") as f: return json.load(f).get("high_score", 0)
            except Exception: return 0
        return 0

    def save_high_score(self):
        with open(SAVE_FILE, "w") as f: json.dump({"high_score": self.high_score}, f)

    def reset_game(self):
        self.score = 0
        self.lives = 3
        self.scared_timer = 0
        self.ghost_eat_score = 200
        self.game_timer = 180 * 60
        self.food_spawn_timer = 40 * 60
        self.fruit_active = False
        self.fruit_timer = 0
        self.fruit_type = 0
        self.mode_timer = 0
        self.floating_scores.clear()
        self.parse_maze()
        self.fruit_pos = (self.grid_width // 2, self.grid_height // 2)
        self.reset_level()

    def reset_level(self):
        level_entry = ALL_MAPS[self.current_level]
        layout = level_entry["layout"]
        self.wall_color = level_entry["color"]
        
        self.maze = [list(row) for row in layout]
        self.total_dots = sum(row.count(".") + row.count("o") for row in self.maze)
        self.dots_eaten = 0
        self.pacman = Pacman(*self.pac_start)

        delays = [0, 5, 10, 15]
        self.ghosts = [
            Ghost(pos[0], pos[1], idx, delays[idx]) 
            for idx, pos in enumerate(self.ghost_starts)
        ]

    def advance_level(self):
        self.current_level += 1
        if self.current_level >= len(ALL_MAPS):
            self.state = "WIN"
        else:
            self.parse_maze()
            self.reset_level()
            self.scared_timer = 0
            self.ghost_eat_score = 200

    def spawn_random_food(self):
        if self.valid_food_locs:
            self.fruit_active = True
            self.fruit_timer = 600
            self.fruit_type = random.randint(0, 3)
            self.fruit_pos = random.choice(self.valid_food_locs)

    def handle_input(self, event):
        if self.state == "MENU":
            for btn in self.menu_buttons: btn.handle_event(event)
        elif self.state == "LEVEL_SELECT":
            for btn in self.lvl_buttons: btn.handle_event(event)
        elif self.state == "PAUSED":
            for btn in self.pause_buttons: btn.handle_event(event)

        if event.type == pygame.KEYDOWN:
            if self.state in ("GAMEOVER", "WIN") and event.key == pygame.K_SPACE:
                self.start_new_game()
            elif event.key == pygame.K_r and self.state == "PLAYING":
                self.reset_game()
            elif event.key in (pygame.K_p, pygame.K_ESCAPE):
                if self.state == "PLAYING": self.state = "PAUSED"
                elif self.state == "PAUSED": self.state = "PLAYING"

            if self.state == "PLAYING":
                if event.key in (pygame.K_LEFT, pygame.K_a): self.pacman.next_dir = (-1, 0)
                elif event.key in (pygame.K_RIGHT, pygame.K_d): self.pacman.next_dir = (1, 0)
                elif event.key in (pygame.K_UP, pygame.K_w): self.pacman.next_dir = (0, -1)
                elif event.key in (pygame.K_DOWN, pygame.K_s): self.pacman.next_dir = (0, 1)

    def update(self):
        if self.state != "PLAYING": return

        self.game_timer -= 1
        if self.game_timer <= 0:
            self.state = "GAMEOVER"
            return

        self.food_spawn_timer -= 1
        if self.food_spawn_timer <= 0:
            self.spawn_random_food()
            self.food_spawn_timer = 40 * 60

        if self.fruit_active:
            self.fruit_timer -= 1
            if self.fruit_timer <= 0: self.fruit_active = False

        if self.scared_timer > 0:
            self.scared_timer -= 1
            if self.scared_timer == 0: self.ghost_eat_score = 200

        for popup in self.floating_scores[:]:
            popup.update()
            if popup.timer <= 0: self.floating_scores.remove(popup)

        self.mode_timer += 1
        ghost_mode = "SCATTER" if (self.mode_timer // 60) % 20 < 7 else "CHASE"

        self.pacman.update(self.maze, self.grid_width, self.grid_height, self.ghost_house_tiles)

        gx, gy = self.pacman.get_grid_pos()
        if 0 <= gx < self.grid_width and 0 <= gy < self.grid_height:
            char = self.maze[gy][gx]
            if char == ".":
                self.maze[gy][gx] = " "
                self.score += 10
                self.dots_eaten += 1
                snd_waka.play()
            elif char == "o":
                self.maze[gy][gx] = " "
                self.score += 50
                self.dots_eaten += 1
                self.scared_timer = 360
                self.ghost_eat_score = 200
                snd_power.play()

        if self.dots_eaten >= self.total_dots:
            self.advance_level()

        if self.fruit_active and (gx, gy) == self.fruit_pos:
            self.fruit_active = False
            fruit_values = [100, 300, 500, 700]
            val = fruit_values[self.fruit_type]
            self.score += val
            self.floating_scores.append(FloatingScore(self.pacman.x, self.pacman.y, val))
            snd_eat_fruit.play()

        if self.score > self.high_score:
            self.high_score = self.score
            self.save_high_score()

        blinky_pos = (self.ghosts[0].x, self.ghosts[0].y) if self.ghosts else (0, 0)
        is_frig = self.scared_timer > 0

        for ghost in self.ghosts:
            ghost.update(self.maze, self.pacman, blinky_pos, is_frig, ghost_mode, self.ghost_house_tiles, self.gate_tiles)
            dist = math.hypot(ghost.x - self.pacman.x, ghost.y - self.pacman.y)
            if dist < 12:
                if ghost.state == "SCARED":
                    ghost.state = "EYES"
                    pts = self.ghost_eat_score
                    self.score += pts
                    self.floating_scores.append(FloatingScore(ghost.x, ghost.y, pts))
                    self.ghost_eat_score = min(1600, self.ghost_eat_score * 2)
                    snd_eat_ghost.play()
                elif ghost.state == "NORMAL":
                    snd_death.play()
                    self.lives -= 1
                    if self.lives <= 0: self.state = "GAMEOVER"
                    else:
                        self.pacman.reset()
                        for g in self.ghosts: g.reset()

    def draw(self):
        screen.fill(COLOR_BG)

        pygame.draw.rect(screen, (15, 15, 25), (0, 0, self.screen_width, HUD_HEIGHT))
        screen.blit(font_ui.render(f"SCORE: {self.score}", True, COLOR_TEXT), (15, 18))
        screen.blit(font_ui.render(f"MAP: {self.current_level + 1}/{len(ALL_MAPS)}", True, COLOR_PACMAN), (120, 18))

        secs_left = max(0, self.game_timer // 60)
        m, s = divmod(secs_left, 60)
        time_color = (255, 50, 50) if secs_left < 30 else COLOR_TEXT
        screen.blit(font_ui.render(f"TIME: {m:02d}:{s:02d}", True, time_color), (220, 18))

        for i in range(self.lives):
            pygame.draw.circle(screen, COLOR_PACMAN, (self.screen_width - 25 - (i * 18), 28), 6)

        # Draw Arcade Outlined Maze Walls using Level-Specific RGB Color
        draw_maze(screen, self.maze, self.wall_color)

        # Draw Dots & Power Pellets
        for y, row in enumerate(self.maze):
            for x, char in enumerate(row):
                cx, cy = x * CELL_SIZE + CELL_SIZE // 2, y * CELL_SIZE + CELL_SIZE // 2 + HUD_HEIGHT
                if char == ".": pygame.draw.circle(screen, COLOR_DOT, (cx, cy), 2.5)
                elif char == "o": pygame.draw.circle(screen, COLOR_POWER, (cx, cy), 6)

        if self.fruit_active:
            fx, fy = self.fruit_pos[0] * CELL_SIZE, self.fruit_pos[1] * CELL_SIZE + HUD_HEIGHT
            sprite = SPRITES_FRUIT[self.fruit_type] if SPRITES_FRUIT[self.fruit_type] else None
            if sprite: screen.blit(sprite, (fx, fy))
            else: pygame.draw.circle(screen, (255, 0, 80), (fx + CELL_SIZE // 2, fy + CELL_SIZE // 2), 6)

        self.pacman.draw(screen)
        for ghost in self.ghosts: ghost.draw(screen, self.scared_timer)
        for popup in self.floating_scores: popup.draw(screen)

        if self.state == "MENU":
            self.draw_overlay("PAC-MAN ARCADE", [f"HIGH SCORE: {self.high_score}"], buttons=self.menu_buttons)
        elif self.state == "LEVEL_SELECT":
            self.draw_overlay("SELECT LEVEL", [], buttons=self.lvl_buttons)
        elif self.state == "PAUSED":
            self.draw_overlay("GAME PAUSED", [], buttons=self.pause_buttons)
        elif self.state == "GAMEOVER":
            self.draw_overlay("GAME OVER", [f"Final Score: {self.score}", f"High Score: {self.high_score}", "", "Press SPACE for Main Menu"])
        elif self.state == "WIN":
            self.draw_overlay("YOU WIN!", ["All Maps Cleared!", f"Final Score: {self.score}", "", "Press SPACE for Main Menu"])

        pygame.display.flip()

    def draw_overlay(self, title, lines, buttons=None):
        overlay = pygame.Surface((self.screen_width, self.screen_height - HUD_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 230))
        screen.blit(overlay, (0, HUD_HEIGHT))

        t_surf = font_large.render(title, True, COLOR_PACMAN)
        screen.blit(t_surf, t_surf.get_rect(center=(self.screen_width // 2, HUD_HEIGHT + 70)))

        y_off = HUD_HEIGHT + 130
        for line in lines:
            line_surf = font_ui.render(line, True, COLOR_TEXT)
            screen.blit(line_surf, line_surf.get_rect(center=(self.screen_width // 2, y_off)))
            y_off += 28

        if buttons:
            for btn in buttons:
                btn.draw(screen)

game = Game()
while True:
    clock.tick(60)
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
        game.handle_input(event)

    game.update()
    game.draw()