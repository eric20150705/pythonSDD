#################################載入套件#################################
import pygame
#################################遊戲機本設定#################################
WIDTH = 800
HEIGHT = 600
FRS = 60
BACKGROUND = (15, 23, 42)
################################初始化設定#################################
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("打磚塊")
clock = pygame.time.Clock()

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
    # 清除畫面
    screen.fill(BACKGROUND)
    # 更新畫面
    pygame.display.flip()
#################################遊戲結束設定#################################
pygame.quit()