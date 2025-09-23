import pygame
import sys
import math
import numpy as np
from pygame.locals import *

# Инициализация Pygame
pygame.init()

# Константы
WIDTH, HEIGHT = 1000, 700
CANVAS_WIDTH, CANVAS_HEIGHT = 800, 600
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
GRAY = (200, 200, 200)

# Создание окна
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("CompGraph_lab3")

# Основные поверхности
canvas = pygame.Surface((CANVAS_WIDTH, CANVAS_HEIGHT))
canvas.fill(WHITE)
toolbar = pygame.Surface((WIDTH - CANVAS_WIDTH, HEIGHT))
toolbar.fill(GRAY)

# Переменные состояния
current_tool = "draw"  # draw, fill, pattern_fill, boundary, line, triangle
current_color = BLACK
pattern_image = None
pattern_loaded = False
boundary_points = []
triangle_points = []
drawing = False

# Шрифт
font = pygame.font.SysFont('Arial', 16)


class PatternFill:
    def __init__(self):
        self.pattern = None
        self.width = 0
        self.height = 0

    def load_pattern(self, filename):
        try:
            self.pattern = pygame.image.load(filename).convert()
            self.width, self.height = self.pattern.get_size()
            return True
        except:
            return False

    def get_pixel(self, x, y):
        if self.pattern is None:
            return BLACK
        # Циклическое повторение рисунка
        px = x % self.width
        py = y % self.height
        return self.pattern.get_at((px, py))


pattern_filler = PatternFill()


def draw_button(text, rect, active=False):
    color = (100, 100, 200) if active else (150, 150, 150)
    pygame.draw.rect(toolbar, color, rect)
    pygame.draw.rect(toolbar, BLACK, rect, 2)

    text_surf = font.render(text, True, BLACK)
    text_rect = text_surf.get_rect(center=rect.center)
    toolbar.blit(text_surf, text_rect)


def flood_fill_scanline(surface, x, y, fill_color, target_color=None):
    """Рекурсивная заливка с использованием алгоритма серий пикселов"""
    if x < 0 or x >= CANVAS_WIDTH or y < 0 or y >= CANVAS_HEIGHT:
        return

    if target_color is None:
        target_color = surface.get_at((x, y))

    if surface.get_at((x, y)) != target_color:
        return

    # Находим левую границу
    left = x
    while left > 0 and surface.get_at((left - 1, y)) == target_color:
        left -= 1

    # Находим правую границу
    right = x
    while right < CANVAS_WIDTH - 1 and surface.get_at((right + 1, y)) == target_color:
        right += 1

    # Заливаем линию
    for i in range(left, right + 1):
        surface.set_at((i, y), fill_color)

    # Рекурсивно обрабатываем строки выше и ниже
    for i in range(left, right + 1):
        if y > 0 and surface.get_at((i, y - 1)) == target_color:
            flood_fill_scanline(surface, i, y - 1, fill_color, target_color)
        if y < CANVAS_HEIGHT - 1 and surface.get_at((i, y + 1)) == target_color:
            flood_fill_scanline(surface, i, y + 1, fill_color, target_color)


def pattern_fill_scanline(surface, x, y, pattern_filler, target_color=None):
    """Заливка рисунком с использованием алгоритма серий пикселов"""
    if x < 0 or x >= CANVAS_WIDTH or y < 0 or y >= CANVAS_HEIGHT:
        return

    if target_color is None:
        target_color = surface.get_at((x, y))

    if surface.get_at((x, y)) != target_color:
        return

    # Находим левую границу
    left = x
    while left > 0 and surface.get_at((left - 1, y)) == target_color:
        left -= 1

    # Находим правую границу
    right = x
    while right < CANVAS_WIDTH - 1 and surface.get_at((right + 1, y)) == target_color:
        right += 1

    # Заливаем линию рисунком
    for i in range(left, right + 1):
        pattern_color = pattern_filler.get_pixel(i, y)
        surface.set_at((i, y), pattern_color)

    # Рекурсивно обрабатываем строки выше и ниже
    for i in range(left, right + 1):
        if y > 0 and surface.get_at((i, y - 1)) == target_color:
            pattern_fill_scanline(surface, i, y - 1, pattern_filler, target_color)
        if y < CANVAS_HEIGHT - 1 and surface.get_at((i, y + 1)) == target_color:
            pattern_fill_scanline(surface, i, y + 1, pattern_filler, target_color)


