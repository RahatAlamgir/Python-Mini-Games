import math
import os
import random
import sys
import pygame

# Initialize Pygame & Mixer
pygame.init()
pygame.mixer.init(frequency=44100, size=-16, channels=1)

# Display Setup
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 300
FPS = 60
BACKGROUND_COLOR = (247, 247, 247)
SCALE_FACTOR = 0.6
HIGH_SCORE_FILE = "highscore.txt"

screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Chrome Dino Run")
clock = pygame.time.Clock()


# Sound Synthesizer
def generate_beep(frequency, duration, volume=0.3):
    sample_rate = 44100
    n_samples = int(sample_rate * duration)
    buf = bytearray()
    for i in range(n_samples):
        t = float(i) / sample_rate
        value = int(32767.0 * volume * math.sin(2.0 * math.pi * frequency * t))
        buf.extend(value.to_bytes(2, byteorder="little", signed=True))
    return pygame.mixer.Sound(buffer=bytes(buf))


SOUND_JUMP = generate_beep(600, 0.08, 0.25)
SOUND_DIE = generate_beep(200, 0.25, 0.4)
SOUND_SCORE = generate_beep(800, 0.1, 0.2)

# High Score File I/O Helpers
def load_high_score():
    if os.path.exists(HIGH_SCORE_FILE):
        try:
            with open(HIGH_SCORE_FILE, "r") as f:
                return int(f.read().strip())
        except ValueError:
            return 0
    return 0


def save_high_score(score):
    with open(HIGH_SCORE_FILE, "w") as f:
        f.write(str(score))


# Load Sprite Sheet
RAW_SPRITE_SHEET = pygame.image.load("offline-sprite-2x.png").convert_alpha()
sheet_w = int(RAW_SPRITE_SHEET.get_width() * SCALE_FACTOR)
sheet_h = int(RAW_SPRITE_SHEET.get_height() * SCALE_FACTOR)
SPRITE_SHEET = pygame.transform.scale(RAW_SPRITE_SHEET, (sheet_w, sheet_h))


def get_scaled_sprite(x, y, w, h):
    sx, sy = int(x * SCALE_FACTOR), int(y * SCALE_FACTOR)
    sw, sh = int(w * SCALE_FACTOR), int(h * SCALE_FACTOR)
    sprite = pygame.Surface((sw, sh), pygame.SRCALPHA)
    sprite.blit(SPRITE_SHEET, (0, 0), (sx, sy, sw, sh))
    return sprite


# Sprites
DINO_RUN = [
    get_scaled_sprite(1514, 2, 88, 94),
    get_scaled_sprite(1602, 2, 88, 94),
]
DINO_DUCK = [
    get_scaled_sprite(1866, 36, 118, 60),
    get_scaled_sprite(1984, 36, 118, 60),
]
DINO_JUMP = get_scaled_sprite(1338, 2, 88, 94)
DINO_DEAD = get_scaled_sprite(1690, 2, 88, 94)

CACTUS_SMALL = [
    get_scaled_sprite(446, 2, 34, 70),
    get_scaled_sprite(480, 2, 68, 70),
    get_scaled_sprite(548, 2, 102, 70),
]
CACTUS_LARGE = [
    get_scaled_sprite(652, 2, 50, 100),
    get_scaled_sprite(702, 2, 100, 100),
    get_scaled_sprite(802, 2, 150, 100),
]
PTERODACTYL = [
    get_scaled_sprite(260, 2, 92, 80),
    get_scaled_sprite(352, 2, 92, 80),
]

# Process Cloud Sprite to add grey outline contrast
CLOUD_SPRITE = get_scaled_sprite(166, 2, 92, 27)
cloud_w, cloud_h = CLOUD_SPRITE.get_size()
CLOUD_VISIBLE = pygame.Surface((cloud_w, cloud_h), pygame.SRCALPHA)
# Draw darker background silhouette for contrast underneath original cloud surface
mask = pygame.mask.from_surface(CLOUD_SPRITE)
outline = mask.to_surface(setcolor=(160, 160, 160, 255), unsetcolor=(0, 0, 0, 0))
CLOUD_VISIBLE.blit(outline, (0, 1))
CLOUD_VISIBLE.blit(outline, (1, 0))
CLOUD_VISIBLE.blit(CLOUD_SPRITE, (0, 0))

