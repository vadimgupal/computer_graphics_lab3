import sys, math, pygame
from collections import deque

# -------------------- Конфиг --------------------
WIDTH, HEIGHT = 1000, 720
CANVAS_RECT = pygame.Rect(0, 60, WIDTH, HEIGHT-60)
UI_HEIGHT = 120
BG = (255, 255, 255)
BORDER_COLOR = (0, 0, 0)   # цвет «границы» для режима 1в (обход границы)
# ---- Параметры заливки картинкой ----
PATTERN_MODE = "tile"      # "stamp" | "tile" | "tile_fixed"
PATTERN_ANCHOR = "center"  # "click" | "center"
# палитры
PALETTE = [
    (0,0,0), (255,255,255), (255,0,0), (0,255,0), (0,0,255),
    (255,128,0), (255,0,255), (0,255,255), (128,128,128), (255,230,120)
]

# -------------------- Инициализация --------------------
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Raster tasks: fill (color/pattern), boundary (1в), Bresenham, Wu, triangle")
font = pygame.font.SysFont("Consolas", 16)

canvas = pygame.Surface((WIDTH, HEIGHT-UI_HEIGHT)).convert()
canvas.fill(BG)

# Паттерн
try:
    pattern_img = pygame.image.load("pattern.png").convert_alpha()
except:
    pattern_img = pygame.Surface((8, 8), pygame.SRCALPHA)
    for y in range(8):
        for x in range(8):
            c = (220, 220, 220, 255) if (x+y) % 2 == 0 else (180, 180, 180, 255)
            pattern_img.set_at((x, y), c)

# -------------------- Утилиты --------------------
def in_canvas(x, y):
    return 0 <= x < CANVAS_RECT.w and 0 <= y < CANVAS_RECT.h

def get_px(surf, x, y):
    return surf.get_at((x, y))[:3]

def set_px(surf, x, y, color):
    surf.set_at((x, y), color)

def draw_text(s, x, y, color=(0,0,0)):
    screen.blit(font.render(s, True, color), (x, y))

# -------------------- Инструменты --------------------
TOOL_DRAW        = "draw"
TOOL_FILL_COLOR  = "fill_color"
TOOL_FILL_IMG    = "fill_img"
TOOL_BOUNDARY    = "boundary"     # 1в по клику внутри
TOOL_BRESENHAM   = "bresenham"
TOOL_WU          = "wu"
TOOL_TRIANGLE    = "triangle"

tool = TOOL_DRAW
brush_color = (0, 0, 0)
fill_color = (255, 230, 120)

last_pos = None           # для непрерывного рисования
line_pts = []             # 2 точки для линий
tri_pts = []             # 3 точки для треугольника

# -------------------- Рисование линий --------------------
def bresenham_line(surface, x0, y0, x1, y1, color):
    dx = abs(x1 - x0)
    dy = abs(y1 - y0)

    sx = 1 if x1 > x0 else -1
    sy = 1 if y1 > y0 else -1

    if dy <= dx:
        d = 2 * dy - dx
        y = y0

        for x in range(x0, x1 + sx, sx):
            surface.set_at((x, y), color)

            if d >= 0:  # if di ≥ 0 then yi+1 = yi + 1
                y += sy
                d += 2 * (dy - dx)  # di+1 = di + 2(dy - dx)
            else:  # if di < 0 then yi+1 = yi
                d += 2 * dy  # di+1 = di + 2dy
    else:
        d = 2 * dx - dy
        x = x0

        for y in range(y0, y1 + sy, sy):
            surface.set_at((x, y), color)

            if d >= 0:  # if di ≥ 0 then xi+1 = xi + 1
                x += sx
                d += 2 * (dx - dy)  # di+1 = di + 2(dx - dy)
            else:  # if di < 0 then xi+1 = xi
                d += 2 * dx  # di+1 = di + 2dx