def find_boundary(surface, x, y, boundary_color):
    """Поиск и обход границы связной области"""
    if x < 0 or x >= CANVAS_WIDTH or y < 0 or y >= CANVAS_HEIGHT:
        return []

    start_color = surface.get_at((x, y))
    if start_color == boundary_color:
        return []

    # Направления обхода (по часовой стрелке)
    directions = [(0, -1), (1, 0), (0, 1), (-1, 0)]
    boundary_points = []
    visited = set()

    # Находим начальную точку границы
    current_x, current_y = x, y
    found = False

    # Ищем границу в соседних пикселях
    for dx, dy in directions:
        nx, ny = x + dx, y + dy
        if 0 <= nx < CANVAS_WIDTH and 0 <= ny < CANVAS_HEIGHT:
            if surface.get_at((nx, ny)) == boundary_color:
                current_x, current_y = nx, ny
                found = True
                break

    if not found:
        return []

    start_x, start_y = current_x, current_y
    boundary_points.append((current_x, current_y))
    visited.add((current_x, current_y))

    # Алгоритм обхода границы (алгоритм жука)
    direction = 0  # начальное направление: вверх
    stuck_counter = 0

    while stuck_counter < 1000:
        # Пытаемся двигаться в текущем направлении
        dx, dy = directions[direction]
        nx, ny = current_x + dx, current_y + dy

        if 0 <= nx < CANVAS_WIDTH and 0 <= ny < CANVAS_HEIGHT:
            if surface.get_at((nx, ny)) == boundary_color:
                if (nx, ny) not in visited:
                    boundary_points.append((nx, ny))
                    visited.add((nx, ny))
                    current_x, current_y = nx, ny
                    # Поворачиваем налево (против часовой стрелки)
                    direction = (direction - 1) % 4
                    stuck_counter = 0
                else:
                    # Уже посещали эту точку, поворачиваем направо
                    direction = (direction + 1) % 4
                    stuck_counter += 1
            else:
                # Не граница, поворачиваем направо
                direction = (direction + 1) % 4
                stuck_counter += 1
        else:
            # Выход за границы, поворачиваем направо
            direction = (direction + 1) % 4
            stuck_counter += 1

        # Проверяем, вернулись ли мы в начало
        if len(boundary_points) > 1 and (current_x, current_y) == (start_x, start_y):
            break

        if stuck_counter >= 4:  # Если застряли
            break

    return boundary_points


def bresenham_line(surface, x0, y0, x1, y1, color):
    """Канонический алгоритм Брезенхема"""
    if abs(y1 - y0) < abs(x1 - x0):
        if x0 > x1:
            plot_line_low(surface, x1, y1, x0, y0, color)
        else:
            plot_line_low(surface, x0, y0, x1, y1, color)
    else:
        if y0 > y1:
            plot_line_high(surface, x1, y1, x0, y0, color)
        else:
            plot_line_high(surface, x0, y0, x1, y1, color)


def plot_line_low(surface, x0, y0, x1, y1, color):
    """Рисует линию с малым наклоном (|dy| <= |dx|)"""
    dx = x1 - x0
    dy = y1 - y0
    yi = 1
    if dy < 0:
        yi = -1
        dy = -dy

    D = 2 * dy - dx
    y = y0

    for x in range(x0, x1 + 1):
        surface.set_at((x, y), color)
        if D > 0:
            y += yi
            D += 2 * (dy - dx)
        else:
            D += 2 * dy


