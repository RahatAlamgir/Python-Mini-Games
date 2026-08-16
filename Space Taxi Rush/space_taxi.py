import json
import math
import os
import random
import sys
import time
import numpy as np
import pygame

# --- Initialize Pygame & Audio ---
pygame.init()
pygame.mixer.init(frequency=44100, size=-16, channels=1, buffer=512)

# Config
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
GRAVITY = 0.08
THRUST_POWER = 0.22
ROTATION_SPEED = 4
MAX_LANDING_SPEED = 3.5
MAX_LANDING_ANGLE = 25

# Colors
COLOR_BG = (12, 14, 22)
COLOR_GRID = (20, 24, 38)
COLOR_HEADER = (22, 26, 40)
COLOR_TEXT = (230, 235, 245)
COLOR_MUTED = (110, 120, 140)
COLOR_TAXI = (255, 210, 0)
COLOR_THRUST = (255, 80, 20)
COLOR_PASSENGER = (0, 255, 163)
COLOR_PAD = (0, 200, 255)
COLOR_PAD_TARGET = (255, 50, 100)

screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Space Taxi Rush")
clock = pygame.time.Clock()

font_ui = pygame.font.SysFont("Segoe UI", 18, bold=True)
font_large = pygame.font.SysFont("Segoe UI", 36, bold=True)
font_title = pygame.font.SysFont("Segoe UI", 48, bold=True)
font_sub = pygame.font.SysFont("Segoe UI", 16)

SAVE_FILE = "highscore.json"


# --- Sound Effects ---
def generate_tone(frequency, duration, volume=0.2, wave_type="sine"):
    sample_rate = 44100
    n_samples = int(sample_rate * duration)
    t = np.linspace(0, duration, n_samples, False)

    if wave_type == "sine":
        wave = np.sin(2 * np.pi * frequency * t)
    elif wave_type == "square":
        wave = np.sign(np.sin(2 * np.pi * frequency * t))
    elif wave_type == "noise":
        wave = np.random.uniform(-1, 1, n_samples)

    envelope = np.linspace(1, 0, n_samples)
    audio = wave * envelope * volume * 32767
    return pygame.mixer.Sound(audio.astype(np.int16).tobytes())


snd_thrust = generate_tone(120, 0.05, volume=0.15, wave_type="noise")
snd_land = generate_tone(523.25, 0.15, volume=0.25)
snd_pickup = generate_tone(880, 0.2, volume=0.25, wave_type="square")
snd_crash = generate_tone(100, 0.4, volume=0.3, wave_type="noise")


class LandingPad:

    def __init__(self, id_num, x, y, width=90):
        self.id = id_num
        self.rect = pygame.Rect(x, y, width, 12)

    def draw(self, surface, is_pickup=False, is_dropoff=False):
        color = COLOR_PAD
        if is_pickup:
            color = COLOR_PASSENGER
        elif is_dropoff:
            color = COLOR_PAD_TARGET

        pygame.draw.rect(surface, color, self.rect, border_radius=3)
        lbl = font_sub.render(f"PAD {self.id}", True, (0, 0, 0))
        surface.blit(lbl, lbl.get_rect(center=self.rect.center))


