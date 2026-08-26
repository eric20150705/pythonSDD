#################################載入套件#################################
import pygame
import random
import math

#################################遊戲機本設定#################################
WIDTH = 800
HEIGHT = 600
FRS = 60
FLASH_DURATION = FRS * 3
STARTING_LIVES = 3
MAX_BALLS = 3
MAX_PADDLE_WIDTH = 240
PADDLE_GROWTH = 32
BALL_RADIUS = 12
BALL_SPEED = 7
SCREEN_SHAKE_FRAMES = 12
SCORE_MULTIPLIER_DURATION = 300
BRICK_NORMAL = "normal"
BRICK_HARD = "hard"
BRICK_BONUS = "bonus"
BRICK_SHAKE = "shake"
BRICK_GOLD = "gold"
BRICK_STEEL = "steel"
BRICK_BOMB = "bomb"
BRICK_GLASS = "glass"
BRICK_RAINBOW = "rainbow"
BRICK_HEAVY = "heavy"
BRICK_MULTIPLIER = "multiplier"
BRICK_WILD = "wild"
BRICK_LIFE = "life"
BRICK_PADDLE = "paddle"
BRICK_TRIPLE = "triple"
BRICK_FLASH = "flash"
BRICK_SCORE = {
    BRICK_NORMAL: 10,
    BRICK_HARD: 20,
    BRICK_BONUS: 30,
    BRICK_SHAKE: 15,
    BRICK_GOLD: 50,
    BRICK_STEEL: 40,
    BRICK_BOMB: 25,
    BRICK_GLASS: 35,
    BRICK_RAINBOW: 60,
    BRICK_HEAVY: 60,
    BRICK_MULTIPLIER: 100,
    BRICK_WILD: 10,
    BRICK_LIFE: 40,
    BRICK_PADDLE: 40,
    BRICK_TRIPLE: 50,
    BRICK_FLASH: 70,
}
BACKGROUND = (15, 23, 42)
PADDLE_COLOR = (248, 113, 113)
BALL_COLOR = (248, 113, 113)
TEXT_COLOR = (255, 255, 255)
SHAKE_BRICK_COLOR = (255, 230, 100)
GOLD_BRICK_COLOR = (255, 215, 60)
STEEL_BRICK_COLOR = (190, 205, 225)
BOMB_BRICK_COLOR = (255, 120, 80)
GLASS_BRICK_COLOR = (190, 240, 255)
RAINBOW_COLORS = [
    (255, 80, 80),
    (255, 210, 70),
    (100, 240, 130),
    (80, 200, 255),
    (180, 100, 255),
]
HEAVY_BRICK_COLOR = (90, 100, 125)
MULTIPLIER_BRICK_COLOR = (255, 120, 220)
WILD_BRICK_COLOR = (190, 120, 255)
LIFE_BRICK_COLOR = (100, 255, 150)
PADDLE_BRICK_COLOR = (100, 190, 255)
TRIPLE_BRICK_COLOR = (255, 150, 80)
FLASH_BRICK_COLOR = (255, 255, 255)
BRICK_COLOR = [
    (244, 114, 182),
    (251, 146, 60),
    (250, 204, 21),
    (74, 222, 128),
    (56, 189, 248),
]


