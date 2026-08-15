import os
import random
import sys
import numpy as np
import pygame

# --- Initialize Pygame & Audio ---
pygame.init()
pygame.mixer.init(frequency=44100, size=-16, channels=1, buffer=512)

# --- Config & Colors ---
GRID_SIZE = 28
GRID_WIDTH = 24
GRID_HEIGHT = 18
SCREEN_WIDTH = GRID_WIDTH * GRID_SIZE
SCREEN_HEIGHT = GRID_HEIGHT * GRID_SIZE + 70

COLOR_BG = (15, 17, 26)
COLOR_GRID = (24, 27, 40)
COLOR_HEADER = (22, 25, 38)
COLOR_TEXT = (230, 235, 245)
COLOR_MUTED = (110, 120, 140)

# Neon Palette
COLOR_SNAKE_HEAD = (0, 255, 163)
COLOR_SNAKE_BODY = (0, 200, 135)
COLOR_SNAKE_GLOW = (0, 255, 163, 40)
COLOR_EYE = (15, 17, 26)

COLOR_FOOD = (255, 50, 85)
COLOR_GOLDEN = (255, 210, 0)
COLOR_SLOW = (160, 60, 255)

HIGHSCORE_FILE = "highscore.txt"

screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Sleek Modern Snake")
clock = pygame.time.Clock()

font_score = pygame.font.SysFont("Segoe UI", 20, bold=True)
font_large = pygame.font.SysFont("Segoe UI", 36, bold=True)
font_sub = pygame.font.SysFont("Segoe UI", 16)


# --- Persistent High Score ---
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


# --- Procedural Sound Effects ---
def generate_tone(frequency, duration, volume=0.25, wave_type="sine"):
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


snd_eat = generate_tone(587.33, 0.08, volume=0.2)
snd_powerup = generate_tone(880, 0.15, volume=0.25, wave_type="square")
snd_gameover = generate_tone(130, 0.35, volume=0.3, wave_type="noise")


class Food:

    def __init__(self, x, y, food_type="normal"):
        self.x = x
        self.y = y
        self.type = food_type
        self.timer = 280 if food_type != "normal" else None

    def update(self):
        if self.timer is not None:
            self.timer -= 1
            return self.timer > 0
        return True


