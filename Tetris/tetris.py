import pygame
import random
import json
import os
import sys

pygame.init()
pygame.font.init()

# Setup Display Constants
CELL_SIZE = 30
COLUMNS = 10
ROWS = 20
GAME_WIDTH = COLUMNS * CELL_SIZE
GAME_HEIGHT = ROWS * CELL_SIZE
SIDEBAR_WIDTH = 220
WINDOW_WIDTH = GAME_WIDTH + SIDEBAR_WIDTH
WINDOW_HEIGHT = GAME_HEIGHT

BASE_DIR = os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else os.getcwd()
SCORE_FILE = os.path.join(BASE_DIR, "high_score.json")

# Palette (RGB)
BLACK = (15, 15, 18)
GRAY = (35, 35, 45)
GRID_LINE = (45, 45, 55)
WHITE = (240, 240, 240)
CYAN = (0, 240, 240)
YELLOW = (240, 240, 0)
PURPLE = (160, 0, 240)
GREEN = (0, 240, 0)
RED = (240, 0, 0)
BLUE = (0, 0, 240)
ORANGE = (240, 160, 0)

COLORS = [CYAN, YELLOW, PURPLE, GREEN, RED, BLUE, ORANGE]

SHAPES = [
    [[0,0,0,0], [1,1,1,1], [0,0,0,0], [0,0,0,0]], # I
    [[1,1], [1,1]],                              # O
    [[0,1,0], [1,1,1], [0,0,0]],                  # T
    [[0,1,1], [1,1,0], [0,0,0]],                  # S
    [[1,1,0], [0,1,1], [0,0,0]],                  # Z
    [[1,0,0], [1,1,1], [0,0,0]],                  # J
    [[0,0,1], [1,1,1], [0,0,0]]                   # L
]

FONT_LARGE = pygame.font.SysFont("Arial", 36, bold=True)
FONT_MED = pygame.font.SysFont("Arial", 20, bold=True)
FONT_SMALL = pygame.font.SysFont("Arial", 14)
FONT_TINY = pygame.font.SysFont("Arial", 12)

class Tetromino:
    def __init__(self, x, y, shape_idx=None):
        self.x = x
        self.y = y
        self.type = random.randint(0, len(SHAPES) - 1) if shape_idx is None else shape_idx
        self.shape = [row[:] for row in SHAPES[self.type]]
        self.color = COLORS[self.type]

    def rotate(self):
        self.shape = [list(row) for row in zip(*self.shape[::-1])]

    def unrotate(self):
        self.shape = [list(row) for row in zip(*[row[::-1] for row in self.shape])]