class Taxi:

    def __init__(self, x, y):
        self.reset(x, y)

    def reset(self, x, y):
        self.pos = [float(x), float(y)]
        self.vel = [0.0, 0.0]
        self.angle = 0.0
        self.fuel = 100.0
        self.is_thrusting = False
        self.has_passenger = False

    def update(self):
        self.vel[1] += GRAVITY
        self.pos[0] += self.vel[0]
        self.pos[1] += self.vel[1]

    def thrust(self):
        if self.fuel > 0:
            rad = math.radians(self.angle)
            self.vel[0] += math.sin(rad) * THRUST_POWER
            self.vel[1] -= math.cos(rad) * THRUST_POWER
            self.fuel = max(0.0, self.fuel - 0.12)
            self.is_thrusting = True

    def rotate(self, direction):
        self.angle += direction * ROTATION_SPEED
        self.angle %= 360

    def draw(self, surface):
        cx, cy = self.pos

        if self.is_thrusting:
            rad = math.radians(self.angle)
            fx = cx - math.sin(rad) * 16
            fy = cy + math.cos(rad) * 16
            pygame.draw.circle(
                surface, COLOR_THRUST, (int(fx), int(fy)), random.randint(4, 7)
            )

        rad = math.radians(self.angle)
        pt_nose = (cx + math.sin(rad) * 14, cy - math.cos(rad) * 14)
        pt_left = (
            cx + math.sin(rad + 2.5) * 12,
            cy - math.cos(rad + 2.5) * 12,
        )
        pt_right = (
            cx + math.sin(rad - 2.5) * 12,
            cy - math.cos(rad - 2.5) * 12,
        )

        pygame.draw.polygon(surface, COLOR_TAXI, [pt_nose, pt_left, pt_right])
        pygame.draw.polygon(
            surface, (0, 0, 0), [pt_nose, pt_left, pt_right], width=2
        )

        if self.has_passenger:
            pygame.draw.circle(surface, COLOR_PASSENGER, (int(cx), int(cy)), 3)