def wu_line(surf, x0, y0, x1, y1, color):
    def ipart(x):
        return int(math.floor(x))

    def fpart(x):
        return x - math.floor(x)

    def rfpart(x):
        return 1 - fpart(x)

    def plot(x, y, a):
        if in_canvas(x,y):
            r,g,b = get_px(surf, x,y)
            rr = int(r*(1-a) + color[0]*a)
            gg = int(g*(1-a) + color[1]*a)
            bb = int(b*(1-a) + color[2]*a)
            set_px(surf, x,y,(rr, gg, bb))

    steep = abs(y1-y0) > abs(x1-x0)
    if steep:
        x0, y0, x1, y1 = y0, x0, y1, x1
    if x0 > x1:
        x0, x1, y0, y1 = x1, x0, y1, y0

    dx = x1-x0
    dy = y1-y0
    gradient = dy/dx if dx else 0.0
    xend = round(x0)
    yend = y0 + gradient*(xend-x0)
    xpxl1 = int(xend)
    ypxl1 = ipart(yend)
    if steep:
        plot(ypxl1,   xpxl1, rfpart(yend))
        plot(ypxl1+1, xpxl1, fpart(yend))
    else:
        plot(xpxl1, ypxl1,   rfpart(yend))
        plot(xpxl1, ypxl1+1, fpart(yend))
    intery = yend + gradient
    xend = round(x1)
    yend = y1 + gradient*(xend-x1)
    xpxl2 = int(xend)
    ypxl2 = ipart(yend)
    for x in range(xpxl1+1, xpxl2):
        if steep:
            plot(ipart(intery),   x, rfpart(intery))
            plot(ipart(intery)+1, x, fpart(intery))
        else:
            plot(x, ipart(intery),   rfpart(intery))
            plot(x, ipart(intery)+1, fpart(intery))
        intery += gradient
    if steep:
        plot(ypxl2,   xpxl2, rfpart(yend))
        plot(ypxl2+1, xpxl2, fpart(yend))
    else:
        plot(xpxl2, ypxl2,   rfpart(yend))
        plot(xpxl2, ypxl2+1, fpart(yend))

# -------------------- Треугольник (градиент) --------------------
def area2(a,b,c):
    return (b[0]-a[0])*(c[1]-a[1]) - (c[0]-a[0])*(b[1]-a[1])

def fill_triangle_barycentric(surf, A, B, C, colA, colB, colC):
    S = area2(A, B, C)
    if S == 0:
        return
    xmin = max(0, min(A[0], B[0], C[0]))
    xmax = min(surf.get_width()-1, max(A[0], B[0], C[0]))
    ymin = max(0, min(A[1], B[1], C[1]))
    ymax = min(surf.get_height()-1, max(A[1], B[1], C[1]))

    for y in range(ymin, ymax+1):
        for x in range(xmin, xmax+1):
            P = (x, y)
            a = area2(B, C, P)/S
            b = area2(C, A, P)/S
            c = area2(A, B, P)/S
            if a >= 0 and b >= 0 and c >= 0:
                r = int(colA[0]*a + colB[0]*b + colC[0]*c)
                g = int(colA[1]*a + colB[1]*b + colC[1]*c)
                bcol = int(colA[2]*a + colB[2]*b + colC[2]*c)
                set_px(surf, x, y, (max(0, min(255, r)), max(0,min(255, g)), max(0, min(255, bcol))))

# -------------------- Заливки (scanline) --------------------
def scanline_fill_color(surf, seed, target, repl):
    if repl == target:
        return
    x0, y0 = seed
    if not in_canvas(x0, y0):
        return
    if get_px(surf, x0, y0) != target:
        return

    # расширяемся по строке
    xl = x0
    while xl-1 >= 0 and get_px(surf, xl-1, y0) == target:
        xl -= 1
    xr = x0
    while xr+1 < surf.get_width() and get_px(surf, xr+1, y0) == target:
        xr += 1
    for x in range(xl, xr+1):
        set_px(surf, x, y0, repl)

    # строки выше/ниже
    for ny in (y0-1, y0+1):
        if 0 <= ny < surf.get_height():
            x = xl
            while x <= xr:
                if get_px(surf, x, ny) == target:
                    scanline_fill_color(surf, (x, ny), target, repl)
                    while x <= xr and get_px(surf, x, ny) == repl:
                        x += 1
                x += 1

