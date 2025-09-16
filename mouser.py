import pyautogui
import time

# Espera 2 segundos para dar tempo de você mudar de tela
time.sleep(2)

# Velocidade de movimento (em segundos)
duracao = 0.5  

# ---- Movimentos relativos ----
# Mover para a direita 200px
# pyautogui.moveRel(200, 0, duration=duracao)

# # Mover para baixo 200px
# pyautogui.moveRel(0, 200, duration=duracao)

# Mover para a esquerda 200px
pyautogui.moveRel(-200, 0, duration=duracao)

# Mover para cima 200px
pyautogui.moveRel(0, -400, duration=duracao)