################################物件類別#################################
class Brick:
    def __init__(self, x, y, width, height, color, brick_type=BRICK_NORMAL):
        self.rect = pygame.Rect(x, y, width, height)
        self.color = color
        self.brick_type = brick_type
        self.max_hits = {
            BRICK_HARD: 2,
            BRICK_STEEL: 3,
            BRICK_HEAVY: 4,
        }.get(brick_type, 1)
        self.hits_left = self.max_hits
        self.alive = True

    @property
    def shakes_screen(self):
        return self.brick_type in (BRICK_SHAKE, BRICK_BOMB)

    @property
    def score_value(self):
        if self.brick_type == BRICK_WILD:
            return random.choice([10, 20, 30, 50, 80])
        return BRICK_SCORE[self.brick_type]

    def hit(self):
        self.hits_left -= 1
        if self.hits_left <= 0:
            self.alive = False
        return not self.alive

    def draw(self, surface):
        if self.alive:
            pygame.draw.rect(surface, self.color, self.rect, border_radius=5)

            if self.brick_type in (BRICK_HARD, BRICK_STEEL, BRICK_HEAVY):
                border_color = (
                    TEXT_COLOR
                    if self.brick_type == BRICK_HARD
                    else (
                        STEEL_BRICK_COLOR
                        if self.brick_type == BRICK_STEEL
                        else HEAVY_BRICK_COLOR
                    )
                )
                pygame.draw.rect(
                    surface,
                    border_color,
                    self.rect,
                    width=2,
                    border_radius=5,
                )
                for index in range(self.hits_left):
                    pygame.draw.circle(
                        surface,
                        border_color,
                        (self.rect.right - 12 - index * 8, self.rect.top + 8),
                        2,
                    )
            elif self.brick_type == BRICK_BONUS:
                center_x, center_y = self.rect.center
                pygame.draw.polygon(
                    surface,
                    TEXT_COLOR,
                    [
                        (center_x, center_y - 7),
                        (center_x + 7, center_y),
                        (center_x, center_y + 7),
                        (center_x - 7, center_y),
                    ],
                )
            elif self.brick_type == BRICK_GOLD:
                pygame.draw.rect(
                    surface,
                    GOLD_BRICK_COLOR,
                    self.rect,
                    width=3,
                    border_radius=5,
                )
                pygame.draw.circle(surface, GOLD_BRICK_COLOR, self.rect.center, 5)
            elif self.brick_type == BRICK_SHAKE:
                pygame.draw.rect(
                    surface,
                    SHAKE_BRICK_COLOR,
                    self.rect,
                    width=2,
                    border_radius=5,
                )
            elif self.brick_type == BRICK_BOMB:
                pygame.draw.rect(
                    surface,
                    BOMB_BRICK_COLOR,
                    self.rect,
                    width=2,
                    border_radius=5,
                )
                left, top = self.rect.left + 18, self.rect.top + 6
                right, bottom = self.rect.right - 18, self.rect.bottom - 6
                pygame.draw.line(surface, BOMB_BRICK_COLOR, (left, top), (right, bottom), 3)
                pygame.draw.line(surface, BOMB_BRICK_COLOR, (right, top), (left, bottom), 3)
            elif self.brick_type == BRICK_GLASS:
                inner_rect = self.rect.inflate(-10, -8)
                pygame.draw.rect(
                    surface,
                    GLASS_BRICK_COLOR,
                    inner_rect,
                    width=2,
                    border_radius=3,
                )
            elif self.brick_type == BRICK_RAINBOW:
                stripe_width = self.rect.width // len(RAINBOW_COLORS)
                for index, stripe_color in enumerate(RAINBOW_COLORS):
                    stripe_rect = pygame.Rect(
                        self.rect.left + index * stripe_width,
                        self.rect.top + 5,
                        stripe_width,
                        self.rect.height - 10,
                    )
                    pygame.draw.rect(surface, stripe_color, stripe_rect)
                pygame.draw.rect(
                    surface,
                    TEXT_COLOR,
                    self.rect,
                    width=2,
                    border_radius=5,
                )
            elif self.brick_type == BRICK_MULTIPLIER:
                center_x, center_y = self.rect.center
                points = []
                for index in range(10):
                    angle = -math.pi / 2 + index * math.pi / 5
                    radius = 8 if index % 2 == 0 else 3
                    points.append(
                        (
                            round(center_x + math.cos(angle) * radius),
                            round(center_y + math.sin(angle) * radius),
                        )
                    )
                pygame.draw.polygon(surface, MULTIPLIER_BRICK_COLOR, points)
            elif self.brick_type == BRICK_WILD:
                center_x, center_y = self.rect.center
                pygame.draw.circle(
                    surface,
                    WILD_BRICK_COLOR,
                    (center_x, center_y),
                    7,
                    width=2,
                )
                pygame.draw.line(
                    surface,
                    WILD_BRICK_COLOR,
                    (center_x, center_y - 3),
                    (center_x, center_y + 3),
                    2,
                )
                pygame.draw.circle(
                    surface,
                    WILD_BRICK_COLOR,
                    (center_x, center_y + 6),
                    1,
                )
            elif self.brick_type == BRICK_LIFE:
                center_x, center_y = self.rect.center
                pygame.draw.rect(
                    surface,
                    LIFE_BRICK_COLOR,
                    self.rect,
                    width=2,
                    border_radius=5,
                )
                pygame.draw.line(
                    surface,
                    LIFE_BRICK_COLOR,
                    (center_x - 7, center_y),
                    (center_x + 7, center_y),
                    3,
                )
                pygame.draw.line(
                    surface,
                    LIFE_BRICK_COLOR,
                    (center_x, center_y - 7),
                    (center_x, center_y + 7),
                    3,
                )
            elif self.brick_type == BRICK_PADDLE:
                center_x, center_y = self.rect.center
                pygame.draw.rect(
                    surface,
                    PADDLE_BRICK_COLOR,
                    self.rect,
                    width=2,
                    border_radius=5,
                )
                pygame.draw.rect(
                    surface,
                    PADDLE_BRICK_COLOR,
                    pygame.Rect(center_x - 16, center_y - 3, 32, 6),
                    border_radius=3,
                )
            elif self.brick_type == BRICK_TRIPLE:
                center_x, center_y = self.rect.center
                for offset in (-8, 0, 8):
                    pygame.draw.circle(
                        surface,
                        TRIPLE_BRICK_COLOR,
                        (center_x + offset, center_y),
                        4,
                    )
            elif self.brick_type == BRICK_FLASH:
                center_x, center_y = self.rect.center
                pygame.draw.rect(
                    surface,
                    FLASH_BRICK_COLOR,
                    self.rect,
                    width=2,
                    border_radius=5,
                )
                pygame.draw.polygon(
                    surface,
                    FLASH_BRICK_COLOR,
                    [
                        (center_x + 2, center_y - 9),
                        (center_x - 5, center_y + 1),
                        (center_x - 1, center_y + 1),
                        (center_x - 3, center_y + 9),
                        (center_x + 6, center_y - 3),
                        (center_x + 2, center_y - 3),
                    ],
                )


