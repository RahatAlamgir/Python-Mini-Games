import json
import math
import os
import random
import sys
import numpy as np
import pygame

# --- Initialize Pygame & Audio ---
pygame.init()
pygame.mixer.init(frequency=44100, size=-16, channels=1, buffer=512)

# Config
SCREEN_WIDTH = 760
SCREEN_HEIGHT = 600
PADDLE_WIDTH = 110
PADDLE_HEIGHT = 16
BALL_RADIUS = 7

BRICK_COLS = 16
BRICK_ROWS = 10
BRICK_HEIGHT = 14
BRICK_PADDING = 3
BRICK_OFFSET_TOP = 75
BRICK_OFFSET_LEFT = 15

# Colors
COLOR_BG = (15, 17, 26)
COLOR_HEADER = (25, 28, 42)
COLOR_PADDLE = (0, 230, 255)
COLOR_BALL = (255, 255, 255)
COLOR_TEXT = (240, 240, 240)
COLOR_MUTED = (120, 130, 150)
COLOR_ACCENT = (0, 255, 150)

BRICK_COLORS = {
    1: (0, 255, 150),   # Green
    2: (255, 200, 0),   # Yellow
    3: (255, 50, 90),   # Red
    -1: (120, 120, 140) # Silver
}

POWERUP_COLORS = {
    "2X": (0, 255, 255),  # Cyan
    "SLOW": (0, 255, 100), # Green
    "FAST": (255, 50, 50)  # Red
}

HIGHSCORE_FILE = "highscore_dxball.txt"
LEVELS_FILE = "levels.json"

screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("DX-Ball - Advanced Edition")
clock = pygame.time.Clock()

font_ui = pygame.font.SysFont("Segoe UI", 18, bold=True)
font_large = pygame.font.SysFont("Segoe UI", 36, bold=True)
font_sub = pygame.font.SysFont("Segoe UI", 16)


# --- High Score Storage ---
def load_high_score():
    if os.path.exists(HIGHSCORE_FILE):
        try:
            with open(HIGHSCORE_FILE, "r") as f:
                return int(f.read().strip())
        except (ValueError, IOError):
            return 0
    return 0


def save_high_score(score):
    try:
        with open(HIGHSCORE_FILE, "w") as f:
            f.write(str(score))
    except IOError:
        pass


# --- Synthesized Audio ---
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


snd_paddle = generate_tone(440, 0.05)
snd_brick = generate_tone(660, 0.08)
snd_powerup = generate_tone(880, 0.12, wave_type="square")
snd_lose = generate_tone(150, 0.3, wave_type="noise")


class Ball:

    def __init__(self, x, y, vx, vy, attached=False):
        self.pos = [float(x), float(y)]
        self.speed = [float(vx), float(vy)]
        self.attached = attached

    def get_rect(self):
        return pygame.Rect(
            self.pos[0] - BALL_RADIUS,
            self.pos[1] - BALL_RADIUS,
            BALL_RADIUS * 2,
            BALL_RADIUS * 2,
        )


class PowerUp:

    def __init__(self, x, y, p_type):
        self.rect = pygame.Rect(x - 15, y - 10, 30, 20)
        self.type = p_type  # '2X', 'SLOW', 'FAST'
        self.speed = 3

    def update(self):
        self.rect.y += self.speed

    def draw(self, surface):
        color = POWERUP_COLORS.get(self.type, (255, 255, 255))
        pygame.draw.rect(surface, color, self.rect, border_radius=5)
        txt = font_sub.render(self.type, True, (0, 0, 0))
        surface.blit(txt, txt.get_rect(center=self.rect.center))


class Brick:

    def __init__(self, rect, hits):
        self.rect = rect
        self.hits = hits

    def draw(self, surface):
        color = BRICK_COLORS.get(self.hits, (255, 255, 255))
        pygame.draw.rect(surface, color, self.rect, border_radius=3)
        pygame.draw.rect(
            surface, (255, 255, 255, 40), self.rect, width=1, border_radius=3
        )


