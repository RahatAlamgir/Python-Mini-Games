import pygame
import random
import sys
import math
import os
import array

pygame.init()
pygame.mixer.init(frequency=44100, size=-16, channels=1)

# Setup Display
SCREEN_WIDTH = 600
SCREEN_HEIGHT = 700
FPS = 60
LANE_HEIGHT = 50

screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Endless Cross The Road")
clock = pygame.time.Clock()

# --- PROCEDURAL SOUND GENERATOR ---
def generate_sound(freq, duration_ms, wave_type='sine'):
    sample_rate = 44100
    n_samples = int(sample_rate * (duration_ms / 1000.0))
    buf = array.array('h')
    
    for i in range(n_samples):
        t = float(i) / sample_rate
        if wave_type == 'sine':
            val = math.sin(2.0 * math.pi * freq * t)
        elif wave_type == 'square':
            val = 0.5 if math.sin(2.0 * math.pi * freq * t) > 0 else -0.5
        elif wave_type == 'noise':
            val = random.uniform(-1, 1)
        
        env = 1.0 - (i / float(n_samples))
        buf.append(int(val * 12000 * env))
        
    return pygame.mixer.Sound(buffer=buf)

# Sound Effects
SOUND_HOP = generate_sound(450, 60, 'sine')
SOUND_SCORE = generate_sound(800, 90, 'sine')
SOUND_SPLASH = generate_sound(150, 200, 'noise')
SOUND_CRASH = generate_sound(100, 250, 'square')

# Load Assets
try:
    CAR_SCALE = 1.3

    def load_img(path, factor=1.0):
        img = pygame.image.load(path).convert_alpha()
        w, h = img.get_size()
        return pygame.transform.smoothscale(img, (max(1, int(w * factor)), max(1, int(h * factor))))

    VEHICLE_IMAGES = [
        load_img("assets/cars/sports_green.png", CAR_SCALE),
        load_img("assets/cars/sports_race.png", CAR_SCALE),
        load_img("assets/cars/sports_red.png", CAR_SCALE),
        load_img("assets/cars/taxi.png", CAR_SCALE),
        load_img("assets/cars/firetruck.png", CAR_SCALE),
        load_img("assets/cars/police.png", CAR_SCALE),
        load_img("assets/cars/sports_yellow.png", CAR_SCALE),
        load_img("assets/cars/ambulance.png", CAR_SCALE),
        load_img("assets/cars/bus_school.png", CAR_SCALE),
        load_img("assets/cars/bus.png", CAR_SCALE),
    ]

    LIGHT_SINGLE = load_img("assets/decor/light.png", 1.5)
    LIGHT_DOUBLE = load_img("assets/decor/light_double.png", 1.5)
    BARRIER_IMG = load_img("assets/decor/barrier.png", 1.0)

    PLAYER_IDLE = pygame.transform.scale(pygame.image.load("assets/player/man.png").convert_alpha(), (24, 32))
    PLAYER_WALK1 = pygame.transform.scale(pygame.image.load("assets/player/man_walk1.png").convert_alpha(), (24, 32))
    PLAYER_WALK2 = pygame.transform.scale(pygame.image.load("assets/player/man_walk2.png").convert_alpha(), (24, 32))

except pygame.error as e:
    print(f"Error loading image assets: {e}")
    sys.exit()

HIGH_SCORE_FILE = "best_score.txt"

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