GROUND_SPRITE = get_scaled_sprite(2, 104, 2400, 24)
GAME_OVER_SPRITE = get_scaled_sprite(1294, 29, 382, 32)
RESTART_SPRITE = get_scaled_sprite(2, 2, 72, 64)

GROUND_SURFACE_Y = 240
GROUND_WIDTH = GROUND_SPRITE.get_width()


class Cloud:
    def __init__(self, start_x=None):
        self.x = (
            start_x
            if start_x is not None
            else SCREEN_WIDTH + random.randint(10, 100)
        )
        self.y = random.randint(30, 90)
        self.speed = 1.2

    def update(self, game_speed):
        self.x -= self.speed + (game_speed * 0.1)

    def draw(self, surface):
        surface.blit(CLOUD_VISIBLE, (self.x, self.y))


class Dino:
    def __init__(self):
        self.x = 50
        self.normal_h = DINO_JUMP.get_height()
        self.duck_h = DINO_DUCK[0].get_height()

        self.stand_y = GROUND_SURFACE_Y - self.normal_h
        self.duck_y = GROUND_SURFACE_Y - self.duck_h
        self.y = self.stand_y

        self.vel_y = 0
        self.gravity = 0.7 * SCALE_FACTOR
        self.jump_strength = -16.0 * SCALE_FACTOR

        self.is_jumping = False
        self.is_ducking = False
        self.anim_index = 0

        self.rect = pygame.Rect(
            self.x, self.y, int(40 * SCALE_FACTOR), self.normal_h
        )

    def jump(self):
        if not self.is_jumping:
            self.vel_y = self.jump_strength
            self.is_jumping = True
            SOUND_JUMP.play()

    def cancel_jump(self):
        if self.is_jumping and self.vel_y < 0:
            self.vel_y *= 0.45

    def update(self, keys):
        if (keys[pygame.K_DOWN] or keys[pygame.K_s]) and not self.is_jumping:
            self.is_ducking = True
            self.y = self.duck_y
            self.rect = pygame.Rect(
                self.x,
                self.y,
                DINO_DUCK[0].get_width() - 5,
                self.duck_h - 5,
            )
        else:
            self.is_ducking = False
            if not self.is_jumping:
                self.y = self.stand_y
                self.rect = pygame.Rect(
                    self.x, self.y, int(40 * SCALE_FACTOR), self.normal_h
                )

        if self.is_jumping:
            self.vel_y += self.gravity
            self.y += self.vel_y

            if self.y >= self.stand_y:
                self.y = self.stand_y
                self.is_jumping = False
                self.vel_y = 0

            self.rect = pygame.Rect(
                self.x, self.y, int(40 * SCALE_FACTOR), self.normal_h
            )

        self.anim_index += 0.2

    def draw(self, surface, is_dead=False):
        if is_dead:
            surface.blit(DINO_DEAD, (self.x, self.y))
        elif self.is_jumping:
            surface.blit(DINO_JUMP, (self.x, self.y))
        elif self.is_ducking:
            sprite = DINO_DUCK[int(self.anim_index) % len(DINO_DUCK)]
            surface.blit(sprite, (self.x, self.y))
        else:
            sprite = DINO_RUN[int(self.anim_index) % len(DINO_RUN)]
            surface.blit(sprite, (self.x, self.y))


class Obstacle:
    def __init__(self, speed):
        self.speed = speed
        self.is_bird = random.random() < 0.3

        if self.is_bird:
            self.sprite = PTERODACTYL
            bird_h = self.sprite[0].get_height()
            self.y = random.choice(
                [
                    GROUND_SURFACE_Y - bird_h - int(55 * SCALE_FACTOR),
                    GROUND_SURFACE_Y - bird_h - int(25 * SCALE_FACTOR),
                    GROUND_SURFACE_Y - bird_h,
                ]
            )
            self.rect = pygame.Rect(
                SCREEN_WIDTH,
                self.y + 5,
                self.sprite[0].get_width() - 8,
                bird_h - 10,
            )
            self.anim_index = 0
        else:
            is_large = random.choice([True, False])
            sprites = CACTUS_LARGE if is_large else CACTUS_SMALL
            self.sprite = random.choice(sprites)
            self.y = GROUND_SURFACE_Y - self.sprite.get_height()
            self.rect = pygame.Rect(
                SCREEN_WIDTH,
                self.y + 2,
                self.sprite.get_width() - 6,
                self.sprite.get_height() - 4,
            )

        self.x = float(SCREEN_WIDTH)

    def update(self, speed):
        self.x -= speed
        self.rect.x = int(self.x)

    def draw(self, surface):
        if self.is_bird:
            self.anim_index += 0.15
            sprite = self.sprite[int(self.anim_index) % len(self.sprite)]
            surface.blit(sprite, (self.x, self.y))
        else:
            surface.blit(self.sprite, (self.x, self.y))