def scanline_fill_pattern(surf, seed, target, pattern, anchor, tiled=True, visited=None):
    """
    Итеративная scanline-заливка рисунком:
    - Находим на строке сплошной сегмент target [xl..xr], закрашиваем (или помечаем).
    - На строках y-1 и y+1 ищем все сегменты target и кладём их в стек.
    - Без рекурсии => нет RecursionError на больших областях.
    """
    x0, y0 = seed
    w, h = surf.get_width(), surf.get_height()
    if not in_canvas(x0, y0):
        return
    if visited is None:
        visited = [[False] * w for _ in range(h)]

    # Быстрая проверка старта
    if get_px(surf, x0, y0) != target:
        visited[y0][x0] = True
        return

    pw, ph = pattern.get_width(), pattern.get_height()
    ax, ay = anchor

    stack = [(x0, y0)]
    while stack:
        sx, sy = stack.pop()
        if not (0 <= sx < w and 0 <= sy < h):
            continue
        if visited[sy][sx] or get_px(surf, sx, sy) != target:
            visited[sy][sx] = True
            continue

        # --- 1) расширяемся на текущей строке ---
        xl = sx
        while xl - 1 >= 0 and (not visited[sy][xl - 1]) and get_px(surf, xl - 1, sy) == target:
            xl -= 1
        xr = sx
        while xr + 1 < w and (not visited[sy][xr + 1]) and get_px(surf, xr + 1, sy) == target:
            xr += 1

        # --- 2) красим [xl..xr] и помечаем visited ---
        for x in range(xl, xr + 1):
            if visited[sy][x]:
                continue
            if tiled:
                ux = (x - ax) % pw
                uy = (sy - ay) % ph
                color = pattern.get_at((ux, uy))[:3]
                set_px(surf, x, sy, color)
            else:
                ux = x - ax
                uy = sy - ay
                if 0 <= ux < pw and 0 <= uy < ph:
                    color = pattern.get_at((ux, uy))[:3]
                    set_px(surf, x, sy, color)
                # если вышли за картинку — просто помечаем посещённым (но не красим)
            visited[sy][x] = True

        # --- 3) на строках сверху/снизу ищем все сегменты target и кладём их в стек ---
        for ny in (sy - 1, sy + 1):
            if not (0 <= ny < h):
                continue
            x = xl
            while x <= xr:
                # пропускаем не-target и уже посещённое
                while x <= xr and (visited[ny][x] or get_px(surf, x, ny) != target):
                    x += 1
                if x > xr:
                    break
                # найден старт сегмента; расширяем влево/вправо до границ целой строки
                seg_l = x
                while seg_l - 1 >= 0 and (not visited[ny][seg_l - 1]) and get_px(surf, seg_l - 1, ny) == target:
                    seg_l -= 1
                seg_r = x
                while seg_r + 1 < w and (not visited[ny][seg_r + 1]) and get_px(surf, seg_r + 1, ny) == target:
                    seg_r += 1

                # Кладём ЛЕВЫЙ край сегмента в стек (как и в рекурсивной версии)
                stack.append((seg_l, ny))

                # Продолжаем поиск после сегмента
                x = seg_r + 1


# -------------------- 1в: Выделение границы по клику внутри --------------------
# Идея: BFS по внутренней области (все пиксели != BORDER_COLOR), параллельно набираем соседей == BORDER_COLOR — это граница.

NBS4 = [(1, 0), (-1, 0), (0, 1), (0, -1)]

def boundary_from_inside(surf, seed, border_color=BORDER_COLOR):
    w, h = surf.get_width(), surf.get_height()
    sx, sy = seed
    if not in_canvas(sx, sy):
        return []
    if get_px(surf, sx, sy) == border_color:
        return []  # клик по самой границе — для простоты ничего не делаем

    q = deque([(sx, sy)])
    seen = set([(sx, sy)])
    boundary = set()

    while q:
        x, y = q.popleft()
        for dx, dy in NBS4:
            nx, ny = x+dx, y+dy
            if 0 <= nx < w and 0 <= ny < h:
                c = get_px(surf, nx, ny)
                if c == border_color:
                    boundary.add((nx, ny))
                else:
                    if (nx, ny) not in seen:
                        seen.add((nx, ny))
                        q.append((nx, ny))
    return list(boundary)

def draw_points(surf, pts, color=(255,0,0)):
    for x,y in pts:
        set_px(surf, x,y, color)

# -------------------- UI: кнопки и палитры --------------------
class Button:
    def __init__(self, rect, text, tool_id=None):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.tool_id = tool_id
    def draw(self, active=False):
        col = (210,210,210) if not active else (180,220,255)
        pygame.draw.rect(screen, col, self.rect, border_radius=6)
        pygame.draw.rect(screen, (120,120,120), self.rect, 1, border_radius=6)
        draw_text(self.text, self.rect.x+8, self.rect.y+8)
    def hit(self, pos):
        return self.rect.collidepoint(pos)

# кнопки инструментов
buttons = [
    Button((10,10,100,40), "Рисовать", TOOL_DRAW),
    Button((120,10,110,40), "Заливка", TOOL_FILL_COLOR),
    Button((240,10,140,40), "Заливка img", TOOL_FILL_IMG),
    Button((390,10,120,40), "Граница (1в)", TOOL_BOUNDARY),
    Button((520,10,120,40), "Брезенхем", TOOL_BRESENHAM),
    Button((650,10,80,40), "Ву", TOOL_WU),
    Button((740,10,120,40), "Треугольник", TOOL_TRIANGLE),
    Button((870,10,60,40), "Очист", None),
]

# палитры
brush_palette_rects = []
fill_palette_rects  = []

def draw_palette(x0, y0, label, current_color, rects_list):
    draw_text(label, x0, y0)
    rects_list.clear()
    for i, c in enumerate(PALETTE):
        r = pygame.Rect(x0 + i*24, y0+20, 20, 20)
        rects_list.append((r,c))
        pygame.draw.rect(screen, c, r)
        pygame.draw.rect(screen, (80, 80, 80), r, 1)
        if c == current_color:
            pygame.draw.rect(screen, (0, 0, 0), r.inflate(4, 4), 2)