class Player(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.image = PLAYER_IDLE
        self.rect = self.image.get_rect()
        
        self.initial_y = SCREEN_HEIGHT - 100
        self.grid_x = SCREEN_WIDTH // 2
        self.grid_y = self.initial_y
        
        self.start_x = self.grid_x
        self.start_y = self.grid_y
        self.target_x = self.grid_x
        self.target_y = self.grid_y
        
        self.anim_progress = 1.0
        self.anim_speed = 0.15
        self.walk_toggle = False

        self.rect.center = (self.grid_x, self.grid_y)

    def start_move(self, dx, dy):
        if self.anim_progress < 1.0:
            return False

        new_target_y = self.grid_y + dy * LANE_HEIGHT
        if new_target_y > self.initial_y:
            return False

        self.start_x = self.grid_x
        self.start_y = self.grid_y
        self.target_x = max(20, min(SCREEN_WIDTH - 20, self.grid_x + dx * 40))
        self.target_y = new_target_y
        
        self.grid_x = self.target_x
        self.grid_y = self.target_y
        
        self.anim_progress = 0.0
        self.walk_toggle = not self.walk_toggle
        
        frame = PLAYER_WALK1 if self.walk_toggle else PLAYER_WALK2
        self.image = pygame.transform.flip(frame, True, False) if dx < 0 else frame
        
        SOUND_HOP.play()
        return True

    def update(self):
        if self.anim_progress < 1.0:
            self.anim_progress += self.anim_speed
            if self.anim_progress >= 1.0:
                self.anim_progress = 1.0
                self.image = PLAYER_IDLE

        current_x = self.start_x + (self.target_x - self.start_x) * self.anim_progress
        current_y = self.start_y + (self.target_y - self.start_y) * self.anim_progress
        
        jump_offset = math.sin(self.anim_progress * math.pi) * 8 if self.anim_progress < 1.0 else 0
        self.rect.center = (int(current_x), int(current_y - jump_offset))

class Vehicle(pygame.sprite.Sprite):
    def __init__(self, y_pos, speed, direction):
        super().__init__()
        base_sprite = random.choice(VEHICLE_IMAGES)

        self.image = pygame.transform.flip(base_sprite, True, False) if direction == -1 else base_sprite
        self.rect = self.image.get_rect()
        self.speed = speed
        self.direction = direction
        self.rect.centery = y_pos
        self.rect.x = -self.rect.width if direction == 1 else SCREEN_WIDTH

    def update(self):
        self.rect.x += self.speed * self.direction
        if (self.direction == 1 and self.rect.left > SCREEN_WIDTH + 50) or \
           (self.direction == -1 and self.rect.right < -50):
            self.kill()

class Log(pygame.sprite.Sprite):
    def __init__(self, y_pos, speed, direction):
        super().__init__()
        self.width = random.choice([110, 150, 190])
        self.height = 32
        self.image = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        
        pygame.draw.rect(self.image, (120, 66, 20), (0, 0, self.width, self.height), border_radius=8)
        pygame.draw.rect(self.image, (85, 45, 12), (0, 0, self.width, self.height), width=3, border_radius=8)
        pygame.draw.line(self.image, (160, 95, 35), (10, 8), (self.width - 10, 8), 2)
        pygame.draw.line(self.image, (160, 95, 35), (15, 22), (self.width - 15, 22), 2)

        self.rect = self.image.get_rect()
        self.speed = speed
        self.direction = direction
        self.rect.centery = y_pos
        self.rect.x = -self.rect.width if direction == 1 else SCREEN_WIDTH

    def update(self):
        self.rect.x += self.speed * self.direction
        if (self.direction == 1 and self.rect.left > SCREEN_WIDTH + 60) or \
           (self.direction == -1 and self.rect.right < -60):
            self.kill()

class Lane:
    def __init__(self, y, lane_type=None):
        self.y = y
        self.type = lane_type if lane_type else random.choice(["GRASS", "ROAD", "ROAD", "WATER", "WATER"])
        self.direction = random.choice([1, -1])
        
        if self.type == "WATER":
            self.speed = random.randint(1, 3)
        else:
            self.speed = random.randint(3, 6)
            
        self.spawn_timer = random.randint(0, 40)
        self.grass_decorations = []

        if self.type == "GRASS":
            self.grass_color = random.choice([
                (34, 139, 34),
                (40, 150, 38),
                (28, 125, 30),
            ])

            trees = []
            num_trees = random.randint(1, 3)
            for _ in range(num_trees):
                tx = random.randint(30, SCREEN_WIDTH - 30)
                tree_radius = random.randint(14, 20)
                trees.append((tx, tree_radius))
                self.grass_decorations.append(("tree", tx, 0, tree_radius))

            rocks = []
            num_rocks = random.randint(1, 2)
            for _ in range(num_rocks):
                rx = random.randint(30, SCREEN_WIDTH - 30)
                ry = random.randint(-10, 10)
                rw = random.randint(18, 26)
                rh = random.randint(10, 14)
                rocks.append((rx, ry, rw, rh))
                self.grass_decorations.append(("rock", rx, ry, rw, rh))

            num_tufts = random.randint(3, 6)
            for _ in range(num_tufts):
                valid_position = False
                attempts = 0
                gx, gy = 0, 0

                while not valid_position and attempts < 15:
                    attempts += 1
                    gx = random.randint(20, SCREEN_WIDTH - 20)
                    gy = random.randint(-12, 12)
                    valid_position = True

                    for tx, radius in trees:
                        dist = math.hypot(gx - tx, gy - (-radius // 2))
                        if dist < radius + 8:
                            valid_position = False
                            break

                    if valid_position:
                        for rx, ry, rw, rh in rocks:
                            rock_rect = pygame.Rect(rx - 4, ry - 4, rw + 8, rh + 8)
                            if rock_rect.collidepoint(gx, gy):
                                valid_position = False
                                break

                if valid_position:
                    self.grass_decorations.append(("tuft", gx, gy))

    def update(self, vehicles_group, logs_group, score):
        self.spawn_timer += 1
        
        if self.type == "ROAD":
            spawn_interval = max(25, 75 - (score // 3))
            if self.spawn_timer >= spawn_interval:
                self.spawn_timer = 0
                adjusted_speed = self.speed + (score // 15)
                vehicles_group.add(Vehicle(self.y, adjusted_speed, self.direction))

        elif self.type == "WATER":
            spawn_interval = max(60, 120 - (score // 4))
            if self.spawn_timer >= spawn_interval:
                can_spawn = True
                for log in logs_group:
                    if abs(log.rect.centery - self.y) < 10:
                        if self.direction == 1 and log.rect.left < 140:
                            can_spawn = False
                        elif self.direction == -1 and log.rect.right > SCREEN_WIDTH - 140:
                            can_spawn = False

                if can_spawn:
                    self.spawn_timer = 0
                    logs_group.add(Log(self.y, self.speed, self.direction))

    def draw_grass_decor(self, surface, camera_y):
        for item in self.grass_decorations:
            if item[0] == "tree":
                _, tx, ty, radius = item
                cy = int(self.y + ty + camera_y)
                pygame.draw.rect(surface, (100, 50, 15), (tx - 4, cy, 8, 16))
                pygame.draw.circle(surface, (20, 100, 25), (tx, cy - radius // 2), radius)
                pygame.draw.circle(surface, (35, 140, 40), (tx - 3, cy - radius // 2 - 2), radius - 3)
            elif item[0] == "tuft":
                _, gx, gy = item
                cy = int(self.y + gy + camera_y)
                pygame.draw.line(surface, (50, 180, 50), (gx, cy), (gx - 3, cy - 6), 2)
                pygame.draw.line(surface, (50, 180, 50), (gx, cy), (gx, cy - 8), 2)
                pygame.draw.line(surface, (50, 180, 50), (gx, cy), (gx + 3, cy - 6), 2)
            elif item[0] == "rock":
                _, rx, ry, rw, rh = item
                rock_rect = pygame.Rect(rx, int(self.y + ry + camera_y), rw, rh)
                pygame.draw.rect(surface, (130, 130, 130), rock_rect, border_radius=4)
                pygame.draw.rect(surface, (90, 90, 90), rock_rect, width=2, border_radius=4)

def draw_curb_barrier(surface, y_pos):
    bw = BARRIER_IMG.get_width()
    bh = BARRIER_IMG.get_height()
    for x in range(0, SCREEN_WIDTH, bw):
        surface.blit(BARRIER_IMG, (x, int(y_pos - bh // 2)))

def draw_street_lights(surface, y_pos, light_img):
    light_spacing = 130
    for x in range(30, SCREEN_WIDTH + light_spacing, light_spacing):
        rect = light_img.get_rect(midbottom=(x, int(y_pos + 5)))
        surface.blit(light_img, rect)

def generate_new_lane(y_pos, recent_lanes):
    recent_grass = 0
    for l in reversed(recent_lanes[-2:]):
        if l.type == "GRASS":
            recent_grass += 1
        else:
            break

    lane_type = random.choice(["ROAD", "ROAD", "WATER", "WATER"]) if recent_grass >= 2 else random.choice(["GRASS", "ROAD", "ROAD", "WATER", "WATER"])
    return Lane(y_pos, lane_type)

class Button:
    def __init__(self, x, y, width, height, text, font):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.font = font

    def draw(self, surface, mouse_pos):
        is_hovered = self.rect.collidepoint(mouse_pos)
        
        btn_surf = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
        bg_color = (255, 255, 255, 70) if is_hovered else (255, 255, 255, 35)
        border_color = (255, 255, 255, 220) if is_hovered else (255, 255, 255, 120)
        
        pygame.draw.rect(btn_surf, bg_color, (0, 0, self.rect.width, self.rect.height), border_radius=12)
        pygame.draw.rect(btn_surf, border_color, (0, 0, self.rect.width, self.rect.height), width=2, border_radius=12)
        surface.blit(btn_surf, self.rect.topleft)

        txt_surf = self.font.render(self.text, True, (255, 255, 255))
        txt_rect = txt_surf.get_rect(center=self.rect.center)
        surface.blit(txt_surf, txt_rect)

    def is_clicked(self, event):
        return event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(event.pos)

def render_transparent_card(title, font_title, mouse_pos, buttons, subtitle=None, font_sub=None):
    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 140))
    screen.blit(overlay, (0, 0))

    card_w, card_h = 420, 360
    card_x, card_y = (SCREEN_WIDTH - card_w) // 2, (SCREEN_HEIGHT - card_h) // 2
    
    card = pygame.Surface((card_w, card_h), pygame.SRCALPHA)
    pygame.draw.rect(card, (20, 20, 20, 180), (0, 0, card_w, card_h), border_radius=20)
    pygame.draw.rect(card, (255, 255, 255, 50), (0, 0, card_w, card_h), width=2, border_radius=20)
    screen.blit(card, (card_x, card_y))

    t_surf = font_title.render(title, True, (255, 255, 255))
    screen.blit(t_surf, t_surf.get_rect(center=(SCREEN_WIDTH // 2, card_y + 45)))

    if subtitle and font_sub:
        s_surf = font_sub.render(subtitle, True, (220, 220, 220))
        screen.blit(s_surf, s_surf.get_rect(center=(SCREEN_WIDTH // 2, card_y + 80)))

    for btn in buttons:
        btn.draw(screen, mouse_pos)

def main():
    state = "MENU"
    high_score = load_high_score()

    player = Player()
    vehicles = pygame.sprite.Group()
    logs = pygame.sprite.Group()
    
    lanes = [Lane(y, "GRASS") for y in range(SCREEN_HEIGHT + 50, SCREEN_HEIGHT - 200, -LANE_HEIGHT)]
    for y in range(SCREEN_HEIGHT - 200, -400, -LANE_HEIGHT):
        lanes.append(generate_new_lane(y, lanes))
    
    score = 0
    max_y_reached = player.grid_y
    camera_y = 0

    font_hud = pygame.font.SysFont("Arial", 24, bold=True)
    font_large = pygame.font.SysFont("Arial", 38, bold=True)
    font_btn = pygame.font.SysFont("Arial", 22, bold=True)
    font_sub = pygame.font.SysFont("Arial", 20)

    # UI Buttons
    btn_start = Button(SCREEN_WIDTH // 2 - 100, SCREEN_HEIGHT // 2 - 30, 200, 48, "PLAY", font_btn)
    btn_exit_m = Button(SCREEN_WIDTH // 2 - 100, SCREEN_HEIGHT // 2 + 35, 200, 48, "EXIT", font_btn)
    
    # Pause Buttons
    btn_resume = Button(SCREEN_WIDTH // 2 - 100, SCREEN_HEIGHT // 2 - 55, 200, 44, "RESUME", font_btn)
    btn_restart_p = Button(SCREEN_WIDTH // 2 - 100, SCREEN_HEIGHT // 2 + 0, 200, 44, "RESTART", font_btn)
    btn_exit_p = Button(SCREEN_WIDTH // 2 - 100, SCREEN_HEIGHT // 2 + 55, 200, 44, "EXIT", font_btn)

    # Game Over Buttons
    btn_restart_g = Button(SCREEN_WIDTH // 2 - 100, SCREEN_HEIGHT // 2 + 25, 200, 48, "PLAY AGAIN", font_btn)

    def reset_game():
        nonlocal player, vehicles, logs, lanes, score, max_y_reached, camera_y
        player = Player()
        vehicles.empty()
        logs.empty()
        score = 0
        max_y_reached = player.grid_y
        camera_y = 0
        lanes = [Lane(y, "GRASS") for y in range(SCREEN_HEIGHT + 50, SCREEN_HEIGHT - 200, -LANE_HEIGHT)]
        for y in range(SCREEN_HEIGHT - 200, -400, -LANE_HEIGHT):
            lanes.append(generate_new_lane(y, lanes))

    running = True

    while running:
        clock.tick(FPS)
        mouse_pos = pygame.mouse.get_pos()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if state == "MENU":
                if btn_start.is_clicked(event) or (event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE):
                    reset_game()
                    state = "PLAYING"
                elif btn_exit_m.is_clicked(event):
                    running = False

            elif state == "PLAYING":
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_UP:
                        if player.start_move(0, -1):
                            if player.target_y < max_y_reached:
                                score += 1
                                max_y_reached = player.target_y
                                SOUND_SCORE.play()
                                if score > high_score:
                                    high_score = score
                                    save_high_score(high_score)
                    elif event.key == pygame.K_DOWN:
                        player.start_move(0, 1)
                    elif event.key == pygame.K_LEFT:
                        player.start_move(-1, 0)
                    elif event.key == pygame.K_RIGHT:
                        player.start_move(1, 0)
                    elif event.key in (pygame.K_ESCAPE, pygame.K_p):
                        state = "PAUSED"

            elif state == "PAUSED":
                if btn_resume.is_clicked(event) or (event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_p)):
                    state = "PLAYING"
                elif btn_restart_p.is_clicked(event) or (event.type == pygame.KEYDOWN and event.key == pygame.K_r):
                    reset_game()
                    state = "PLAYING"
                elif btn_exit_p.is_clicked(event):
                    running = False

            elif state == "GAME_OVER":
                if btn_restart_g.is_clicked(event) or (event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE):
                    reset_game()
                    state = "PLAYING"

        # --- GAME UPDATE ---
        if state == "PLAYING":
            target_camera_y = (SCREEN_HEIGHT - 150) - player.grid_y
            camera_y += (target_camera_y - camera_y) * 0.08

            min_lane_y = min(l.y for l in lanes)
            if min_lane_y + camera_y > -200:
                lanes.append(generate_new_lane(min_lane_y - LANE_HEIGHT, lanes))

            for lane in lanes:
                lane.update(vehicles, logs, score)
                
            vehicles.update()
            logs.update()
            player.update()

            lanes = [l for l in lanes if l.y + camera_y < SCREEN_HEIGHT + 150]
            lanes.sort(key=lambda l: l.y)

            current_lane = next((l for l in lanes if abs(player.rect.centery - l.y) < LANE_HEIGHT // 2), None)

            if current_lane and current_lane.type == "WATER":
                collided_logs = pygame.sprite.spritecollide(player, logs, False)
                if collided_logs:
                    log = collided_logs[0]
                    player.grid_x += log.speed * log.direction
                    player.start_x += log.speed * log.direction
                    player.target_x += log.speed * log.direction
                else:
                    SOUND_SPLASH.play()
                    state = "GAME_OVER"

            if pygame.sprite.spritecollide(player, vehicles, False) or player.rect.right < 0 or player.rect.left > SCREEN_WIDTH:
                SOUND_CRASH.play()
                state = "GAME_OVER"

        # --- RENDERING ---
        screen.fill((30, 30, 30))
        
        # 1. Base Terrain
        for lane in lanes:
            draw_y = lane.y + camera_y
            color = lane.grass_color if lane.type == "GRASS" else (30, 120, 200) if lane.type == "WATER" else (50, 50, 50)
            pygame.draw.rect(screen, color, (0, draw_y - LANE_HEIGHT // 2, SCREEN_WIDTH, LANE_HEIGHT))
            
            if lane.type == "GRASS":
                lane.draw_grass_decor(screen, camera_y)
            elif lane.type == "ROAD":
                for x in range(0, SCREEN_WIDTH, 40):
                    pygame.draw.rect(screen, (255, 255, 255), (x, draw_y + (LANE_HEIGHT // 2) - 2, 22, 4))

        # 2. Logs
        for log in logs:
            screen.blit(log.image, (log.rect.x, log.rect.y + camera_y))

        # 3. Curb Barriers
        for i, lane in enumerate(lanes):
            if lane.type == "ROAD":
                if i == 0 or lanes[i - 1].type != "ROAD":
                    top_edge_y = lane.y - (LANE_HEIGHT // 2) + camera_y
                    draw_curb_barrier(screen, top_edge_y)
                
                if i == len(lanes) - 1 or lanes[i + 1].type != "ROAD":
                    bottom_edge_y = lane.y + (LANE_HEIGHT // 2) + camera_y
                    draw_curb_barrier(screen, bottom_edge_y)

        # 4. Vehicles & Player (Rendered BELOW Street Lights)
        for vehicle in vehicles:
            screen.blit(vehicle.image, (vehicle.rect.x, vehicle.rect.y + camera_y))

        player_draw_rect = player.rect.copy()
        player_draw_rect.y += int(camera_y)
        screen.blit(player.image, player_draw_rect)

        # 5. Street Lights (Rendered OVER Vehicles and Player)
        for i, lane in enumerate(lanes):
            if lane.type == "ROAD":
                road_count = sum(1 for k in range(max(0, i-2), min(len(lanes), i+3)) if lanes[k].type == "ROAD")
                if road_count >= 2:
                    if i == 0 or lanes[i - 1].type != "ROAD":
                        top_edge_y = lane.y - (LANE_HEIGHT // 2) + camera_y
                        draw_street_lights(screen, top_edge_y, LIGHT_SINGLE)
                    
                    if i == len(lanes) - 1 or lanes[i + 1].type != "ROAD":
                        bottom_edge_y = lane.y + (LANE_HEIGHT // 2) + camera_y
                        draw_street_lights(screen, bottom_edge_y, LIGHT_DOUBLE)

        # HUD Overlay
        screen.blit(font_hud.render(f"Score: {score}", True, (255, 255, 255)), (15, 15))
        screen.blit(font_hud.render(f"Best: {high_score}", True, (255, 215, 0)), (15, 45))

        # Transparent Clickable Menus
        if state == "MENU":
            render_transparent_card("CROSS THE ROAD", font_large, mouse_pos, [btn_start, btn_exit_m])
        elif state == "PAUSED":
            render_transparent_card("PAUSED", font_large, mouse_pos, [btn_resume, btn_restart_p, btn_exit_p])
        elif state == "GAME_OVER":
            render_transparent_card("GAME OVER", font_large, mouse_pos, [btn_restart_g], f"Final Score: {score}", font_sub)

        pygame.display.flip()

    pygame.quit()

if __name__ == "__main__":
    main()