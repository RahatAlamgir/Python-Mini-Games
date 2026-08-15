import pygame
import sys
import chess_engine
import ai

# --- Configuration & UI Dimensions ---
BOARD_WIDTH, BOARD_HEIGHT = 600, 600
SIDEBAR_WIDTH = 200
WIDTH, HEIGHT = BOARD_WIDTH + SIDEBAR_WIDTH, BOARD_HEIGHT
BOARD_SIZE = 8
SQUARE_SIZE = BOARD_WIDTH // BOARD_SIZE
FPS = 30

# Colors
LIGHT_SQUARE = (240, 217, 181)
DARK_SQUARE = (181, 136, 99)
HIGHLIGHT_COLOR = (186, 202, 68)
SELECTED_COLOR = (246, 246, 105)
CHECK_COLOR = (230, 85, 85)
BG_DARK = (40, 44, 52)
BTN_NORMAL = (70, 130, 180)
BTN_HOVER = (100, 160, 210)
TEXT_COLOR = (255, 255, 255)

PIECE_SYMBOLS = {
    "r": "♜", "n": "♞", "b": "♝", "q": "♛", "k": "♚", "p": "♟",
    "R": "♖", "N": "♘", "B": "♗", "Q": "♕", "K": "♔", "P": "♙"
}

STATE_MENU = "MENU"
STATE_PLAYING = "PLAYING"
STATE_PAUSED = "PAUSED"


class Button:
    """Helper class to create interactive clickable UI buttons."""

    def __init__(self, x, y, width, height, text, bg_color=BTN_NORMAL, hover_color=BTN_HOVER):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.bg_color = bg_color
        self.hover_color = hover_color
        self.is_hovered = False

    def draw(self, screen, font):
        color = self.hover_color if self.is_hovered else self.bg_color
        pygame.draw.rect(screen, color, self.rect, border_radius=8)
        pygame.draw.rect(screen, (200, 200, 200), self.rect, width=2, border_radius=8)

        text_surf = font.render(self.text, True, TEXT_COLOR)
        text_rect = text_surf.get_rect(center=self.rect.center)
        screen.blit(text_surf, text_rect)

    def check_hover(self, pos):
        self.is_hovered = self.rect.collidepoint(pos)

    def is_clicked(self, pos, event_type):
        return event_type == pygame.MOUSEBUTTONDOWN and self.rect.collidepoint(pos)