def get_random_spawn_delay(speed):
    """Calculates randomized obstacle delay scaled dynamically to current speed."""
    base_min = max(35, int(320 / speed))
    base_max = max(70, int(600 / speed))
    return random.randint(base_min, base_max)


def main():
    dino = Dino()
    obstacles = []
    clouds = [Cloud(150), Cloud(450), Cloud(750)]

    spawn_timer = 0
    next_spawn_delay = get_random_spawn_delay(6.0)
    cloud_timer = 0
    ground_x = 0.0
    game_speed = 6.0
    score = 0
    high_score = load_high_score()
    game_over = False

    font = pygame.font.Font(None, 24)
    big_font = pygame.font.Font(None, 42)

    running = True
    while running:
        clock.tick(FPS)
        keys = pygame.key.get_pressed()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_SPACE, pygame.K_UP):
                    if game_over:
                        dino = Dino()
                        obstacles.clear()
                        clouds = [Cloud(150), Cloud(450), Cloud(750)]
                        score = 0
                        game_speed = 6.0
                        next_spawn_delay = get_random_spawn_delay(game_speed)
                        game_over = False
                    else:
                        dino.jump()

            if event.type == pygame.KEYUP:
                if event.key in (pygame.K_SPACE, pygame.K_UP):
                    dino.cancel_jump()

        if not game_over:
            dino.update(keys)

            # Move Ground
            ground_x -= game_speed
            if ground_x <= -GROUND_WIDTH:
                ground_x += GROUND_WIDTH

            # Manage Clouds
            cloud_timer += 1
            if cloud_timer > random.randint(100, 200):
                clouds.append(Cloud())
                cloud_timer = 0

            for cloud in clouds[:]:
                cloud.update(game_speed)
                if cloud.x < -100:
                    clouds.remove(cloud)

            # Dynamic & Variable Obstacle Spawning
            spawn_timer += 1
            if spawn_timer >= next_spawn_delay:
                obstacles.append(Obstacle(game_speed))
                spawn_timer = 0
                next_spawn_delay = get_random_spawn_delay(game_speed)

            for obs in obstacles[:]:
                obs.update(game_speed)

                if obs.x < -150:
                    obstacles.remove(obs)

                if dino.rect.colliderect(obs.rect):
                    game_over = True
                    SOUND_DIE.play()
                    if score > high_score:
                        high_score = score
                        save_high_score(high_score)

            # Progression
            score += 1
            if score > 0 and score % 500 == 0:
                SOUND_SCORE.play()
                game_speed += 0.5

        # Drawing
        screen.fill(BACKGROUND_COLOR)

        # Draw Clouds
        for cloud in clouds:
            cloud.draw(screen)

        # Draw Ground Line
        ground_y_pos = GROUND_SURFACE_Y - int(10 * SCALE_FACTOR)
        screen.blit(GROUND_SPRITE, (int(ground_x), ground_y_pos))
        screen.blit(GROUND_SPRITE, (int(ground_x) + GROUND_WIDTH, ground_y_pos))

        # Draw Entities
        dino.draw(screen, is_dead=game_over)
        for obs in obstacles:
            obs.draw(screen)

        # Score UI
        score_val = score // 5
        high_val = high_score // 5
        score_text = font.render(
            f"HI {high_val:05d}  {score_val:05d}", True, (83, 83, 83)
        )
        screen.blit(score_text, (SCREEN_WIDTH - 140, 15))

        # Game Over Banner
        if game_over:
            go_w = GAME_OVER_SPRITE.get_width()
            res_w = RESTART_SPRITE.get_width()
            screen.blit(GAME_OVER_SPRITE, (SCREEN_WIDTH // 2 - go_w // 2, 80))
            screen.blit(RESTART_SPRITE, (SCREEN_WIDTH // 2 - res_w // 2, 160))

            text_surface = big_font.render("G A M E   O V E R", True, (83, 83, 83))
            text_rect = text_surface.get_rect(center=(SCREEN_WIDTH // 2, 130))
            screen.blit(text_surface, text_rect)

        pygame.display.flip()


if __name__ == "__main__":
    main()