class Game:

    def __init__(self):
        self.state = "MENU"  # MENU, PLAYING, PAUSED, GAMEOVER
        self.best_score, self.best_time = self.load_records()
        self.reset_game()

    def load_records(self):
        if os.path.exists(SAVE_FILE):
            try:
                with open(SAVE_FILE, "r") as f:
                    data = json.load(f)
                    return data.get("best_score", 0), data.get("best_time", 0.0)
            except Exception:
                return 0, 0.0
        return 0, 0.0

    def save_records(self):
        data = {"best_score": self.best_score, "best_time": self.best_time}
        with open(SAVE_FILE, "w") as f:
            json.dump(data, f)

    def reset_game(self):
        self.score = 0
        self.fares_completed = 0
        self.start_time = time.time()
        self.alive_time = 0.0
        self.msg = ""
        self.msg_timer = 0

        self.pads = [
            LandingPad(1, 60, 220),
            LandingPad(2, 650, 180),
            LandingPad(3, 150, 480),
            LandingPad(4, 520, 440),
        ]

        self.walls = [
            pygame.Rect(0, 60, 20, 540),
            pygame.Rect(780, 60, 20, 540),
            pygame.Rect(0, 580, 800, 20),
            pygame.Rect(340, 250, 120, 20),
            pygame.Rect(380, 270, 40, 150),
        ]

        self.taxi = Taxi(105, 180)
        self.spawn_passenger()

    def spawn_passenger(self):
        self.pickup_pad = random.choice(self.pads)
        available_dropoffs = [p for p in self.pads if p != self.pickup_pad]
        self.dropoff_pad = random.choice(available_dropoffs)
        self.taxi.has_passenger = False

    def toggle_pause(self):
        if self.state == "PLAYING":
            self.state = "PAUSED"
            self.pause_start = time.time()
        elif self.state == "PAUSED":
            self.state = "PLAYING"
            self.start_time += time.time() - self.pause_start

    def handle_input(self, event):
        if event.type == pygame.KEYDOWN:
            if self.state == "MENU" and event.key == pygame.K_SPACE:
                self.reset_game()
                self.state = "PLAYING"
            elif self.state == "GAMEOVER" and event.key == pygame.K_SPACE:
                self.reset_game()
                self.state = "PLAYING"
            elif event.key == pygame.K_r:  # In-game Manual Restart
                self.reset_game()
                self.state = "PLAYING"
            elif event.key in (pygame.K_p, pygame.K_ESCAPE):
                if self.state in ("PLAYING", "PAUSED"):
                    self.toggle_pause()

    def update(self):
        if self.state != "PLAYING":
            return

        self.alive_time = time.time() - self.start_time
        keys = pygame.key.get_pressed()
        self.taxi.is_thrusting = False

        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.taxi.rotate(-1)
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.taxi.rotate(1)
        if keys[pygame.K_UP] or keys[pygame.K_w] or keys[pygame.K_SPACE]:
            self.taxi.thrust()

        if self.msg_timer > 0:
            self.msg_timer -= 1

        self.taxi.update()
        self.check_collisions()

    def check_collisions(self):
        # Map Screen Boundary Check (Out of Bounds)
        tx, ty = self.taxi.pos
        if (
            tx < 0
            or tx > SCREEN_WIDTH
            or ty < 60  # Header bar boundary
            or ty > SCREEN_HEIGHT
        ):
            self.trigger_crash("FLEW OUT OF BOUNDS!")
            return

        taxi_rect = pygame.Rect(tx - 10, ty - 10, 20, 20)

        # Wall Obstacle Collisions
        for wall in self.walls:
            if taxi_rect.colliderect(wall):
                self.trigger_crash("CRASHED INTO OBSTACLE!")
                return

        # Landing Pad Collisions
        for pad in self.pads:
            if taxi_rect.colliderect(pad.rect):
                speed = math.hypot(self.taxi.vel[0], self.taxi.vel[1])
                angle_diff = min(
                    abs(self.taxi.angle),
                    abs(360 - self.taxi.angle),
                )

                if speed <= MAX_LANDING_SPEED and angle_diff <= MAX_LANDING_ANGLE:
                    self.taxi.vel = [0.0, 0.0]
                    self.taxi.pos[1] = pad.rect.top - 10
                    self.taxi.angle = 0
                    self.taxi.fuel = min(100.0, self.taxi.fuel + 0.4)

                    if pad == self.pickup_pad and not self.taxi.has_passenger:
                        self.taxi.has_passenger = True
                        snd_pickup.play()
                        self.msg = f"PASSENGER BOARDED! GO TO PAD {self.dropoff_pad.id}"
                        self.msg_timer = 120
                    elif pad == self.dropoff_pad and self.taxi.has_passenger:
                        snd_land.play()
                        self.score += 250 + int(self.taxi.fuel)
                        self.fares_completed += 1
                        self.msg = "FARE DELIVERED! +250 PTS"
                        self.msg_timer = 120
                        self.spawn_passenger()
                else:
                    self.trigger_crash("HARD IMPACT ON PAD!")
                return

    def trigger_crash(self, reason):
        snd_crash.play()
        self.state = "GAMEOVER"
        self.msg = reason

        updated = False
        if self.score > self.best_score:
            self.best_score = self.score
            updated = True
        if self.alive_time > self.best_time:
            self.best_time = self.alive_time
            updated = True
        if updated:
            self.save_records()

    def draw_bg(self):
        screen.fill(COLOR_BG)
        for x in range(0, SCREEN_WIDTH, 40):
            pygame.draw.line(screen, COLOR_GRID, (x, 60), (x, SCREEN_HEIGHT))
        for y in range(60, SCREEN_HEIGHT, 40):
            pygame.draw.line(screen, COLOR_GRID, (0, y), (SCREEN_WIDTH, y))

    def draw_hud(self):
        pygame.draw.rect(screen, COLOR_HEADER, (0, 0, SCREEN_WIDTH, 60))
        pygame.draw.line(screen, COLOR_GRID, (0, 60), (SCREEN_WIDTH, 60), 2)

        screen.blit(
            font_ui.render(f"SCORE: {self.score}", True, COLOR_TEXT), (20, 18)
        )
        screen.blit(
            font_ui.render(
                f"TIME: {self.alive_time:.1f}s", True, COLOR_PASSENGER
            ),
            (160, 18),
        )

        fuel_color = (
            (0, 255, 150) if self.taxi.fuel > 30 else (255, 50, 50)
        )
        pygame.draw.rect(screen, (40, 45, 60), (310, 22, 140, 16), border_radius=4)
        pygame.draw.rect(
            screen,
            fuel_color,
            (310, 22, int(1.4 * self.taxi.fuel), 16),
            border_radius=4,
        )
        screen.blit(font_sub.render("FUEL", True, COLOR_TEXT), (270, 20))

        speed = math.hypot(self.taxi.vel[0], self.taxi.vel[1])
        spd_color = (
            COLOR_TEXT if speed <= MAX_LANDING_SPEED else (255, 80, 80)
        )
        screen.blit(
            font_ui.render(f"SPD: {speed:.1f}", True, spd_color),
            (SCREEN_WIDTH - 120, 18),
        )

    def draw_world(self):
        for wall in self.walls:
            pygame.draw.rect(screen, (35, 42, 60), wall, border_radius=4)
            pygame.draw.rect(
                screen, (60, 70, 95), wall, width=2, border_radius=4
            )

        for pad in self.pads:
            is_pk = pad == self.pickup_pad and not self.taxi.has_passenger
            is_dp = pad == self.dropoff_pad and self.taxi.has_passenger
            pad.draw(screen, is_pickup=is_pk, is_dropoff=is_dp)

            if is_pk:
                px, py = pad.rect.centerx, pad.rect.top - 8
                pygame.draw.circle(screen, COLOR_PASSENGER, (px, py - 6), 4)
                pygame.draw.line(
                    screen, COLOR_PASSENGER, (px, py - 2), (px, py + 6), 2
                )

        if self.state != "GAMEOVER":
            self.taxi.draw(screen)

    def draw(self):
        self.draw_bg()
        self.draw_hud()
        self.draw_world()

        if self.msg_timer > 0 and self.state == "PLAYING":
            txt = font_sub.render(self.msg, True, COLOR_TAXI)
            screen.blit(txt, txt.get_rect(center=(SCREEN_WIDTH // 2, 85)))

        if self.state == "MENU":
            self.draw_overlay(
                "SPACE TAXI RUSH",
                [
                    "Fly: Arrow Keys / WASD | Pause: P / ESC",
                    "Quick Restart: Press R at any time",
                    "",
                    f"BEST SCORE: {self.best_score} PTS",
                    f"LONGEST SURVIVAL: {self.best_time:.1f} SEC",
                    "",
                    "Press SPACE to Start Flying",
                ],
            )

        elif self.state == "PAUSED":
            self.draw_overlay(
                "GAME PAUSED",
                [
                    "Press P or ESC to Resume Flying",
                    "Press R to Restart Run",
                ],
            )

        elif self.state == "GAMEOVER":
            self.draw_overlay(
                "CAB DESTROYED!",
                [
                    self.msg,
                    f"Final Score: {self.score} | Alive Time: {self.alive_time:.1f}s",
                    "",
                    f"BEST SCORE: {self.best_score} | BEST TIME: {self.best_time:.1f}s",
                    "",
                    "Press SPACE to Restart",
                ],
            )

        pygame.display.flip()

    def draw_overlay(self, title, lines):
        overlay = pygame.Surface(
            (SCREEN_WIDTH, SCREEN_HEIGHT - 60), pygame.SRCALPHA
        )
        overlay.fill((10, 12, 20, 230))
        screen.blit(overlay, (0, 60))

        t_surface = font_title.render(title, True, COLOR_TAXI)
        screen.blit(
            t_surface,
            t_surface.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 110)),
        )

        y_offset = SCREEN_HEIGHT // 2 - 30
        for line in lines:
            line_surface = font_ui.render(line, True, COLOR_TEXT)
            screen.blit(
                line_surface,
                line_surface.get_rect(center=(SCREEN_WIDTH // 2, y_offset)),
            )
            y_offset += 32


# --- Game Loop ---
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