# -------------------- Главный цикл --------------------
def main():
    global tool, brush_color, fill_color, last_pos, line_pts, tri_pts

    clock = pygame.time.Clock()
    drawing = False

    while True:
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            elif e.type == pygame.MOUSEBUTTONDOWN:
                if e.button == 1:
                    # клик по UI?
                    if e.pos[1] < UI_HEIGHT:
                        # кнопки
                        for b in buttons:
                            if b.hit(e.pos):
                                if b.tool_id is None:   # очистка
                                    canvas.fill(BG)
                                    line_pts.clear()
                                    tri_pts.clear()
                                else:
                                    tool = b.tool_id
                                break
                        # палитры
                        for r,c in brush_palette_rects:
                            if r.collidepoint(e.pos):
                                brush_color = c
                        for r,c in fill_palette_rects:
                            if r.collidepoint(e.pos):
                                fill_color = c
                    else:
                        # клик по холсту
                        x, y = e.pos[0], e.pos[1]-UI_HEIGHT

                        if tool == TOOL_DRAW:
                            drawing = True
                            last_pos = (x,y)
                            pygame.draw.circle(canvas, brush_color, (x,y), 1)

                        elif tool == TOOL_FILL_COLOR:
                            target = get_px(canvas, x,y)
                            scanline_fill_color(canvas, (x,y), target, fill_color)


                        elif tool == TOOL_FILL_IMG:

                            target = get_px(canvas, x, y)

                            # --- выбрать режим тайлинга ---

                            if PATTERN_MODE == "stamp":

                                tiled = False

                            else:

                                tiled = True

                            # --- задать якорь (anchor) ---

                            ax, ay = x, y

                            if PATTERN_ANCHOR == "center":
                                ax = x - pattern_img.get_width() // 2

                                ay = y - pattern_img.get_height() // 2

                            if PATTERN_MODE == "tile_fixed":
                                ax, ay = 0, 0  # узор «привязан» к левому верхнему углу холста

                            scanline_fill_pattern(canvas, (x, y), target, pattern_img, (ax, ay), tiled=tiled)

                        elif tool == TOOL_BOUNDARY:
                            # 1в: по клику внутри — извлечь и прорисовать границу
                            boundary = boundary_from_inside(canvas, (x,y), border_color=BORDER_COLOR)
                            draw_points(canvas, boundary, (255,0,0))
                            print(f"boundary points: {len(boundary)}")

                        elif tool in (TOOL_BRESENHAM, TOOL_WU):
                            line_pts.append((x, y))
                            if len(line_pts) >= 2:
                                (x0,y0),(x1,y1) = line_pts[-2], line_pts[-1]
                                if tool == TOOL_BRESENHAM:
                                    bresenham_line(canvas, x0,y0,x1,y1, brush_color)
                                else:
                                    wu_line(canvas, x0,y0,x1,y1, brush_color)
                            if len(line_pts) > 2:
                                line_pts = line_pts[-2:]

                        elif tool == TOOL_TRIANGLE:
                            tri_pts.append((x, y))
                            if len(tri_pts) == 3:
                                A, B, C = tri_pts[-3], tri_pts[-2], tri_pts[-1]
                                fill_triangle_barycentric(canvas, A, B, C,
                                                          (255, 0, 0), (0, 255, 0), (0, 128, 255))
                                tri_pts.clear()

                elif e.button == 3:
                    # ПКМ — сохранить PNG
                    pygame.image.save(canvas, "out.png")
                    print("Saved to out.png")

            elif e.type == pygame.MOUSEBUTTONUP and e.button == 1:
                drawing = False
                last_pos = None

            elif e.type == pygame.MOUSEMOTION and drawing and tool == TOOL_DRAW:
                x, y = e.pos[0], e.pos[1]-UI_HEIGHT
                if last_pos:
                    pygame.draw.line(canvas, brush_color, last_pos, (x,y), 3)
                last_pos = (x,y)

        # рендер UI
        screen.fill((235, 235, 235))
        # кнопки
        for b in buttons:
            b.draw(active=(b.tool_id == tool))

        # палитры
        draw_palette(10, 55, "Кисть:", brush_color, brush_palette_rects)
        draw_palette(300, 55, "Заливка:", fill_color, fill_palette_rects)

        # холст
        screen.blit(canvas, (0, UI_HEIGHT))
        pygame.draw.rect(screen, (150,150,150), (0, UI_HEIGHT, WIDTH, HEIGHT-UI_HEIGHT), 1)

        # подсказки
        draw_text("ЛКМ по холсту — действие текущего инструмента. ПКМ — сохранить out.png", 10, 105, (40, 40, 40))

        pygame.display.flip()
        clock.tick(120)

if __name__ == "__main__":
    main()