def plot_line_high(surface, x0, y0, x1, y1, color):
    """Рисует линию с большим наклоном (|dy| > |dx|)"""
    dx = x1 - x0
    dy = y1 - y0
    xi = 1
    if dx < 0:
        xi = -1
        dx = -dx

    D = 2 * dx - dy
    x = x0

    for y in range(y0, y1 + 1):
        surface.set_at((x, y), color)
        if D > 0:
            x += xi
            D += 2 * (dx - dy)
        else:
            D += 2 * dx


def wu_line(surface, x1, y1, x2, y2, color):
    """Алгоритм ВУ для сглаженных отрезков"""

    def plot(x, y, brightness):
        if 0 <= x < CANVAS_WIDTH and 0 <= y < CANVAS_HEIGHT:
            r = int(color[0] + (255 - color[0]) * (1-brightness))
            g = int(color[1] + (255 - color[1]) * (1-brightness))
            b = int(color[2] + (255 - color[2]) * (1-brightness))
            surface.set_at((int(x), int(y)), (r, g, b))
            #print(r,g,b, brightness)

    dx = x2 - x1
    dy = y2 - y1

    if abs(dx) > abs(dy):
        # Горизонтальная линия
        if x2 < x1:
            x1, x2 = x2, x1
            y1, y2 = y2, y1
            dx = -dx
            dy = -dy

        gradient = dy / dx if dx != 0 else 1
        xend = round(x1)
        yend = y1 + gradient * (xend - x1)
        xgap = 1 - (x1 + 0.5) % 1
        xpxl1 = xend
        ypxl1 = int(yend)
        plot(xpxl1, ypxl1, (1 - (yend % 1)) * xgap)
        plot(xpxl1, ypxl1 + 1, (yend % 1) * xgap)
        intery = yend + gradient

        xend = round(x2)
        yend = y2 + gradient * (xend - x2)
        xgap = (x2 + 0.5) % 1
        xpxl2 = xend
        ypxl2 = int(yend)
        plot(xpxl2, ypxl2, (1 - (yend % 1)) * xgap)
        plot(xpxl2, ypxl2 + 1, (yend % 1) * xgap)

        for x in range(int(xpxl1) + 1, int(xpxl2)):
            plot(x, int(intery), 1 - (intery % 1))
            plot(x, int(intery) + 1, intery % 1)
            #print(1 - (intery % 1), intery % 1)
            intery += gradient
    else:
        # Вертикальная линия
        if y2 < y1:
            x1, x2 = x2, x1
            y1, y2 = y2, y1
            dx = -dx
            dy = -dy

        gradient = dx / dy if dy != 0 else 1
        yend = round(y1)
        xend = x1 + gradient * (yend - y1)
        ygap = 1 - (y1 + 0.5) % 1
        ypxl1 = yend
        xpxl1 = int(xend)
        plot(xpxl1, ypxl1, (1 - (xend % 1)) * ygap)
        plot(xpxl1 + 1, ypxl1, (xend % 1) * ygap)
        interx = xend + gradient

        yend = round(y2)
        xend = x2 + gradient * (yend - y2)
        ygap = (y2 + 0.5) % 1
        ypxl2 = yend
        xpxl2 = int(xend)
        plot(xpxl2, ypxl2, (1 - (xend % 1)) * ygap)
        plot(xpxl2 + 1, ypxl2, (xend % 1) * ygap)

        for y in range(int(ypxl1) + 1, int(ypxl2)):
            plot(int(interx), y, 1 - (interx % 1))
            plot(int(interx) + 1, y, interx % 1)
            interx += gradient