class SnakeGame:

    def __init__(self):
        self.high_score = load_high_score()
        self.reset()

    def reset(self):
        self.direction = (1, 0)
        self.next_direction = (1, 0)
        self.snake = [(5, 9), (4, 9), (3, 9)]
        self.score = 0
        self.game_over = False
        self.move_timer = 0
        self.base_delay = 110
        self.slow_timer = 0
        self.msg = ""
        self.msg_timer = 0

        self.foods = []
        self.spawn_food("normal")

    def spawn_food(self, food_type="normal"):
        while True:
            x = random.randint(0, GRID_WIDTH - 1)
            y = random.randint(0, GRID_HEIGHT - 1)
            if not any(f.x == x and f.y == y for f in self.foods) and (
                x,
                y,
            ) not in self.snake:
                self.foods.append(Food(x, y, food_type))
                break

    def handle_input(self, event):
        if event.type == pygame.KEYDOWN:
            if self.game_over:
                if event.key == pygame.K_SPACE:
                    self.reset()
                return

            if (
                event.key in (pygame.K_UP, pygame.K_w)
                and self.direction != (0, 1)
            ):
                self.next_direction = (0, -1)
            elif (
                event.key in (pygame.K_DOWN, pygame.K_s)
                and self.direction != (0, -1)
            ):
                self.next_direction = (0, 1)
            elif (
                event.key in (pygame.K_LEFT, pygame.K_a)
                and self.direction != (1, 0)
            ):
                self.next_direction = (-1, 0)
            elif (
                event.key in (pygame.K_RIGHT, pygame.K_d)
                and self.direction != (-1, 0)
            ):
                self.next_direction = (1, 0)

    def update(self, dt):
        if self.game_over:
            return

        if self.msg_timer > 0:
            self.msg_timer -= 1

        self.foods = [f for f in self.foods if f.update()]
        if not any(f.type == "normal" for f in self.foods):
            self.spawn_food("normal")

        speed_delay = max(45, self.base_delay - (self.score // 40) * 6)
        if self.slow_timer > 0:
            self.slow_timer -= dt
            speed_delay += 45

        self.move_timer += dt
        if self.move_timer >= speed_delay:
            self.move_timer = 0
            self.direction = self.next_direction

            head_x, head_y = self.snake[0]
            dx, dy = self.direction
            new_head = (head_x + dx, head_y + dy)

            # Collision Check
            if (
                new_head[0] < 0
                or new_head[0] >= GRID_WIDTH
                or new_head[1] < 0
                or new_head[1] >= GRID_HEIGHT
                or new_head in self.snake
            ):
                snd_gameover.play()
                self.game_over = True
                return

            self.snake.insert(0, new_head)

            # Food Check
            eaten = next(
                (f for f in self.foods if (f.x, f.y) == new_head), None
            )
            if eaten:
                self.foods.remove(eaten)
                if eaten.type == "normal":
                    self.score += 10
                    snd_eat.play()
                    self.spawn_food("normal")
                    if random.random() < 0.3 and len(self.foods) < 2:
                        self.spawn_food(
                            random.choice(["golden", "slow"])
                        )
                elif eaten.type == "golden":
                    self.score += 30
                    snd_powerup.play()
                    self.msg = "+30 GOLDEN BONUS!"
                    self.msg_timer = 50
                elif eaten.type == "slow":
                    self.score += 15
                    self.slow_timer = 4500
                    snd_powerup.play()
                    self.msg = "SLOW-MOTION!"
                    self.msg_timer = 50

                if self.score > self.high_score:
                    self.high_score = self.score
                    save_high_score(self.high_score)
            else:
                self.snake.pop()

    def draw_snake(self):
        # Draw Glow Surface
        glow_surf = pygame.Surface(
            (SCREEN_WIDTH, SCREEN_HEIGHT - 70), pygame.SRCALPHA
        )

        for i, (x, y) in enumerate(self.snake):
            cx = x * GRID_SIZE + GRID_SIZE // 2
            cy = y * GRID_SIZE + 70 + GRID_SIZE // 2

            # Head
            if i == 0:
                # Soft Glow under Head
                pygame.draw.circle(
                    glow_surf, COLOR_SNAKE_GLOW, (cx, cy), GRID_SIZE // 2 + 6
                )
                screen.blit(glow_surf, (0, 0))

                # Head Shape
                rect = pygame.Rect(
                    x * GRID_SIZE + 2,
                    y * GRID_SIZE + 72,
                    GRID_SIZE - 4,
                    GRID_SIZE - 4,
                )
                pygame.draw.rect(
                    screen, COLOR_SNAKE_HEAD, rect, border_radius=10
                )

                # Dynamic Eyes
                dx, dy = self.direction
                eye_radius = 3
                offset_fwd = 4
                offset_side = 6

                eye1 = (
                    cx + dx * offset_fwd + dy * offset_side,
                    cy + dy * offset_fwd - dx * offset_side,
                )
                eye2 = (
                    cx + dx * offset_fwd - dy * offset_side,
                    cy + dy * offset_fwd + dx * offset_side,
                )

                pygame.draw.circle(screen, COLOR_EYE, eye1, eye_radius)
                pygame.draw.circle(screen, COLOR_EYE, eye2, eye_radius)

            # Tail (smaller)
            elif i == len(self.snake) - 1:
                rect = pygame.Rect(
                    x * GRID_SIZE + 5,
                    y * GRID_SIZE + 75,
                    GRID_SIZE - 10,
                    GRID_SIZE - 10,
                )
                pygame.draw.rect(
                    screen, COLOR_SNAKE_BODY, rect, border_radius=6
                )

            # Body Segments
            else:
                rect = pygame.Rect(
                    x * GRID_SIZE + 3,
                    y * GRID_SIZE + 73,
                    GRID_SIZE - 6,
                    GRID_SIZE - 6,
                )
                pygame.draw.rect(
                    screen, COLOR_SNAKE_BODY, rect, border_radius=7
                )

    def draw(self):
        screen.fill(COLOR_BG)

        # Draw Clean Grid
        for x in range(0, SCREEN_WIDTH, GRID_SIZE):
            pygame.draw.line(screen, COLOR_GRID, (x, 70), (x, SCREEN_HEIGHT))
        for y in range(70, SCREEN_HEIGHT, GRID_SIZE):
            pygame.draw.line(screen, COLOR_GRID, (0, y), (SCREEN_WIDTH, y))

        # Top Header Bar
        pygame.draw.rect(screen, COLOR_HEADER, (0, 0, SCREEN_WIDTH, 70))
        pygame.draw.line(screen, COLOR_GRID, (0, 70), (SCREEN_WIDTH, 70), 2)

        score_txt = font_score.render(f"SCORE  {self.score}", True, COLOR_TEXT)
        high_txt = font_score.render(
            f"BEST  {self.high_score}", True, COLOR_MUTED
        )
        screen.blit(score_txt, (24, 22))
        screen.blit(high_txt, (SCREEN_WIDTH - high_txt.get_width() - 24, 22))

        if self.msg_timer > 0:
            p_txt = font_sub.render(self.msg, True, COLOR_GOLDEN)
            screen.blit(
                p_txt, (SCREEN_WIDTH // 2 - p_txt.get_width() // 2, 26)
            )

        # Draw Food Items
        for food in self.foods:
            cx = food.x * GRID_SIZE + GRID_SIZE // 2
            cy = food.y * GRID_SIZE + 70 + GRID_SIZE // 2

            if food.type == "normal":
                pygame.draw.circle(
                    screen, COLOR_FOOD, (cx, cy), GRID_SIZE // 2 - 4
                )
            elif food.type == "golden":
                pygame.draw.circle(
                    screen, COLOR_GOLDEN, (cx, cy), GRID_SIZE // 2 - 3
                )
            elif food.type == "slow":
                pygame.draw.circle(
                    screen, COLOR_SLOW, (cx, cy), GRID_SIZE // 2 - 3
                )

        # Draw Snake
        self.draw_snake()

        # Game Over Screen
        if self.game_over:
            overlay = pygame.Surface(
                (SCREEN_WIDTH, SCREEN_HEIGHT - 70), pygame.SRCALPHA
            )
            overlay.fill((10, 12, 18, 215))
            screen.blit(overlay, (0, 70))

            t1 = font_large.render("GAME OVER", True, COLOR_FOOD)
            t2 = font_sub.render("Press SPACE to Restart", True, COLOR_TEXT)

            screen.blit(
                t1,
                t1.get_rect(
                    center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 10)
                ),
            )
            screen.blit(
                t2,
                t2.get_rect(
                    center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 30)
                ),
            )

        pygame.display.flip()


# --- Game Loop ---
game = SnakeGame()
while True:
    dt = clock.tick(60)
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
        game.handle_input(event)

    game.update(dt)
    game.draw()