class MainGame:

    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Python Chess CE - Clickable UI")
        self.clock = pygame.time.Clock()
        self.piece_font = pygame.font.SysFont("Segoe UI Symbol", SQUARE_SIZE - 10)
        self.ui_font = pygame.font.SysFont("Arial", 22, bold=True)
        self.title_font = pygame.font.SysFont("Arial", 40, bold=True)

        self.state = STATE_MENU
        self.game_mode = "PVP"

        self.gs = chess_engine.GameState()
        self.valid_moves = self.gs.get_valid_moves()
        self.selected_sq = ()
        self.player_clicks = []
        self.move_made = False

        # --- Instantiate UI Buttons ---
        self.setup_buttons()

    def setup_buttons(self):
        # Menu Buttons
        self.btn_pvp = Button(WIDTH // 2 - 120, 220, 240, 50, "Play vs Player (PVP)")
        self.btn_pvai = Button(WIDTH // 2 - 120, 290, 240, 50, "Play vs AI (PVAI)")
        self.btn_exit_menu = Button(WIDTH // 2 - 120, 360, 240, 50, "Exit Game", bg_color=(180, 70, 70), hover_color=(210, 100, 100))

        # Pause Buttons
        self.btn_resume = Button(WIDTH // 2 - 120, 220, 240, 50, "Resume Game")
        self.btn_restart_pause = Button(WIDTH // 2 - 120, 290, 240, 50, "Restart Game")
        self.btn_main_menu = Button(WIDTH // 2 - 120, 360, 240, 50, "Main Menu")

        # In-Game Sidebar Buttons
        self.btn_undo = Button(BOARD_WIDTH + 20, 440, 160, 45, "Undo Move")
        self.btn_pause = Button(BOARD_WIDTH + 20, 495, 160, 45, "Pause Game")
        self.btn_menu_side = Button(BOARD_WIDTH + 20, 550, 160, 45, "Main Menu")

    def run(self):
        while True:
            self.clock.tick(FPS)
            mouse_pos = pygame.mouse.get_pos()

            if self.state == STATE_MENU:
                self.handle_menu_events(mouse_pos)
                self.draw_menu()
            elif self.state == STATE_PAUSED:
                self.handle_pause_events(mouse_pos)
                self.draw_pause_screen()
            elif self.state == STATE_PLAYING:
                self.handle_playing_events(mouse_pos)
                self.draw_game()

            pygame.display.flip()

    # --- Event Handling ---
    def handle_menu_events(self, mouse_pos):
        self.btn_pvp.check_hover(mouse_pos)
        self.btn_pvai.check_hover(mouse_pos)
        self.btn_exit_menu.check_hover(mouse_pos)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                if self.btn_pvp.is_clicked(mouse_pos, event.type):
                    self.game_mode = "PVP"
                    self.reset_game()
                    self.state = STATE_PLAYING
                elif self.btn_pvai.is_clicked(mouse_pos, event.type):
                    self.game_mode = "PVAI"
                    self.reset_game()
                    self.state = STATE_PLAYING
                elif self.btn_exit_menu.is_clicked(mouse_pos, event.type):
                    pygame.quit(); sys.exit()

    def handle_pause_events(self, mouse_pos):
        self.btn_resume.check_hover(mouse_pos)
        self.btn_restart_pause.check_hover(mouse_pos)
        self.btn_main_menu.check_hover(mouse_pos)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                if self.btn_resume.is_clicked(mouse_pos, event.type):
                    self.state = STATE_PLAYING
                elif self.btn_restart_pause.is_clicked(mouse_pos, event.type):
                    self.reset_game()
                    self.state = STATE_PLAYING
                elif self.btn_main_menu.is_clicked(mouse_pos, event.type):
                    self.state = STATE_MENU

    def handle_playing_events(self, mouse_pos):
        self.btn_undo.check_hover(mouse_pos)
        self.btn_pause.check_hover(mouse_pos)
        self.btn_menu_side.check_hover(mouse_pos)

        is_human_turn = (self.gs.white_to_move and self.game_mode in ["PVP", "PVAI"]) or \
                        (not self.gs.white_to_move and self.game_mode == "PVP")

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()

            elif event.type == pygame.MOUSEBUTTONDOWN:
                # Handle Sidebar Clicks
                if self.btn_undo.is_clicked(mouse_pos, event.type):
                    self.undo_last_move()
                elif self.btn_pause.is_clicked(mouse_pos, event.type):
                    self.state = STATE_PAUSED
                elif self.btn_menu_side.is_clicked(mouse_pos, event.type):
                    self.state = STATE_MENU

                # Handle Board Clicks
                elif mouse_pos[0] < BOARD_WIDTH and is_human_turn and not self.gs.checkmate:
                    col, row = mouse_pos[0] // SQUARE_SIZE, mouse_pos[1] // SQUARE_SIZE

                    if self.selected_sq == (row, col):
                        self.selected_sq = ()
                        self.player_clicks = []
                    else:
                        self.selected_sq = (row, col)
                        self.player_clicks.append(self.selected_sq)

                    if len(self.player_clicks) == 2:
                        move = chess_engine.Move(self.player_clicks[0], self.player_clicks[1], self.gs.board)
                        for valid_move in self.valid_moves:
                            if move == valid_move:
                                self.gs.make_move(valid_move)
                                self.move_made = True
                                self.selected_sq = ()
                                self.player_clicks = []
                        if not self.move_made:
                            self.player_clicks = [self.selected_sq]

        # AI Turn Trigger
        if not is_human_turn and not self.gs.checkmate and not self.gs.stalemate:
            ai_move = ai.find_best_move(self.gs, self.valid_moves)
            if ai_move:
                self.gs.make_move(ai_move)
                self.move_made = True

        if self.move_made:
            self.valid_moves = self.gs.get_valid_moves()
            self.move_made = False

    def undo_last_move(self):
        self.gs.undo_move()
        if self.game_mode == "PVAI":
            self.gs.undo_move()
        self.move_made = True
        self.selected_sq = ()
        self.player_clicks = []

    def reset_game(self):
        self.gs = chess_engine.GameState()
        self.valid_moves = self.gs.get_valid_moves()
        self.selected_sq = ()
        self.player_clicks = []

    # --- Drawing Methods ---
    def draw_menu(self):
        self.screen.fill(BG_DARK)
        title = self.title_font.render("PYTHON CHESS", True, TEXT_COLOR)
        self.screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 100))

        self.btn_pvp.draw(self.screen, self.ui_font)
        self.btn_pvai.draw(self.screen, self.ui_font)
        self.btn_exit_menu.draw(self.screen, self.ui_font)

    def draw_pause_screen(self):
        self.screen.fill(BG_DARK)
        title = self.title_font.render("GAME PAUSED", True, TEXT_COLOR)
        self.screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 100))

        self.btn_resume.draw(self.screen, self.ui_font)
        self.btn_restart_pause.draw(self.screen, self.ui_font)
        self.btn_main_menu.draw(self.screen, self.ui_font)

    def draw_game(self):
        # Draw Chessboard
        for r in range(BOARD_SIZE):
            for c in range(BOARD_SIZE):
                color = LIGHT_SQUARE if (r + c) % 2 == 0 else DARK_SQUARE

                # Highlight King in check
                if self.gs.in_check_state():
                    k_r, k_c = self.gs.white_king_location if self.gs.white_to_move else self.gs.black_king_location
                    if (r, c) == (k_r, k_c):
                        color = CHECK_COLOR

                if self.selected_sq == (r, c):
                    color = SELECTED_COLOR

                rect = pygame.Rect(c * SQUARE_SIZE, r * SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE)
                pygame.draw.rect(self.screen, color, rect)

                # Highlight valid move options
                if self.selected_sq != ():
                    for move in self.valid_moves:
                        if move.start_row == self.selected_sq[0] and move.start_col == self.selected_sq[1]:
                            target_rect = pygame.Rect(move.end_col * SQUARE_SIZE, move.end_row * SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE)
                            pygame.draw.rect(self.screen, HIGHLIGHT_COLOR, target_rect)

                # Render Pieces
                piece = self.gs.board[r][c]
                if piece != " ":
                    text_surface = self.piece_font.render(PIECE_SYMBOLS[piece], True, (0, 0, 0))
                    text_rect = text_surface.get_rect(center=rect.center)
                    self.screen.blit(text_surface, text_rect)

        # Draw Sidebar
        sidebar_rect = pygame.Rect(BOARD_WIDTH, 0, SIDEBAR_WIDTH, HEIGHT)
        pygame.draw.rect(self.screen, BG_DARK, sidebar_rect)
        pygame.draw.line(self.screen, (100, 100, 100), (BOARD_WIDTH, 0), (BOARD_WIDTH, HEIGHT), 2)

        # Display Turn Status
        turn_text = "White's Turn" if self.gs.white_to_move else "Black's Turn"
        mode_text = f"Mode: {self.game_mode}"
        
        turn_surf = self.ui_font.render(turn_text, True, TEXT_COLOR)
        mode_surf = self.ui_font.render(mode_text, True, (180, 180, 180))
        
        self.screen.blit(turn_surf, (BOARD_WIDTH + 20, 40))
        self.screen.blit(mode_surf, (BOARD_WIDTH + 20, 80))

        # Draw Sidebar Buttons
        self.btn_undo.draw(self.screen, self.ui_font)
        self.btn_pause.draw(self.screen, self.ui_font)
        self.btn_menu_side.draw(self.screen, self.ui_font)

        # Game Over Banner Overlays
        if self.gs.checkmate:
            winner = "Black" if self.gs.white_to_move else "White"
            text = self.ui_font.render(f"CHECKMATE! {winner} Wins", True, (255, 60, 60))
            self.screen.blit(text, (BOARD_WIDTH // 2 - text.get_width() // 2, BOARD_HEIGHT // 2 - 20))
        elif self.gs.stalemate:
            text = self.ui_font.render("STALEMATE!", True, (255, 255, 60))
            self.screen.blit(text, (BOARD_WIDTH // 2 - text.get_width() // 2, BOARD_HEIGHT // 2 - 20))


if __name__ == "__main__":
    game = MainGame()
    game.run()