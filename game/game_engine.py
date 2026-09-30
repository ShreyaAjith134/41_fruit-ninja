import pygame
import random
from .fruit import Fruit

# Game Engine

WHITE = (255, 255, 255)
BOMB_BLACK = (30, 30, 30)
FRUIT_COLORS = [(220, 60, 60), (230, 140, 40), (230, 200, 40), (90, 180, 90)]
GAME_OVER_RED = (235, 70, 70)
GREY = (190, 190, 200)

class GameEngine:
    INPUT_DELAY_FRAMES = 30  # ~0.5s at 60 FPS: stops a leftover swipe/click from skipping the screen

    def __init__(self, width, height):
        self.width = width
        self.height = height

        self.font = pygame.font.SysFont("Arial", 28)
        self.title_font = pygame.font.SysFont("Arial", 72, bold=True)
        self.sub_font = pygame.font.SysFont("Arial", 32)
        self.small_font = pygame.font.SysFont("Arial", 22)

        # Dim layer drawn behind the Game Over text (created once, reused)
        self._overlay = pygame.Surface((width, height), pygame.SRCALPHA)
        self._overlay.fill((0, 0, 0, 170))

        self.high_score = 0  # best score this session, survives restarts
        self.reset()

    def reset(self):
        """Start a fresh round. Also used for the very first round."""
        self.fruits = []
        self.trail = []  # recent mouse positions, drawn as the "blade"
        self._last_pos = None  # previous mouse position, used to sweep the blade segment

        self.spawn_interval = 55  # frames between spawns
        self._spawn_timer = 0
        self.bomb_chance = 0.15
        self.speed_scale = 1.0

        self.lives = 3
        self.score = 0
        self.game_over = False
        self.game_over_reason = ""
        self._game_over_frames = 0
        self.new_high_score = False

    def spawn_fruit(self):
        x = random.randint(60, self.width - 60)
        vy = -random.uniform(13, 16) * self.speed_scale
        vx = random.uniform(-2, 2)
        gravity = 0.35
        kind = "bomb" if random.random() < self.bomb_chance else "fruit"

        fruit = Fruit(x, self.height + 30, vx, vy, gravity, kind=kind)
        fruit.color = BOMB_BLACK if kind == "bomb" else random.choice(FRUIT_COLORS)
        self.fruits.append(fruit)

    def handle_event(self, event):
        if self.game_over:
            self._handle_game_over_event(event)
            return

        if event.type == pygame.MOUSEMOTION:
            self._handle_motion(event.pos)

    def _handle_game_over_event(self, event):
        # Ignore input briefly so the swipe that ended the game can't dismiss the screen.
        if self._game_over_frames < self.INPUT_DELAY_FRAMES:
            return

        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_r, pygame.K_RETURN, pygame.K_SPACE):
                self.reset()
            elif event.key in (pygame.K_ESCAPE, pygame.K_q):
                pygame.event.post(pygame.event.Event(pygame.QUIT))  # main loop exits cleanly
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.reset()

    def _handle_motion(self, pos):
        x, y = pos
        # Test the whole segment travelled since the last motion event, not just
        # the new point, so fast swipes can't skip over a fruit between events.
        px, py = self._last_pos if self._last_pos is not None else pos

        for fruit in self.fruits:
            if self.game_over:
                break  # a bomb was just sliced; don't slice anything else
            if not fruit.sliced and fruit.intersects_segment(px, py, x, y):
                self._slice(fruit)

        self._last_pos = pos
        self.trail.append(pos)
        if len(self.trail) > 15:
            self.trail.pop(0)

    def _slice(self, fruit):
        fruit.sliced = True
        if fruit.kind == "bomb":
            self._end_game("You sliced a bomb!")
        else:
            self.score += 1

    def _end_game(self, reason):
        if self.game_over:
            return
        self.game_over = True
        self.game_over_reason = reason
        self._game_over_frames = 0
        if self.score > self.high_score:
            self.high_score = self.score
            self.new_high_score = self.score > 0

    def handle_input(self):
        # Reserved for continuously-held-key input; this game is
        # entirely mouse-driven, so there's nothing to poll here.
        pass

    def update(self):
        if self.game_over:
            self._game_over_frames += 1
            return

        self._spawn_timer += 1
        if self._spawn_timer >= self.spawn_interval:
            self._spawn_timer = 0
            self.spawn_fruit()

        still_alive = []
        for fruit in self.fruits:
            fruit.update()
            if fruit.sliced:
                continue
            if fruit.off_screen(self.height):
                if fruit.kind == "fruit":
                    self.lives -= 1
                continue
            still_alive.append(fruit)
        self.fruits = still_alive

        if self.lives <= 0:
            self.lives = 0
            self._end_game("You ran out of lives!")

    def render(self, screen):
        for fruit in self.fruits:
            color = getattr(fruit, "color", WHITE)
            pygame.draw.circle(screen, color, (int(fruit.x), int(fruit.y)), fruit.radius)

        if len(self.trail) >= 2:
            pygame.draw.lines(screen, WHITE, False, self.trail, 3)

        score_text = self.font.render(f"Score: {self.score}", True, WHITE)
        screen.blit(score_text, (10, 10))
        lives_text = self.font.render(f"Lives: {max(self.lives, 0)}", True, WHITE)
        screen.blit(lives_text, (self.width - 130, 10))

        if self.game_over:
            self._render_game_over(screen)

    def _blit_centered(self, screen, surf, y):
        screen.blit(surf, surf.get_rect(center=(self.width // 2, y)))

    def _render_game_over(self, screen):
        screen.blit(self._overlay, (0, 0))
        cy = self.height // 2

        self._blit_centered(screen, self.title_font.render("GAME OVER", True, GAME_OVER_RED), cy - 100)
        self._blit_centered(screen, self.sub_font.render(self.game_over_reason, True, GREY), cy - 40)
        self._blit_centered(screen, self.sub_font.render(f"Final Score: {self.score}", True, WHITE), cy + 10)

        best = f"Best: {self.high_score}" + ("  - New high score!" if self.new_high_score else "")
        self._blit_centered(screen, self.small_font.render(best, True, GREY), cy + 50)

        if self._game_over_frames >= self.INPUT_DELAY_FRAMES:
            # Blink the prompt so it's obvious the game is waiting on the player
            if (self._game_over_frames // 30) % 2 == 0:
                prompt = "Press R / Enter / Click to play again   |   Esc to quit"
                self._blit_centered(screen, self.small_font.render(prompt, True, WHITE), cy + 110)
