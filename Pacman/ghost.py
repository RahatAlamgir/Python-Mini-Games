import math
import random
import pygame

from map import (
    CELL_SIZE, HUD_HEIGHT, GHOST_SPEED_NORMAL, GHOST_SPEED_SCARED, GHOST_SPEED_EYES,
    SPRITE_GHOSTS, SPRITE_SCARED, SPRITE_FLASH,
    SPRITE_EYES_LEFT, SPRITE_EYES_RIGHT, SPRITE_EYES_UP, SPRITE_EYES_DOWN
)

class Ghost:
    def __init__(self, gx, gy, ghost_id, spawn_delay=0):
        self.start_gx = gx
        self.start_gy = gy
        self.ghost_id = ghost_id
        self.spawn_delay = spawn_delay
        self.colors = [(255, 0, 0), (255, 184, 255), (0, 255, 255), (255, 184, 82)]
        self.reset()

    def reset(self):
        self.x = self.start_gx * CELL_SIZE + CELL_SIZE // 2
        self.y = self.start_gy * CELL_SIZE + CELL_SIZE // 2
        self.dir_x, self.dir_y = 0, 0
        self.state = "NORMAL"
        self.delay_timer = self.spawn_delay * 60
        self.is_inside_house = True

    def update(self, maze, pacman, blinky_pos, is_frightened, global_mode, ghost_house_tiles, gate_tiles):
        # 1. Handle initial exit spawn delay
        if self.delay_timer > 0:
            self.delay_timer -= 1
            return

        grid_h = len(maze)
        grid_w = len(maze[0]) if grid_h > 0 else 0
        curr_gx = int(self.x) // CELL_SIZE
        curr_gy = int(self.y) // CELL_SIZE

        # 2. State transition
        if is_frightened and self.state == "NORMAL":
            self.state = "SCARED"
        elif not is_frightened and self.state == "SCARED":
            self.state = "NORMAL"

        speed = GHOST_SPEED_EYES if self.state == "EYES" else (GHOST_SPEED_SCARED if self.state == "SCARED" else GHOST_SPEED_NORMAL)

        # 3. Check if EYES returned home
        if self.state == "EYES":
            if abs(self.x - (self.start_gx * CELL_SIZE + CELL_SIZE // 2)) < 4 and \
               abs(self.y - (self.start_gy * CELL_SIZE + CELL_SIZE // 2)) < 4:
                self.state = "NORMAL"
                self.is_inside_house = True

        # --- 4. EXPLICIT GHOST HOUSE EXIT MECHANIC ---
        if self.is_inside_house and self.state != "EYES":
            gate_gx, gate_gy = gate_tiles[0] if gate_tiles else (grid_w // 2, grid_h // 2)
            
            target_pixel_x = gate_gx * CELL_SIZE + CELL_SIZE // 2
            target_pixel_y = (gate_gy - 1) * CELL_SIZE + CELL_SIZE // 2

            # Step A: Align horizontally with gate center
            if abs(self.x - target_pixel_x) > speed:
                self.dir_x = 1 if self.x < target_pixel_x else -1
                self.dir_y = 0
            else:
                # Step B: Snap X center and force straight UP movement out through the gate
                self.x = target_pixel_x
                self.dir_x = 0
                self.dir_y = -1

            self.x += self.dir_x * speed
            self.y += self.dir_y * speed

            # Step C: Complete exit once fully above the gate tile
            if self.y <= target_pixel_y:
                self.y = target_pixel_y
                self.is_inside_house = False

            return

        # --- 5. STANDARD MAZE NAVIGATION ---
        center_x = curr_gx * CELL_SIZE + CELL_SIZE // 2
        center_y = curr_gy * CELL_SIZE + CELL_SIZE // 2

        if abs(self.x - center_x) < speed and abs(self.y - center_y) < speed:
            self.x, self.y = center_x, center_y
            target = self.get_target(pacman, blinky_pos, global_mode, grid_w, grid_h)
            can_pass_gate = (self.state == "EYES")
            self.choose_direction(maze, target, grid_w, grid_h, allow_gates=can_pass_gate)

        self.x += self.dir_x * speed
        self.y += self.dir_y * speed

        # Screen Wrap
        if self.x < 0:
            self.x = (grid_w - 1) * CELL_SIZE
        elif self.x >= grid_w * CELL_SIZE:
            self.x = 0

    def get_target(self, pacman, blinky_pos, global_mode, grid_w, grid_h):
        if self.state == "EYES":
            return (self.start_gx, self.start_gy)

        px, py = pacman.get_grid_pos()

        if self.state == "SCARED":
            gx, gy = int(self.x) // CELL_SIZE, int(self.y) // CELL_SIZE
            escape_x = gx + (gx - px)
            escape_y = gy + (gy - py)
            return (max(0, min(grid_w - 1, escape_x)), max(0, min(grid_h - 1, escape_y)))

        if global_mode == "SCATTER":
            corners = [(grid_w - 1, 0), (0, 0), (grid_w - 1, grid_h - 1), (0, grid_h - 1)]
            return corners[self.ghost_id % 4]

        # Chase Targets
        if self.ghost_id == 0:  # Blinky
            return (px, py)
        elif self.ghost_id == 1:  # Pinky
            return (px + pacman.dir_x * 4, py + pacman.dir_y * 4)
        elif self.ghost_id == 2:  # Inky
            bx, by = blinky_pos
            tx, ty = px + pacman.dir_x * 2, py + pacman.dir_y * 2
            return (2 * tx - bx, 2 * ty - by)
        else:  # Clyde
            gx, gy = int(self.x) // CELL_SIZE, int(self.y) // CELL_SIZE
            dist = math.hypot(gx - px, gy - py)
            return (px, py) if dist > 8 else (0, grid_h - 1)

    def choose_direction(self, maze, target, grid_w, grid_h, allow_gates=False):
        curr_gx = int(self.x) // CELL_SIZE
        curr_gy = int(self.y) // CELL_SIZE
        opposite = (-self.dir_x, -self.dir_y)

        valid_dirs = []
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            if (dx, dy) == opposite and (self.dir_x != 0 or self.dir_y != 0):
                continue
            nx, ny = curr_gx + dx, curr_gy + dy

            if nx < 0 or nx >= grid_w:
                valid_dirs.append((dx, dy))
                continue

            if 0 <= ny < grid_h:
                tile = maze[ny][nx]
                if tile != "W" and (tile != "G" or allow_gates):
                    valid_dirs.append((dx, dy))

        if not valid_dirs:
            valid_dirs = [opposite] if opposite != (0, 0) else [(0, -1), (0, 1), (-1, 0), (1, 0)]

        best_dir = valid_dirs[0]
        tx, ty = target

        if self.state == "SCARED":
            max_dist = -1
            random.shuffle(valid_dirs)
            for dx, dy in valid_dirs:
                nx, ny = curr_gx + dx, curr_gy + dy
                dist = math.hypot(nx - tx, ny - ty)
                if dist > max_dist:
                    max_dist = dist
                    best_dir = (dx, dy)
        else:
            min_dist = float("inf")
            for dx, dy in valid_dirs:
                nx, ny = curr_gx + dx, curr_gy + dy
                dist = math.hypot(nx - tx, ny - ty)
                if dist < min_dist:
                    min_dist = dist
                    best_dir = (dx, dy)

        self.dir_x, self.dir_y = best_dir

    def draw(self, surface, scared_timer):
        gx = int(self.x) - CELL_SIZE // 2
        gy = int(self.y) - CELL_SIZE // 2 + HUD_HEIGHT

        if self.state == "SCARED":
            sprites = SPRITE_FLASH if (scared_timer < 120 and (scared_timer // 15) % 2 == 0) else SPRITE_SCARED
            sprite = sprites[0] if sprites and sprites[0] else None
            if sprite:
                surface.blit(sprite, (gx, gy))
            else:
                pygame.draw.circle(surface, (0, 0, 255), (int(self.x), int(self.y) + HUD_HEIGHT), CELL_SIZE // 2)
        elif self.state == "EYES":
            sprite = SPRITE_EYES_LEFT if self.dir_x == -1 else (
                     SPRITE_EYES_RIGHT if self.dir_x == 1 else (
                     SPRITE_EYES_UP if self.dir_y == -1 else SPRITE_EYES_DOWN))
            if sprite:
                surface.blit(sprite, (gx, gy))
            else:
                pygame.draw.circle(surface, (255, 255, 255), (int(self.x), int(self.y) + HUD_HEIGHT), 4)
        else:
            sprites = SPRITE_GHOSTS[self.ghost_id % 4]
            sprite = sprites[0] if sprites and sprites[0] else None
            if sprite:
                surface.blit(sprite, (gx, gy))
            else:
                pygame.draw.circle(surface, self.colors[self.ghost_id % 4], (int(self.x), int(self.y) + HUD_HEIGHT), CELL_SIZE // 2)