class Paddle:
    def __init__(self):
        self.rect = pygame.Rect(0, 0, 120, 16)
        self.rect.midbottom = (WIDTH // 2, HEIGHT - 34)
        self.speed = 8

    def update(self, keys):
        derection = 0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            derection = -1
        elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            derection = 1
        self.rect.x += derection * self.speed
        self.rect.x = max(0, min(self.rect.x, WIDTH - self.rect.width))

    def grow(self):
        center_x = self.rect.centerx
        self.rect.width = min(MAX_PADDLE_WIDTH, self.rect.width + PADDLE_GROWTH)
        self.rect.centerx = center_x
        self.rect.x = max(0, min(self.rect.x, WIDTH - self.rect.width))

    def draw(self, surface):
        pygame.draw.rect(surface, PADDLE_COLOR, self.rect, border_radius=8)


class Ball:
    def __init__(self, paddle):
        self.radius = BALL_RADIUS
        self.position = pygame.Vector2(0, 0)
        self.velocity = pygame.Vector2(0, 0)
        self.color = BALL_COLOR
        self.color_timer = 0
        self.rect = pygame.Rect(0, 0, self.radius * 2, self.radius * 2)
        self.launched = False
        self.reset(paddle)

    def set_velocity(self, direction):
        if direction.length_squared() > 0:
            self.velocity = direction.normalize() * BALL_SPEED

    def reset(self, paddle):
        self.launched = False
        self.position.update(paddle.rect.centerx, paddle.rect.top - self.radius)
        self.set_velocity(pygame.Vector2(1, -1))
        self.rect.center = (round(self.position.x), round(self.position.y))

    def launch(self):
        self.launched = True

    def set_color(self, color, duration):
        self.color = color
        self.color_timer = duration

    def duplicate(self, paddle, direction):
        duplicate_ball = Ball(paddle)
        duplicate_ball.position = self.position.copy()
        duplicate_ball.rect.center = (
            round(duplicate_ball.position.x),
            round(duplicate_ball.position.y),
        )
        duplicate_ball.launched = self.launched
        duplicate_ball.set_velocity(direction)
        duplicate_ball.color = self.color
        duplicate_ball.color_timer = self.color_timer
        return duplicate_ball

    def update(self, paddle):
        lost = False
        if self.color_timer > 0:
            self.color_timer -= 1
            if self.color_timer == 0:
                self.color = BALL_COLOR

        if not self.launched:
            self.position.update(paddle.rect.centerx, paddle.rect.top - self.radius)
        else:
            self.position += self.velocity
            if self.position.x - self.radius <= 0:
                self.position.x = self.radius
                self.velocity.x *= -1
            elif self.position.x + self.radius >= WIDTH:
                self.position.x = WIDTH - self.radius
                self.velocity.x *= -1
            if self.position.y - self.radius <= 0:
                self.position.y = self.radius
                self.velocity.y *= -1
            if self.position.y + self.radius > HEIGHT:
                self.reset(paddle)
                lost = True

        self.rect.center = (round(self.position.x), round(self.position.y))
        return lost

    def draw(self, surface):
        pygame.draw.circle(surface, self.color, self.rect.center, self.radius)


class Explosion:
    def __init__(self, center, color, particle_count=18, speed_multiplier=1.0):
        self.center = pygame.Vector2(center)
        self.color = color
        self.flash_life = 6
        self.flash_radius = round(12 * speed_multiplier)
        self.particles = []

        for _ in range(particle_count):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(1.5, 5.0) * speed_multiplier
            life = random.randint(18, 30)
            self.particles.append(
                {
                    "position": pygame.Vector2(center),
                    "velocity": pygame.Vector2(math.cos(angle), math.sin(angle))
                    * speed,
                    "radius": random.randint(2, 5),
                    "life": life,
                    "max_life": life,
                }
            )

    def update(self):
        for particle in self.particles:
            particle["position"] += particle["velocity"]
            particle["velocity"] *= 0.92
            particle["velocity"].y += 0.12
            particle["life"] -= 1

        self.flash_life = max(0, self.flash_life - 1)
        self.particles = [
            particle for particle in self.particles if particle["life"] > 0
        ]
        return bool(self.particles)

    def draw(self, surface):
        if self.flash_life > 0:
            flash_radius = self.flash_radius + self.flash_life * 2
            pygame.draw.circle(
                surface,
                (255, 220, 100),
                (round(self.center.x), round(self.center.y)),
                flash_radius,
                width=3,
            )

        for particle in self.particles:
            fade = particle["life"] / particle["max_life"]
            particle_color = tuple(
                max(0, min(255, round(channel * fade))) for channel in self.color
            )
            radius = max(1, round(particle["radius"] * fade))
            position = particle["position"]
            pygame.draw.circle(
                surface,
                particle_color,
                (round(position.x), round(position.y)),
                radius,
            )


class Firework:
    def __init__(self):
        self.position = pygame.Vector2(
            random.randint(80, WIDTH - 80), HEIGHT + 10
        )
        self.velocity = pygame.Vector2(0, -random.uniform(7.0, 10.0))
        self.target_y = random.randint(120, 300)
        self.color = random.choice(
            [
                (255, 80, 80),
                (255, 210, 70),
                (80, 220, 255),
                (180, 100, 255),
                (100, 255, 150),
            ]
        )
        self.burst = False
        self.particles = []

    def create_burst(self):
        self.burst = True
        for _ in range(36):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(1.5, 5.5)
            life = random.randint(30, 50)
            self.particles.append(
                {
                    "position": pygame.Vector2(self.position),
                    "velocity": pygame.Vector2(math.cos(angle), math.sin(angle))
                    * speed,
                    "radius": random.randint(2, 4),
                    "life": life,
                    "max_life": life,
                }
            )

    def update(self):
        if not self.burst:
            self.position += self.velocity
            self.velocity.y += 0.08
            if self.position.y <= self.target_y:
                self.create_burst()
            return True

        for particle in self.particles:
            particle["position"] += particle["velocity"]
            particle["velocity"] *= 0.98
            particle["velocity"].y += 0.04
            particle["life"] -= 1

        self.particles = [
            particle for particle in self.particles if particle["life"] > 0
        ]
        return bool(self.particles)

    def draw(self, surface):
        if not self.burst:
            position = (round(self.position.x), round(self.position.y))
            pygame.draw.line(
                surface,
                self.color,
                (position[0], position[1] + 14),
                position,
                2,
            )
            pygame.draw.circle(surface, TEXT_COLOR, position, 3)
            return

        for particle in self.particles:
            fade = particle["life"] / particle["max_life"]
            particle_color = tuple(
                max(0, min(255, round(channel * fade))) for channel in self.color
            )
            radius = max(1, round(particle["radius"] * fade))
            position = particle["position"]
            pygame.draw.circle(
                surface,
                particle_color,
                (round(position.x), round(position.y)),
                radius,
            )


################################定義含式區#################################
def create_bricks():
    """用同一份Brick物件建立5列9行的磚塊"""
    bricks = []
    rows = 5
    columns = 9
    brick_width = 72
    brick_height = 24
    gap = 8
    start_x = 44
    start_y = 70
    brick_types = [
        BRICK_NORMAL,
        BRICK_BONUS,
        BRICK_SHAKE,
        BRICK_HARD,
        BRICK_GOLD,
        BRICK_STEEL,
        BRICK_BOMB,
        BRICK_GLASS,
        BRICK_RAINBOW,
        BRICK_HEAVY,
        BRICK_MULTIPLIER,
        BRICK_WILD,
        BRICK_LIFE,
        BRICK_PADDLE,
        BRICK_TRIPLE,
        BRICK_FLASH,
    ]
    brick_layout = brick_types.copy()
    while len(brick_layout) < rows * columns:
        brick_layout.append(random.choice(brick_types))
    random.shuffle(brick_layout)
    brick_index = 0

    for row in range(rows):
        for col in range(columns):
            x = start_x + col * (brick_width + gap)
            y = start_y + row * (brick_height + gap)
            color = BRICK_COLOR[row]
            brick_type = brick_layout[brick_index]
            bricks.append(Brick(x, y, brick_width, brick_height, color, brick_type))
            brick_index += 1
    return bricks

def bounce_ball(ball, target_rect):
    overlap = {
        "left": ball.rect.right - target_rect.left,
        "right": target_rect.right - ball.rect.left,
        "top": ball.rect.bottom - target_rect.top,
        "bottom": target_rect.bottom - ball.rect.top,
    }
    collision_side = min(overlap, key=overlap.get)

    if collision_side in ["left", "right"]:
        ball.velocity.x *= -1
    elif collision_side in ["top", "bottom"]:
        ball.velocity.y *= -1


def spawn_brick_explosion(brick, explosions):
    if brick.brick_type == BRICK_GLASS:
        explosions.append(
            Explosion(brick.rect.center, brick.color, 32, speed_multiplier=1.25)
        )
    elif brick.brick_type == BRICK_BONUS:
        explosions.append(
            Explosion(brick.rect.center, brick.color, 28, speed_multiplier=1.15)
        )
    elif brick.brick_type == BRICK_BOMB:
        explosions.append(
            Explosion(brick.rect.center, brick.color, 40, speed_multiplier=1.5)
        )
    else:
        explosions.append(Explosion(brick.rect.center, brick.color))


def add_triple_balls(balls, source_ball, paddle):
    for angle in (-25, 25):
        if len(balls) >= MAX_BALLS:
            break
        balls.append(
            source_ball.duplicate(
                paddle,
                source_ball.velocity.rotate(angle),
            )
        )


def apply_brick_effects(
    destroyed_events,
    balls,
    paddle,
    fireworks,
    lives,
    screen_shake,
    score_multiplier_timer,
    flash_timer,
):
    for brick_type, source_ball in destroyed_events:
        if brick_type == BRICK_GOLD:
            fireworks.append(Firework())
        elif brick_type == BRICK_RAINBOW:
            for current_ball in balls:
                current_ball.set_color(random.choice(RAINBOW_COLORS), 240)
        elif brick_type == BRICK_MULTIPLIER:
            score_multiplier_timer = SCORE_MULTIPLIER_DURATION
        elif brick_type == BRICK_WILD:
            wild_effect = random.choice(
                ["shake", "multiplier", "rainbow", "firework"]
            )
            if wild_effect == "shake":
                screen_shake = max(screen_shake, SCREEN_SHAKE_FRAMES * 2)
            elif wild_effect == "multiplier":
                score_multiplier_timer = SCORE_MULTIPLIER_DURATION
            elif wild_effect == "rainbow":
                for current_ball in balls:
                    current_ball.set_color(random.choice(RAINBOW_COLORS), 240)
            else:
                fireworks.append(Firework())
        elif brick_type == BRICK_LIFE:
            lives += 1
        elif brick_type == BRICK_PADDLE:
            paddle.grow()
        elif brick_type == BRICK_TRIPLE:
            add_triple_balls(balls, source_ball, paddle)
        elif brick_type == BRICK_FLASH:
            flash_timer = FLASH_DURATION

    return lives, screen_shake, score_multiplier_timer, flash_timer


def handle_collision(ball, paddle, bricks, explosions):
    if ball.velocity.y > 0 and ball.rect.colliderect(paddle.rect):
        ball.rect.bottom = paddle.rect.top
        ball.position.y = ball.rect.centery

        offset = (ball.rect.centerx - paddle.rect.centerx) / (paddle.rect.width / 2)
        offset = max(-1, min(1, offset))
        ball.set_velocity(pygame.Vector2(offset, -1))

    for brick in bricks:
        if brick.alive and ball.rect.colliderect(brick.rect):
            spawn_brick_explosion(brick, explosions)
            brick_destroyed = brick.hit()
            bounce_ball(ball, brick.rect)
            score_gain = 0
            should_shake = brick.shakes_screen
            destroyed_events = []

            if brick_destroyed:
                score_gain += brick.score_value
                destroyed_events.append((brick.brick_type, ball))

                if brick.brick_type == BRICK_BOMB:
                    blast_rect = brick.rect.inflate(130, 90)
                    for nearby_brick in bricks:
                        if (
                            nearby_brick is brick
                            or not nearby_brick.alive
                            or not nearby_brick.rect.colliderect(blast_rect)
                        ):
                            continue

                        spawn_brick_explosion(nearby_brick, explosions)
                        nearby_destroyed = nearby_brick.hit()
                        should_shake = (
                            should_shake or nearby_brick.shakes_screen
                        )
                        if nearby_destroyed:
                            score_gain += nearby_brick.score_value
                            destroyed_events.append((nearby_brick.brick_type, ball))

            return score_gain, should_shake, destroyed_events

    return 0, False, []

################################初始化設定#################################
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
game_surface = pygame.Surface((WIDTH, HEIGHT))
pygame.display.set_caption("打磚塊")
clock = pygame.time.Clock()
font = pygame.font.SysFont("Microsoft JhengHei", 28)
game_over_font = pygame.font.SysFont("Microsoft JhengHei", 64)
#################################建立磚塊#################################

bricks = create_bricks()
explosions = []
fireworks = []
#################################底板#################################
paddle = Paddle()
#################################球#################################
balls = [Ball(paddle)]
################################主程式#################################
running = True
lives = STARTING_LIVES
score = 0
score_multiplier_timer = 0
game_over = False
game_won = False
firework_timer = 0
screen_shake = 0
flash_timer = 0
while running:
    # 設定 FpS
    clock.tick(FRS)
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN :
            if event.key == pygame.K_ESCAPE:
                running = False
            elif (
                event.key == pygame.K_SPACE
                and not game_over
                and not game_won
                and flash_timer == 0
            ):
                print("Space key pressed")
                for current_ball in balls:
                    current_ball.launch()
    # 取得鍵盤按鍵狀態；閃光期間暫停遊戲，避免玩家失明時繼續掉球。
    flash_active = flash_timer > 0
    if not flash_active:
        if score_multiplier_timer > 0:
            score_multiplier_timer -= 1

        if not game_over and not game_won:
            keys = pygame.key.get_pressed()
            paddle.update(keys)

            active_balls = []
            for current_ball in balls:
                if not current_ball.update(paddle):
                    active_balls.append(current_ball)
            balls = active_balls

            if not balls:
                lives -= 1
                if lives <= 0:
                    game_over = True
                else:
                    balls = [Ball(paddle)]

            if not game_over:
                for current_ball in balls.copy():
                    score_gain, should_shake, destroyed_events = handle_collision(
                        current_ball, paddle, bricks, explosions
                    )
                    score_multiplier = 2 if score_multiplier_timer > 0 else 1
                    score += score_gain * score_multiplier
                    if should_shake:
                        screen_shake = max(screen_shake, SCREEN_SHAKE_FRAMES)

                    (
                        lives,
                        screen_shake,
                        score_multiplier_timer,
                        flash_timer,
                    ) = apply_brick_effects(
                        destroyed_events,
                        balls,
                        paddle,
                        fireworks,
                        lives,
                        screen_shake,
                        score_multiplier_timer,
                        flash_timer,
                    )

                if all(not brick.alive for brick in bricks):
                    game_won = True

        if game_won:
            firework_timer -= 1
            if firework_timer <= 0:
                fireworks.append(Firework())
                firework_timer = random.randint(10, 20)

        explosions[:] = [
            explosion for explosion in explosions if explosion.update()
        ]
        fireworks[:] = [firework for firework in fireworks if firework.update()]
        screen_shake = max(0, screen_shake - 1)

    # 清除畫面
    game_surface.fill(BACKGROUND)

    for brick in bricks:
        brick.draw(game_surface)

    for explosion in explosions:
        explosion.draw(game_surface)

    for firework in fireworks:
        firework.draw(game_surface)

    paddle.draw(game_surface)
    for current_ball in balls:
        current_ball.draw(game_surface)

    score_text = font.render(f"分數：{score}", True, TEXT_COLOR)
    lives_text = font.render(f"機會：{lives}", True, TEXT_COLOR)
    game_surface.blit(score_text, (20, 20))
    game_surface.blit(lives_text, (190, 20))
    if score_multiplier_timer > 0:
        multiplier_text = font.render("分數 x2", True, (255, 220, 80))
        game_surface.blit(multiplier_text, (330, 20))

    if game_over:
        game_over_text = game_over_font.render("GAME OVER", True, TEXT_COLOR)
        game_over_rect = game_over_text.get_rect(center=(WIDTH // 2, HEIGHT // 2))
        game_surface.blit(game_over_text, game_over_rect)
    elif game_won:
        you_win_text = game_over_font.render("YOU WIN", True, (255, 220, 80))
        you_win_rect = you_win_text.get_rect(center=(WIDTH // 2, HEIGHT // 2))
        game_surface.blit(you_win_text, you_win_rect)

    if flash_timer > 0:
        screen.fill(TEXT_COLOR)
        flash_timer -= 1
    else:
        screen.fill(BACKGROUND)
        if screen_shake > 0:
            shake_offset = (
                random.randint(-screen_shake, screen_shake),
                random.randint(-screen_shake, screen_shake),
            )
        else:
            shake_offset = (0, 0)
        screen.blit(game_surface, shake_offset)

    # 更新畫面
    pygame.display.flip()
#################################遊戲結束設定#################################
pygame.quit()