def rasterize_triangle(surface, p1, p2, p3, color1, color2, color3):
    """Растеризация треугольника через барицентрические координаты"""

    # Находим ограничивающий прямоугольник
    x_min = int(min(p1[0], p2[0], p3[0]))
    x_max = int(max(p1[0], p2[0], p3[0]))
    y_min = int(min(p1[1], p2[1], p3[1]))
    y_max = int(max(p1[1], p2[1], p3[1]))

    # Предварительные вычисления для барицентрических координат
    v0x = p2[0] - p1[0]
    v0y = p2[1] - p1[1]
    v1x = p3[0] - p1[0]
    v1y = p3[1] - p1[1]

    # "Площадь" треугольника (удвоенная)
    denom = v0x * v1y - v1x * v0y

    # Если треугольник вырожденный (нулевая площадь)
    if abs(denom) < 0.0001:
        return

    # Обработка каждого пикселя в ограничивающем прямоугольнике
    for y in range(y_min, y_max + 1):
        for x in range(x_min, x_max + 1):
            # Вычисляем барицентрические координаты
            v2x = x - p1[0]
            v2y = y - p1[1]

            # Вычисляем dot-продукты
            dot00 = v0x * v0x + v0y * v0y
            dot01 = v0x * v1x + v0y * v1y
            dot02 = v0x * v2x + v0y * v2y
            dot11 = v1x * v1x + v1y * v1y
            dot12 = v1x * v2x + v1y * v2y

            # Вычисляем барицентрические координаты
            inv_denom = 1.0 / (dot00 * dot11 - dot01 * dot01)
            u = (dot11 * dot02 - dot01 * dot12) * inv_denom
            v = (dot00 * dot12 - dot01 * dot02) * inv_denom
            w = 1.0 - u - v  # Третья координата

            # Проверяем, находится ли точка внутри треугольника
            if u >= 0 and v >= 0 and w >= 0:
                # Интерполяция цвета
                r = int(color1[0] * w + color2[0] * u + color3[0] * v)
                g = int(color1[1] * w + color2[1] * u + color3[1] * v)
                b = int(color1[2] * w + color2[2] * u + color3[2] * v)

                # Ограничиваем значения цвета
                r = max(0, min(255, r))
                g = max(0, min(255, g))
                b = max(0, min(255, b))

                # Рисуем пиксель
                if 0 <= x < CANVAS_WIDTH and 0 <= y < CANVAS_HEIGHT:
                    surface.set_at((x, y), (r, g, b))