class Game:

    def __init__(self):
        self.state = "MENU"  # MENU, LEVEL_SELECT, GAME, PAUSE, GAMEOVER, WIN
        self.high_score = load_high_score()
        self.json_levels = self.load_json_levels()
        self.reset_game()

    def load_json_levels(self):
        if not os.path.exists(LEVELS_FILE):
            print(f"Error: {LEVELS_FILE} missing.")
            sys.exit()
        with open(LEVELS_FILE, "r") as f:
            return json.load(f).get("levels", [])

    def reset_game(self):
        self.score = 0
        self.lives = 3
        self.current_level_idx = 0
        self.powerups = []
        self.paddle = pygame.Rect(
            (SCREEN_WIDTH - PADDLE_WIDTH) // 2,
            SCREEN_HEIGHT - 40,
            PADDLE_WIDTH,
            PADDLE_HEIGHT,
        )
        self.load_level(self.current_level_idx)

    def load_level(self, idx):
        self.bricks = []
        self.powerups = []
        self.balls = []

        # Attach main ball
        self.balls.append(
            Ball(self.paddle.centerx, self.paddle.top - BALL_RADIUS, 5, -5, True)
        )

        level_data = self.json_levels[idx]["layout"]
        brick_width = (
            SCREEN_WIDTH
            - (BRICK_OFFSET_LEFT * 2)
            - (BRICK_PADDING * (BRICK_COLS - 1))
        ) // BRICK_COLS

        for r, row in enumerate(level_data):
            for c, hits in enumerate(row):
                if hits != 0:
                    x = BRICK_OFFSET_LEFT + c * (brick_width + BRICK_PADDING)
                    y = BRICK_OFFSET_TOP + r * (BRICK_HEIGHT + BRICK_PADDING)
                    self.bricks.append(
                        Brick(pygame.Rect(x, y, brick_width, BRICK_HEIGHT), hits)
                    )

    def launch_balls(self):
        for ball in self.balls:
            if ball.attached:
                ball.attached = False

    def handle_input(self, event):
        if self.state == "MENU":
            pygame.mouse.set_visible(True)
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                if 280 <= mx <= 480 and 220 <= my <= 260:
                    self.reset_game()
                    self.state = "GAME"
                elif 280 <= mx <= 480 and 280 <= my <= 320:
                    self.state = "LEVEL_SELECT"
                elif 280 <= mx <= 480 and 340 <= my <= 380:
                    pygame.quit()
                    sys.exit()

        elif self.state == "LEVEL_SELECT":
            pygame.mouse.set_visible(True)
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                for i in range(len(self.json_levels)):
                    rx = 180 + (i % 5) * 80
                    ry = 200 + (i // 5) * 80
                    if rx <= mx <= rx + 60 and ry <= my <= ry + 60:
                        self.reset_game()
                        self.current_level_idx = i
                        self.load_level(i)
                        self.state = "GAME"

                # Back Button
                if 280 <= mx <= 480 and 420 <= my <= 460:
                    self.state = "MENU"

        elif self.state == "GAME":
            pygame.mouse.set_visible(False)
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_p, pygame.K_ESCAPE):
                    self.state = "PAUSE"
                elif event.key == pygame.K_SPACE:
                    self.launch_balls()

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self.launch_balls()

        elif self.state == "PAUSE":
            pygame.mouse.set_visible(True)
            if event.type == pygame.KEYDOWN and event.key in (
                pygame.K_p,
                pygame.K_ESCAPE,
            ):
                self.state = "GAME"

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                if 280 <= mx <= 480 and 240 <= my <= 280:
                    self.state = "GAME"
                elif 280 <= mx <= 480 and 300 <= my <= 340:
                    self.state = "MENU"

        elif self.state in ("GAMEOVER", "WIN"):
            pygame.mouse.set_visible(True)
            if (
                event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
            ) or (
                event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE
            ):
                self.state = "MENU"

    def update(self):
        if self.state != "GAME":
            return

        # Paddle Tracking Mouse
        mouse_x = pygame.mouse.get_pos()[0]
        self.paddle.centerx = mouse_x
        self.paddle.x = max(0, min(SCREEN_WIDTH - PADDLE_WIDTH, self.paddle.x))

        # Update Powerups
        for p in self.powerups[:]:
            p.update()
            if p.rect.colliderect(self.paddle):
                snd_powerup.play()
                if p.type == "2X":
                    new_balls = []
                    for b in self.balls:
                        new_balls.append(
                            Ball(b.pos[0], b.pos[1], -b.speed[0], b.speed[1])
                        )
                    self.balls.extend(new_balls)
                elif p.type == "SLOW":
                    for b in self.balls:
                        b.speed[0] *= 0.75
                        b.speed[1] *= 0.75
                elif p.type == "FAST":
                    for b in self.balls:
                        b.speed[0] *= 1.25
                        b.speed[1] *= 1.25
                self.powerups.remove(p)
            elif p.rect.y > SCREEN_HEIGHT:
                self.powerups.remove(p)

        # Update Balls
        for ball in self.balls[:]:
            if ball.attached:
                ball.pos[0] = self.paddle.centerx
                ball.pos[1] = self.paddle.top - BALL_RADIUS
                continue

            ball.pos[0] += ball.speed[0]
            ball.pos[1] += ball.speed[1]
            ball_rect = ball.get_rect()

            # Walls
            if ball.pos[0] - BALL_RADIUS <= 0 or ball.pos[0] + BALL_RADIUS >= SCREEN_WIDTH:
                ball.speed[0] *= -1
                snd_paddle.play()
            if ball.pos[1] - BALL_RADIUS <= 60:
                ball.speed[1] *= -1
                snd_paddle.play()

            # Bottom Death
            if ball.pos[1] + BALL_RADIUS >= SCREEN_HEIGHT:
                self.balls.remove(ball)
                continue

            # Paddle Collision
            if ball_rect.colliderect(self.paddle) and ball.speed[1] > 0:
                offset = (ball_rect.centerx - self.paddle.centerx) / (
                    PADDLE_WIDTH / 2
                )
                angle = offset * (math.pi / 3)
                speed = math.hypot(ball.speed[0], ball.speed[1])
                ball.speed[0] = speed * math.sin(angle)
                ball.speed[1] = -speed * math.cos(angle)
                snd_paddle.play()

            # Bricks Collision
            for brick in self.bricks[:]:
                if ball_rect.colliderect(brick.rect):
                    ball.speed[1] *= -1
                    if brick.hits != -1:
                        brick.hits -= 1
                        self.score += 10
                        if brick.hits <= 0:
                            self.bricks.remove(brick)
                            # Spawn PowerUp Chance (20%)
                            if random.random() < 0.20:
                                ptype = random.choice(["2X", "SLOW", "FAST"])
                                self.powerups.append(
                                    PowerUp(brick.rect.centerx, brick.rect.centery, ptype)
                                )
                        snd_brick.play()

                    if self.score > self.high_score:
                        self.high_score = self.score
                        save_high_score(self.high_score)
                    break

        # Check Ball Loss
        if not self.balls:
            self.lives -= 1
            snd_lose.play()
            if self.lives <= 0:
                self.state = "GAMEOVER"
            else:
                self.balls.append(
                    Ball(self.paddle.centerx, self.paddle.top - BALL_RADIUS, 5, -5, True)
                )

        # Check Level Clear
        destructible = any(b.hits != -1 for b in self.bricks)
        if not destructible:
            if self.current_level_idx + 1 < len(self.json_levels):
                self.current_level_idx += 1
                self.load_level(self.current_level_idx)
            else:
                self.state = "WIN"

    def draw_button(self, text, rect, hover_col=(0, 230, 255), bg_col=(35, 40, 60)):
        mx, my = pygame.mouse.get_pos()
        r = pygame.Rect(rect)
        color = hover_col if r.collidepoint((mx, my)) else bg_col
        pygame.draw.rect(screen, color, r, border_radius=8)
        txt = font_ui.render(text, True, COLOR_TEXT)
        screen.blit(txt, txt.get_rect(center=r.center))

    def draw(self):
        screen.fill(COLOR_BG)

        if self.state == "MENU":
            t = font_large.render("DX-BALL", True, COLOR_PADDLE)
            screen.blit(t, t.get_rect(center=(SCREEN_WIDTH // 2, 120)))
            self.draw_button("NEW GAME", (280, 220, 200, 40))
            self.draw_button("SELECT LEVEL", (280, 280, 200, 40))
            self.draw_button("EXIT GAME", (280, 340, 200, 40))

        elif self.state == "LEVEL_SELECT":
            t = font_large.render("SELECT LEVEL", True, COLOR_TEXT)
            screen.blit(t, t.get_rect(center=(SCREEN_WIDTH // 2, 100)))

            for i in range(len(self.json_levels)):
                rx = 180 + (i % 5) * 80
                ry = 200 + (i // 5) * 80
                self.draw_button(f"{i+1}", (rx, ry, 60, 60))

            self.draw_button("BACK", (280, 420, 200, 40))

        elif self.state in ("GAME", "PAUSE", "GAMEOVER", "WIN"):
            # Header
            pygame.draw.rect(screen, COLOR_HEADER, (0, 0, SCREEN_WIDTH, 60))
            screen.blit(font_ui.render(f"SCORE: {self.score}", True, COLOR_TEXT), (20, 18))
            screen.blit(
                font_ui.render(
                    f"LEVEL: {self.current_level_idx + 1}/{len(self.json_levels)}",
                    True,
                    COLOR_PADDLE,
                ),
                (180, 18),
            )
            screen.blit(
                font_ui.render(f"BEST: {self.high_score}", True, COLOR_MUTED),
                (340, 18),
            )
            screen.blit(
                font_ui.render(f"LIVES: {self.lives}", True, COLOR_TEXT),
                (SCREEN_WIDTH - 110, 18),
            )

            # Bricks, Powerups, Paddle, Balls
            for b in self.bricks:
                b.draw(screen)
            for p in self.powerups:
                p.draw(screen)

            pygame.draw.rect(screen, COLOR_PADDLE, self.paddle, border_radius=6)
            for ball in self.balls:
                pygame.draw.circle(
                    screen, COLOR_BALL, (int(ball.pos[0]), int(ball.pos[1])), BALL_RADIUS
                )

            # Overlays
            if self.state == "PAUSE":
                ov = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT - 60), pygame.SRCALPHA)
                ov.fill((10, 12, 20, 200))
                screen.blit(ov, (0, 60))
                t = font_large.render("PAUSED", True, COLOR_TEXT)
                screen.blit(t, t.get_rect(center=(SCREEN_WIDTH // 2, 160)))
                self.draw_button("RESUME", (280, 240, 200, 40))
                self.draw_button("MAIN MENU", (280, 300, 200, 40))

            elif self.state in ("GAMEOVER", "WIN"):
                ov = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT - 60), pygame.SRCALPHA)
                ov.fill((10, 12, 20, 220))
                screen.blit(ov, (0, 60))

                title = "VICTORY!" if self.state == "WIN" else "GAME OVER"
                color = (0, 255, 150) if self.state == "WIN" else (255, 50, 90)

                t_render = font_large.render(title, True, color)
                sub_render = font_sub.render(
                    "Click to return to Main Menu", True, COLOR_TEXT
                )
                screen.blit(
                    t_render,
                    t_render.get_rect(
                        center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 15)
                    ),
                )
                screen.blit(
                    sub_render,
                    sub_render.get_rect(
                        center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 25)
                    ),
                )

        pygame.display.flip()


# --- Main Loop ---
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