class TetrisGame:
    def __init__(self):
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("Tetris Professional Edition")
        self.clock = pygame.time.Clock()
        
        self.state = 'MENU'
        self.high_score = self.load_high_score()
        self.reset_game()

    def load_high_score(self):
        if os.path.exists(SCORE_FILE):
            try:
                with open(SCORE_FILE, "r") as f:
                    data = json.load(f)
                    return int(data.get("high_score", 0))
            except Exception:
                return 0
        return 0

    def save_high_score(self):
        if self.score > self.high_score:
            self.high_score = self.score
        
        data = {"high_score": self.high_score}
        try:
            with open(SCORE_FILE, "w") as f:
                json.dump(data, f)
        except Exception as e:
            print(f"Error saving high score: {e}")

    def reset_game(self):
        self.locked_positions = {}
        self.bag = []
        self.current_piece = self.get_next_from_bag()
        self.next_piece = self.get_next_from_bag()
        self.hold_piece = None
        self.can_hold = True
        
        self.score = 0
        self.lines_cleared = 0
        self.level = 1
        self.elapsed_time = 0.0
        self.fall_speed = 0.5  # Initial drop delay (0.5 seconds per step)
        self.fall_time = 0.0

    def get_next_from_bag(self):
        if len(self.bag) == 0:
            self.bag = list(range(len(SHAPES)))
            random.shuffle(self.bag)
        idx = self.bag.pop(0)
        return Tetromino(3, 0, idx)

    def valid_space(self, piece, x_offset=0, y_offset=0):
        for y, row in enumerate(piece.shape):
            for x, cell in enumerate(row):
                if cell:
                    target_x = piece.x + x + x_offset
                    target_y = piece.y + y + y_offset
                    if target_x < 0 or target_x >= COLUMNS or target_y >= ROWS:
                        return False
                    if target_y >= 0 and (target_x, target_y) in self.locked_positions:
                        return False
        return True

    def lock_piece(self):
        for y, row in enumerate(self.current_piece.shape):
            for x, cell in enumerate(row):
                if cell:
                    self.locked_positions[(self.current_piece.x + x, self.current_piece.y + y)] = self.current_piece.color
        
        cleared = self.clear_rows()
        self.update_score(cleared)
        
        self.current_piece = self.next_piece
        self.next_piece = self.get_next_from_bag()
        self.can_hold = True

        if not self.valid_space(self.current_piece):
            self.save_high_score()
            self.state = 'GAMEOVER'

    def hold_current_piece(self):
        if not self.can_hold:
            return
        
        if self.hold_piece is None:
            self.hold_piece = Tetromino(3, 0, self.current_piece.type)
            self.current_piece = self.next_piece
            self.next_piece = self.get_next_from_bag()
        else:
            temp = self.hold_piece.type
            self.hold_piece = Tetromino(3, 0, self.current_piece.type)
            self.current_piece = Tetromino(3, 0, temp)
            
        self.can_hold = False

    def clear_rows(self):
        cleared = 0
        for y in range(ROWS - 1, -1, -1):
            row_full = True
            for x in range(COLUMNS):
                if (x, y) not in self.locked_positions:
                    row_full = False
                    break
            if row_full:
                cleared += 1
                for x in range(COLUMNS):
                    del self.locked_positions[(x, y)]
                
                new_locked = {}
                for (lx, ly), color in self.locked_positions.items():
                    if ly < y:
                        new_locked[(lx, ly + 1)] = color
                    else:
                        new_locked[(lx, ly)] = color
                self.locked_positions = new_locked
                return cleared + self.clear_rows()
        return cleared

    def update_score(self, lines):
        score_table = {0: 0, 1: 100, 2: 300, 3: 500, 4: 800}
        self.score += score_table.get(lines, 0) * self.level
        self.lines_cleared += lines
        
        if self.score > self.high_score:
            self.save_high_score()

    def update_level_and_speed(self, dt):
        self.elapsed_time += dt
        
        # Level updates every 60 seconds (1 minute)
        new_level = int(self.elapsed_time // 60) + 1
        
        if new_level != self.level:
            self.level = new_level
            # Exponential speed formula: drops 15% delay per level up down to 0.03s
            self.fall_speed = max(0.03, 0.5 * (0.85 ** (self.level - 1)))
            self.fall_time = 0  # Force immediate timer sync on speed change

    def hard_drop(self):
        while self.valid_space(self.current_piece, y_offset=1):
            self.current_piece.y += 1
            self.score += 2
        self.lock_piece()

    def draw_button(self, text, x, y, width, height, normal_color, hover_color):
        mouse_pos = pygame.mouse.get_pos()
        rect = pygame.Rect(x, y, width, height)
        is_hovered = rect.collidepoint(mouse_pos)
        
        pygame.draw.rect(self.screen, hover_color if is_hovered else normal_color, rect, border_radius=8)
        pygame.draw.rect(self.screen, WHITE, rect, 2, border_radius=8)
        
        txt_surface = FONT_MED.render(text, True, WHITE)
        txt_rect = txt_surface.get_rect(center=rect.center)
        self.screen.blit(txt_surface, txt_rect)
        
        return rect, is_hovered

    def draw_preview_box(self, title, piece, start_x, start_y):
        rect = pygame.Rect(start_x, start_y, 180, 95)
        pygame.draw.rect(self.screen, GRAY, rect, border_radius=6)
        pygame.draw.rect(self.screen, GRID_LINE, rect, 1, border_radius=6)
        
        lbl = FONT_MED.render(title, True, WHITE)
        self.screen.blit(lbl, (start_x + 10, start_y + 6))

        if piece:
            for y, row in enumerate(piece.shape):
                for x, cell in enumerate(row):
                    if cell:
                        px = start_x + 45 + (x * 18)
                        py = start_y + 35 + (y * 18)
                        pygame.draw.rect(self.screen, piece.color, (px, py, 16, 16), border_radius=2)

    def draw_tutorial_panel(self, start_x, start_y):
        rect = pygame.Rect(start_x, start_y, 180, 160)
        pygame.draw.rect(self.screen, GRAY, rect, border_radius=6)
        pygame.draw.rect(self.screen, GRID_LINE, rect, 1, border_radius=6)

        title = FONT_MED.render("CONTROLS", True, CYAN)
        self.screen.blit(title, (start_x + 10, start_y + 6))

        controls = [
            ("Left / Right", "Move Piece"),
            ("Up Arrow", "Rotate Piece"),
            ("Down Arrow", "Soft Drop"),
            ("Spacebar", "Hard Drop"),
            ("C / Shift", "Hold / Swap Piece"),
            ("P or Esc", "Pause Game")
        ]

        for i, (key, desc) in enumerate(controls):
            txt_key = FONT_TINY.render(f"{key}:", True, YELLOW)
            txt_desc = FONT_TINY.render(desc, True, WHITE)
            self.screen.blit(txt_key, (start_x + 10, start_y + 32 + (i * 20)))
            self.screen.blit(txt_desc, (start_x + 85, start_y + 32 + (i * 20)))

    def draw(self):
        self.screen.fill(BLACK)

        # Draw Grid Board
        for y in range(ROWS):
            for x in range(COLUMNS):
                rect = (x * CELL_SIZE, y * CELL_SIZE, CELL_SIZE, CELL_SIZE)
                color = self.locked_positions.get((x, y), BLACK)
                pygame.draw.rect(self.screen, color, rect)
                pygame.draw.rect(self.screen, GRID_LINE, rect, 1)

        # Draw Active Piece & Ghost Piece
        if self.state in ['PLAYING', 'PAUSED'] and self.current_piece:
            ghost_y = 0
            while self.valid_space(self.current_piece, y_offset=ghost_y + 1):
                ghost_y += 1

            for y, row in enumerate(self.current_piece.shape):
                for x, cell in enumerate(row):
                    if cell:
                        # Draw Ghost
                        gx = (self.current_piece.x + x) * CELL_SIZE
                        gy = (self.current_piece.y + y + ghost_y) * CELL_SIZE
                        pygame.draw.rect(self.screen, GRID_LINE, (gx, gy, CELL_SIZE, CELL_SIZE), 1)

                        # Draw Active Piece
                        px = (self.current_piece.x + x) * CELL_SIZE
                        py = (self.current_piece.y + y) * CELL_SIZE
                        if py >= 0:
                            pygame.draw.rect(self.screen, self.current_piece.color, (px + 1, py + 1, CELL_SIZE - 2, CELL_SIZE - 2), border_radius=3)

        # Draw Divider Line
        pygame.draw.line(self.screen, WHITE, (GAME_WIDTH, 0), (GAME_WIDTH, GAME_HEIGHT), 2)

        # Sidebar UI
        sb_x = GAME_WIDTH + 20
        self.draw_preview_box("NEXT", self.next_piece, sb_x, 15)
        self.draw_preview_box("HOLD", self.hold_piece, sb_x, 120)

        # Stats Area
        time_to_next = 60 - int(self.elapsed_time % 60)
        stats = [
            f"SCORE: {self.score}",
            f"BEST: {self.high_score}",
            f"LINES: {self.lines_cleared}",
            f"LEVEL: {self.level}",
            f"SPEED: {self.fall_speed:.2f}s",
            f"NEXT LVL: {time_to_next}s"
        ]
        for i, stat in enumerate(stats):
            lbl = FONT_SMALL.render(stat, True, WHITE)
            self.screen.blit(lbl, (sb_x, 225 + (i * 22)))

        # Bottom Right Tutorial Box
        self.draw_tutorial_panel(sb_x, 425)

        buttons = {}

        # Overlay Screens (Menu / Pause / Game Over)
        if self.state == 'MENU':
            overlay = pygame.Surface((GAME_WIDTH, GAME_HEIGHT))
            overlay.set_alpha(230)
            overlay.fill(BLACK)
            self.screen.blit(overlay, (0, 0))

            title = FONT_LARGE.render("TETRIS", True, CYAN)
            self.screen.blit(title, title.get_rect(center=(GAME_WIDTH // 2, 160)))

            start_rect, _ = self.draw_button("START GAME", GAME_WIDTH // 2 - 75, 250, 150, 45, (0, 150, 0), (0, 200, 0))
            exit_rect, _ = self.draw_button("EXIT GAME", GAME_WIDTH // 2 - 75, 310, 150, 45, (150, 0, 0), (200, 0, 0))
            
            buttons['start'] = start_rect
            buttons['exit'] = exit_rect

        elif self.state == 'PAUSED':
            overlay = pygame.Surface((GAME_WIDTH, GAME_HEIGHT))
            overlay.set_alpha(200)
            overlay.fill(BLACK)
            self.screen.blit(overlay, (0, 0))

            title = FONT_LARGE.render("PAUSED", True, YELLOW)
            self.screen.blit(title, title.get_rect(center=(GAME_WIDTH // 2, 180)))

            resume_rect, _ = self.draw_button("RESUME", GAME_WIDTH // 2 - 75, 260, 150, 45, (0, 120, 180), (0, 160, 220))
            menu_rect, _ = self.draw_button("MAIN MENU", GAME_WIDTH // 2 - 75, 320, 150, 45, (120, 120, 0), (160, 160, 0))
            
            buttons['resume'] = resume_rect
            buttons['menu'] = menu_rect

        elif self.state == 'GAMEOVER':
            overlay = pygame.Surface((GAME_WIDTH, GAME_HEIGHT))
            overlay.set_alpha(230)
            overlay.fill(BLACK)
            self.screen.blit(overlay, (0, 0))

            title = FONT_LARGE.render("GAME OVER", True, RED)
            self.screen.blit(title, title.get_rect(center=(GAME_WIDTH // 2, 160)))

            restart_rect, _ = self.draw_button("RESTART", GAME_WIDTH // 2 - 75, 250, 150, 45, (150, 0, 0), (200, 0, 0))
            menu_rect, _ = self.draw_button("MAIN MENU", GAME_WIDTH // 2 - 75, 310, 150, 45, (100, 100, 100), (140, 140, 140))
            
            buttons['restart'] = restart_rect
            buttons['menu'] = menu_rect

        return buttons

    def run(self):
        running = True
        while running:
            dt = self.clock.tick(60) / 1000.0
            
            if self.state == 'PLAYING':
                self.update_level_and_speed(dt)
                self.fall_time += dt
                if self.fall_time >= self.fall_speed:
                    self.fall_time = 0
                    if self.valid_space(self.current_piece, y_offset=1):
                        self.current_piece.y += 1
                    else:
                        self.lock_piece()

            buttons = self.draw()
            pygame.display.flip()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.save_high_score()
                    running = False

                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if 'start' in buttons and buttons['start'].collidepoint(event.pos):
                        self.reset_game()
                        self.state = 'PLAYING'
                    elif 'exit' in buttons and buttons['exit'].collidepoint(event.pos):
                        self.save_high_score()
                        running = False
                    elif 'resume' in buttons and buttons['resume'].collidepoint(event.pos):
                        self.state = 'PLAYING'
                    elif 'restart' in buttons and buttons['restart'].collidepoint(event.pos):
                        self.reset_game()
                        self.state = 'PLAYING'
                    elif 'menu' in buttons and buttons['menu'].collidepoint(event.pos):
                        self.save_high_score()
                        self.state = 'MENU'

                if event.type == pygame.KEYDOWN:
                    if event.key in [pygame.K_p, pygame.K_ESCAPE]:
                        if self.state == 'PLAYING':
                            self.state = 'PAUSED'
                        elif self.state == 'PAUSED':
                            self.state = 'PLAYING'

                    if self.state == 'PLAYING':
                        if event.key == pygame.K_LEFT:
                            if self.valid_space(self.current_piece, x_offset=-1):
                                self.current_piece.x -= 1
                        elif event.key == pygame.K_RIGHT:
                            if self.valid_space(self.current_piece, x_offset=1):
                                self.current_piece.x += 1
                        elif event.key == pygame.K_DOWN:
                            if self.valid_space(self.current_piece, y_offset=1):
                                self.current_piece.y += 1
                                self.score += 1
                        elif event.key == pygame.K_UP:
                            self.current_piece.rotate()
                            if not self.valid_space(self.current_piece):
                                self.current_piece.unrotate()
                        elif event.key == pygame.K_SPACE:
                            self.hard_drop()
                            self.fall_time = 0
                        elif event.key == pygame.K_c or event.key == pygame.K_LSHIFT:
                            self.hold_current_piece()

        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    game = TetrisGame()
    game.run()