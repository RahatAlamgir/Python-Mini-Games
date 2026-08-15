import pygame
from map import COLOR_BTN, COLOR_BTN_HOVER, COLOR_BTN_TEXT, COLOR_SCORE_POPUP, HUD_HEIGHT

font_ui = pygame.font.SysFont("Segoe UI", 16, bold=True)
font_large = pygame.font.SysFont("Segoe UI", 32, bold=True)
font_popup = pygame.font.SysFont("Segoe UI", 14, bold=True)
font_btn = pygame.font.SysFont("Segoe UI", 18, bold=True)

class Button:
    def __init__(self, x, y, width, height, text, callback):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.callback = callback
        self.is_hovered = False

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.is_hovered = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.callback()

    def draw(self, surface):
        color = COLOR_BTN_HOVER if self.is_hovered else COLOR_BTN
        pygame.draw.rect(surface, color, self.rect, border_radius=8)
        pygame.draw.rect(surface, (100, 100, 255), self.rect, 2, border_radius=8)
        t_surf = font_btn.render(self.text, True, COLOR_BTN_TEXT)
        surface.blit(t_surf, t_surf.get_rect(center=self.rect.center))

class FloatingScore:
    def __init__(self, x, y, score):
        self.x, self.y = x, y
        self.score_str = str(score)
        self.timer = 120

    def update(self):
        self.timer -= 1

    def draw(self, surface):
        if self.timer > 0:
            text_surf = font_popup.render(self.score_str, True, COLOR_SCORE_POPUP)
            surface.blit(text_surf, text_surf.get_rect(center=(int(self.x), int(self.y) + HUD_HEIGHT)))