# Основной цикл
running = True
while running:
    for event in pygame.event.get():
        if event.type == QUIT:
            running = False

        elif event.type == MOUSEBUTTONDOWN:
            x, y = event.pos

            # Обработка кликов в тулбаре
            if x > CANVAS_WIDTH:
                rel_x = x - CANVAS_WIDTH

                # Кнопки инструментов
                if 10 <= rel_x <= 190:
                    if 10 <= y <= 40:
                        current_tool = "draw"
                    elif 50 <= y <= 80:
                        current_tool = "fill"
                    elif 90 <= y <= 120:
                        current_tool = "pattern_fill"
                    elif 130 <= y <= 160:
                        current_tool = "boundary"
                    elif 170 <= y <= 200:
                        current_tool = "line"
                    elif 210 <= y <= 240:
                        current_tool = "triangle"

                # Загрузка рисунка для заливки
                if 10 <= rel_x <= 190 and 280 <= y <= 310:
                    pattern_filler.load_pattern("pattern.jpg")  # загрузка файла >>>>>>>>>>>>>>>>>>>
                    pattern_loaded = True

                # Выбор цвета
                if 10 <= rel_x <= 40:
                    if 350 <= y <= 380:
                        current_color = RED
                    elif 390 <= y <= 420:
                        current_color = GREEN
                    elif 430 <= y <= 460:
                        current_color = BLUE
                    elif 470 <= y <= 500:
                        current_color = BLACK

            # Обработка кликов на холсте
            else:
                if current_tool == "draw":
                    drawing = True

                elif current_tool == "fill":
                    flood_fill_scanline(canvas, x, y, current_color)

                elif current_tool == "pattern_fill" and pattern_loaded:
                    pattern_fill_scanline(canvas, x, y, pattern_filler)

                elif current_tool == "boundary":
                    boundary_points = find_boundary(canvas, x, y, current_color)
                    # Рисуем границу поверх изображения
                    if boundary_points:
                        for i in range(len(boundary_points) - 1):
                            x1, y1 = boundary_points[i]
                            x2, y2 = boundary_points[i + 1]
                            pygame.draw.line(canvas, RED, (x1, y1), (x2, y2), 2)
                        # # Замыкаем границу
                        # if len(boundary_points) > 1:
                        #     x1, y1 = boundary_points[0]
                        #     x2, y2 = boundary_points[-1]
                        #     pygame.draw.line(canvas, RED, (x1, y1), (x2, y2), 2)

                elif current_tool == "line":
                    if len(triangle_points) == 0:
                        triangle_points = [(x, y)]
                    else:
                        # Рисуем отрезок алгоритмом Брезенхема
                        x1, y1 = triangle_points[0]
                        bresenham_line(canvas, x1, y1, x, y, current_color)
                        # Рисуем отрезок алгоритмом ВУ рядом
                        wu_line(canvas, x1 + 5, y1 + 5, x + 5, y + 5, current_color)
                        triangle_points = []

                elif current_tool == "triangle":
                    triangle_points.append((x, y))
                    if len(triangle_points) == 3:
                        # Растеризуем треугольник с градиентом
                        rasterize_triangle(canvas,
                                           triangle_points[0],
                                           triangle_points[1],
                                           triangle_points[2],
                                           RED, GREEN, BLUE)
                        triangle_points = []

        elif event.type == MOUSEBUTTONUP:
            if current_tool == "draw" and drawing:
                drawing = False

        elif event.type == MOUSEMOTION:
            if drawing and current_tool == "draw":
                x, y = event.pos
                if 0 <= x < CANVAS_WIDTH and 0 <= y < CANVAS_HEIGHT:
                    pygame.draw.circle(canvas, current_color, (x, y), 4)

    # Отрисовка интерфейса
    screen.fill(WHITE)
    screen.blit(canvas, (0, 0))
    screen.blit(toolbar, (CANVAS_WIDTH, 0))

    # Очистка тулбара
    toolbar.fill(GRAY)

    # Рисуем кнопки инструментов
    draw_button("Рисование", pygame.Rect(10, 10, 180, 30), current_tool == "draw")
    draw_button("Заливка цветом (1а)", pygame.Rect(10, 50, 180, 30), current_tool == "fill")
    draw_button("Заливка рисунком (1б)", pygame.Rect(10, 90, 180, 30), current_tool == "pattern_fill")
    draw_button("Граница области (1в)", pygame.Rect(10, 130, 180, 30), current_tool == "boundary")
    draw_button("Отрезки (2)", pygame.Rect(10, 170, 180, 30), current_tool == "line")
    draw_button("Треугольник (3)", pygame.Rect(10, 210, 180, 30), current_tool == "triangle")

    # Кнопка загрузки рисунка
    draw_button("Загрузить рисунок", pygame.Rect(10, 280, 180, 30))

    # Выбор цвета
    pygame.draw.rect(toolbar, RED, (10, 350, 30, 30))
    pygame.draw.rect(toolbar, GREEN, (10, 390, 30, 30))
    pygame.draw.rect(toolbar, BLUE, (10, 430, 30, 30))
    pygame.draw.rect(toolbar, BLACK, (10, 470, 30, 30))

    # Информация
    info_text = [
        "Инструкция:",
        "1. Выберите инструмент",
        "2. Для заливки: щелкните внутри области",
        "3. Для границы: щелкните у границы",
        "4. Для отрезков: два щелчка",
        "5. Для треугольника: три щелчка"
    ]

    for i, text in enumerate(info_text):
        text_surf = font.render(text, True, BLACK)
        toolbar.blit(text_surf, (10, 520 + i * 25))


    pygame.display.flip()

pygame.quit()
sys.exit()
