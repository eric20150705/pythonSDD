#################################載入套件#################################
import pygame
import random
#################################遊戲機本設定#################################
WIDTH = 800
HEIGHT = 600
FRS = 60
BACKGROUND = (15, 23, 42)
PADDLE_COLOR = (248, 113, 113)
BRICK_COLOR = [
    (244, 114,182),
    (251, 146, 60),
    (250, 204, 21),
    (74, 222, 128),
    (56, 189, 248)
]
################################物件類別#################################
class Brick:
    def __init__(self, x, y, width, height, color):
        self.rect = pygame.Rect(x, y, width, height)
        self.color = color
        self.alive = True
    def draw(self, surface):
        if self.alive:
            pygame.draw.rect(surface, self.color, self.rect, border_radius=5)
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
    def draw(self, surface):
        pygame.draw.rect(surface, PADDLE_COLOR, self.rect, border_radius=8)
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

    for row in range(rows):
        for col in range(columns):
            x = start_x + col * (brick_width + gap)
            y = start_y + row * (brick_height + gap)
            color = BRICK_COLOR[row]
            bricks.append( Brick(x, y, brick_width, brick_height, color))
    return bricks
################################初始化設定#################################
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("打磚塊")
clock = pygame.time.Clock()
#################################建立磚塊#################################

bricks = create_bricks()
#################################底板#################################
paddle = Paddle()
################################主程式#################################
running = True
while running:
    # 設定 FpS
    clock.tick(FRS)
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            running = False
    # 取得鍵盤按鍵狀態
    keys = pygame.key.get_pressed()
    paddle.update(keys)
    # 清除畫面
    screen.fill(BACKGROUND)

    for brick in bricks:
        brick.draw(screen)

    paddle.draw(screen)
    # 更新畫面
    pygame.display.flip()
#################################遊戲結束設定#################################
pygame.quit()