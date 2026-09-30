import pygame
import random
from .fruit import Fruit
from .sound_manager import SoundManager

# Game Engine

WHITE = (255, 255, 255)
BOMB_BLACK = (30, 30, 30)
FRUIT_COLORS = [(220, 60, 60), (230, 140, 40), (230, 200, 40), (90, 180, 90)]
GAME_OVER_RED = (235, 70, 70)
GREY = (190, 190, 200)

# Difficulty presets. "Medium" matches the original game's tuning.
DIFFICULTIES = {
    "Easy":   {"spawn_interval": 70, "bomb_chance": 0.08, "speed_scale": 1.0,  "color": (70, 170, 90)},
    "Medium": {"spawn_interval": 55, "bomb_chance": 0.15, "speed_scale": 1.0,  "color": (225, 150, 50)},
    "Hard":   {"spawn_interval": 38, "bomb_chance": 0.25, "speed_scale": 1.05, "color": (215, 65, 65)},
}
DEFAULT_DIFFICULTY = "Medium"

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

        self.sounds = SoundManager()  # slice / bomb / game-over effects (silent if no audio device)

        self.high_score = 0  # best score this session, survives restarts
        self.difficulty = DEFAULT_DIFFICULTY
        self._hover = None  # name of the Game Over button under the mouse
        self._build_buttons()
        self.reset()

    def _build_buttons(self):
        """Game Over menu buttons: three difficulties in a row, Exit below."""
        w, h, gap = 150, 48, 20
        total = 3 * w + 2 * gap
        x0 = (self.width - total) // 2
        y = 320
        self.buttons = {}
        for i, name in enumerate(DIFFICULTIES):
            self.buttons[name] = pygame.Rect(x0 + i * (w + gap), y, w, h)
        self.buttons["Exit"] = pygame.Rect((self.width - 200) // 2, y + h + 25, 200, h)

    def reset(self, difficulty=None):
        """Start a fresh round (score, lives, fruit, timers all reset).

        If a difficulty name is given it becomes the active one; otherwise the
        current difficulty is kept. Also used for the very first round.
        """
        if difficulty is not None:
            self.difficulty = difficulty
        settings = DIFFICULTIES[self.difficulty]

        self.fruits = []
        self.trail = []  # recent mouse positions, drawn as the "blade"
        self._last_pos = None  # previous mouse position, used to sweep the blade segment

        self.spawn_interval = settings["spawn_interval"]  # frames between spawns
        self._spawn_timer = 0
        self.bomb_chance = settings["bomb_chance"]
        self.speed_scale = settings["speed_scale"]

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

    def _quit(self):
        pygame.event.post(pygame.event.Event(pygame.QUIT))  # main loop exits cleanly

    def _button_at(self, pos):
        for name, rect in self.buttons.items():
            if rect.collidepoint(pos):
                return name
        return None

    def _choose(self, name):
        if name == "Exit":
            self._quit()
        else:
            self.reset(name)

    def _handle_game_over_event(self, event):
        # Hover highlight always works, even during the input delay.
        if event.type == pygame.MOUSEMOTION:
            self._hover = self._button_at(event.pos)
            return

        # Ignore clicks/keys briefly so the swipe that ended the game can't pick an option.
        if self._game_over_frames < self.INPUT_DELAY_FRAMES:
            return

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_1:
                self._choose("Easy")
            elif event.key == pygame.K_2:
                self._choose("Medium")
            elif event.key == pygame.K_3:
                self._choose("Hard")
            elif event.key in (pygame.K_r, pygame.K_RETURN, pygame.K_SPACE):
                self.reset()  # replay at the same difficulty
            elif event.key in (pygame.K_ESCAPE, pygame.K_q):
                self._quit()
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            name = self._button_at(event.pos)
            if name is not None:
                self._choose(name)

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
            self._end_game("You sliced a bomb!", bomb_channel=self.sounds.play("bomb"))
        else:
            self.score += 1
            self.sounds.play("slice")

    def _end_game(self, reason, bomb_channel=None):
        if self.game_over:
            return
        # Game-over jingle; after a bomb it is queued behind the explosion so they don't clash.
        self.sounds.play("game_over", queue_after=bomb_channel)
        self.game_over = True
        self.game_over_reason = reason
        self._game_over_frames = 0
        self._hover = None
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

        self._blit_centered(screen, self.title_font.render("GAME OVER", True, GAME_OVER_RED), 110)
        self._blit_centered(screen, self.sub_font.render(self.game_over_reason, True, GREY), 165)
        self._blit_centered(screen, self.sub_font.render(f"Final Score: {self.score}", True, WHITE), 210)

        best = f"Best: {self.high_score}" + ("  - New high score!" if self.new_high_score else "")
        self._blit_centered(screen, self.small_font.render(best, True, GREY), 247)

        self._blit_centered(screen, self.font.render("Play again - choose difficulty:", True, WHITE), 290)

        ready = self._game_over_frames >= self.INPUT_DELAY_FRAMES
        for name, rect in self.buttons.items():
            base = DIFFICULTIES[name]["color"] if name in DIFFICULTIES else (90, 90, 105)
            hovered = ready and self._hover == name
            fill = tuple(min(255, c + 35) for c in base) if hovered else base
            if not ready:
                fill = tuple(c // 2 for c in fill)  # dimmed while input is locked
            pygame.draw.rect(screen, fill, rect, border_radius=10)
            # White outline marks the difficulty that was just played
            if name == self.difficulty:
                pygame.draw.rect(screen, WHITE, rect, 3, border_radius=10)
            label = self.sub_font.render(name, True, WHITE)
            screen.blit(label, label.get_rect(center=rect.center))

        hint = "Click a button, or press 1 / 2 / 3  |  R = replay same level  |  Esc = exit"
        self._blit_centered(screen, self.small_font.render(hint, True, GREY), 500)
