#!/usr/bin/env python3
import turtle
import math
import random
import time

random.seed(20261027)

# ============================================================
# Tuning / quality settings
# ============================================================
WIDTH = 900
HEIGHT = 600
HORIZON = 80

TRACK_LEN = 700       # track length in segments
DRAW = 30             # visible road slices; lower if slow
NEAR = 0.8            # near projection distance in segments

CAM_HEIGHT = 1000.0
Y_SCALE = 0.38
ROAD_PROJ = 430.0
CURVE_PROJ = 170.0

MAX_SPEED = 21.0
CAR_SCALE = 1.8
SPRITE_SCALE = 1.8


# ============================================================
# Small helpers
# ============================================================
def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


def lerp(a, b, t):
    return a + (b - a) * t


def mix(c1, c2, t):
    t = clamp(t, 0.0, 1.0)
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def shade(c, f):
    return tuple(clamp(int(v * f), 0, 255) for v in c)


# ============================================================
# Screen / turtles
# ============================================================
screen = turtle.Screen()
screen.setup(WIDTH, HEIGHT)
screen.title("Turtle Pseudo-3D Racer")
screen.colormode(255)
screen.bgcolor((10, 10, 18))
screen.tracer(False)
screen.setworldcoordinates(-WIDTH / 2, -HEIGHT / 2, WIDTH / 2, HEIGHT / 2)

bg = turtle.Turtle()
bg.hideturtle()
bg.speed(0)
bg.penup()

pen = turtle.Turtle()
pen.hideturtle()
pen.speed(0)
pen.penup()
pen.pensize(1)

hud = turtle.Turtle()
hud.hideturtle()
hud.speed(0)
hud.penup()


def fill_poly(t, pts, color):
    """Fill a polygon. Leaves pen up afterwards."""
    if len(pts) < 3:
        return
    t.pensize(1)
    t.pencolor(color)
    t.fillcolor(color)
    t.penup()
    t.goto(pts[0][0], pts[0][1])
    t.pendown()
    t.begin_fill()
    for px, py in pts[1:]:
        t.goto(px, py)
    t.goto(pts[0][0], pts[0][1])
    t.end_fill()
    t.penup()


def draw_shape(x, y, scale, pts, color, angle=0.0):
    """Draw a local polygon sprite part rotated around (x, y)."""
    if scale <= 0 or len(pts) < 3:
        return
    ca = math.cos(angle)
    sa = math.sin(angle)
    out = []
    for px, py in pts:
        px *= scale
        py *= scale
        out.append((x + px * ca - py * sa, y + px * sa + py * ca))
    fill_poly(pen, out, color)


# ============================================================
# Static procedural background: sky, sun, clouds, mountains
# ============================================================
def draw_background():
    # Sky gradient
    top = (20, 20, 70)
    mid = (140, 60, 120)
    low = (255, 150, 80)
    bands = 50

    for i in range(bands):
        t0 = i / bands
        t1 = (i + 1) / bands
        y_top = lerp(HEIGHT / 2, HORIZON, t0)
        y_bot = lerp(HEIGHT / 2, HORIZON, t1)

        if t0 < 0.55:
            c = mix(top, mid, t0 / 0.55)
        else:
            c = mix(mid, low, (t0 - 0.55) / 0.45)

        fill_poly(
            bg,
            [(-WIDTH / 2, y_top), (WIDTH / 2, y_top),
             (WIDTH / 2, y_bot), (-WIDTH / 2, y_bot)],
            c
        )

    # Sun
    sun_x = 170
    sun_y = HORIZON + 75
    bg.goto(sun_x, sun_y)
    bg.dot(150, (255, 160, 90))
    bg.dot(110, (255, 195, 110))
    bg.dot(75, (255, 235, 165))

    # Clouds
    rng = random.Random(99)
    for _ in range(16):
        x = rng.uniform(-WIDTH / 2, WIDTH / 2)
        y = rng.uniform(HORIZON + 35, HEIGHT / 2 - 35)
        size = rng.uniform(16, 64)
        c = mix((255, 225, 205), (255, 175, 155), rng.random())
        bg.goto(x, y)
        bg.dot(int(size), c)
        bg.goto(x + size * 0.45, y - size * 0.12)
        bg.dot(int(size * 0.7), c)

    # Mountains
    def ridge(base, amp1, amp2, color, phase):
        pts = [(-WIDTH / 2, HORIZON - 5)]
        x = -WIDTH / 2
        while x <= WIDTH / 2:
            y = (HORIZON + base +
                 amp1 * math.sin(x * 0.008 + phase) +
                 amp2 * math.sin(x * 0.023 + phase * 2.7))
            pts.append((x, y))
            x += 18
        pts.append((WIDTH / 2, HORIZON - 5))
        fill_poly(bg, pts, color)

    ridge(16, 35, 18, (70, 40, 85), 1.2)
    ridge(6, 25, 12, (45, 25, 55), 3.8)

    # Base ground under the road
    fill_poly(
        bg,
        [(-WIDTH / 2, HORIZON), (WIDTH / 2, HORIZON),
         (WIDTH / 2, -HEIGHT / 2), (-WIDTH / 2, -HEIGHT / 2)],
        (48, 122, 48)
    )

    # Horizon haze
    bg.pensize(4)
    bg.pencolor((255, 180, 110))
    bg.penup()
    bg.goto(-WIDTH / 2, HORIZON)
    bg.pendown()
    bg.goto(WIDTH / 2, HORIZON)
    bg.penup()
    bg.pensize(1)


# ============================================================
# Track generation: curves, hills, textures, roadside sprites
# ============================================================
def make_track():
    track = []
    curve = 0.0
    target = 0.0

    for i in range(TRACK_LEN):
        # Smooth random curve sections
        if i % 45 == 0:
            target = random.choice([
                0.0, 0.0, 0.0,
                0.035, -0.035,
                0.065, -0.065,
                0.09, -0.09
            ])
        curve += (target - curve) * 0.035

        # Gentle procedural hills
        y = (110 * math.sin(i * 0.017) +
             70 * math.sin(i * 0.0053 + 1.7) +
             35 * math.sin(i * 0.031 + 0.5))

        # Roadside decorations
        decor = []
        if i > 15 and random.random() < 0.16:
            side = random.choice([-2.6, -1.9, -1.45, 1.45, 1.9, 2.6])
            kind = random.choice(["palm", "tree", "rock", "bush", "tree", "palm"])
            decor.append((side, kind, random.randrange(10000)))

        if i % 83 == 10:
            decor.append((random.choice([-1.8, 1.8]), "billboard", random.randrange(10000)))

        # Procedural texture variation per segment
        band = (i // 3) % 2
        base_grass = (74, 170, 74) if band == 0 else (56, 144, 56)
        grass = tuple(clamp(c + random.randint(-9, 9), 0, 255) for c in base_grass)

        base_road = (102, 102, 110) if (i // 2) % 2 == 0 else (88, 88, 96)
        road = tuple(clamp(c + random.randint(-7, 7), 0, 255) for c in base_road)

        rumble = (222, 64, 64) if (i // 4) % 2 == 0 else (235, 235, 235)
        lane = ((i // 3) % 2) == 0

        track.append({
            "curve": curve,
            "y": y,
            "decor": decor,
            "grass": grass,
            "road": road,
            "rumble": rumble,
            "lane": lane,
        })

    return track


track = make_track()

CAR_COLORS = [
    (210, 70, 70),
    (70, 120, 220),
    (240, 180, 50),
    (120, 200, 120),
    (220, 120, 240),
    (90, 200, 220),
]

cars = []
for n in range(12):
    cars.append({
        "pos": (20 + n * (TRACK_LEN // 12) + random.uniform(-12, 12)) % TRACK_LEN,
        "offset": random.choice([-0.62, -0.35, 0.35, 0.62]),
        "speed": random.uniform(7.0, 14.0),
        "color": random.choice(CAR_COLORS),
        "variant": random.randrange(10000),
    })

state = {
    "pos": 0.0,
    "player_x": 0.0,       # -1..1 is on road
    "speed": 0.0,
    "distance": 0.0,
    "lap": 1,
    "time": 0.0,
    "tilt": 0.0,
    "last": time.perf_counter(),
}

keys = {"left": False, "right": False, "up": False, "down": False}


def bind(key, name):
    screen.onkeypress(lambda n=name: keys.update({n: True}), key)
    if hasattr(screen, "onkeyrelease"):
        screen.onkeyrelease(lambda n=name: keys.update({n: False}), key)


for k, name in [
    ("Left", "left"), ("Right", "right"), ("Up", "up"), ("Down", "down"),
    ("a", "left"), ("d", "right"), ("w", "up"), ("s", "down"),
    ("space", "down"),
]:
    bind(k, name)

screen.listen()


# ============================================================
# Procedural sprite functions
# ============================================================
def draw_palm(x, y, s, variant):
    if s <= 0.02:
        return

    lean = 10.0 * math.sin(variant * 0.17) + 6.0 * math.sin(variant * 0.043)
    trunk = [
        (-6, 0), (6, 0),
        (4, 42), (lean + 7, 80),
        (lean, 92), (lean - 7, 80),
        (-4, 42)
    ]
    draw_shape(x, y, s, trunk, shade((115, 75, 45), 0.9 + 0.2 * math.sin(variant)))

    top_x = x + lean * s
    top_y = y + 88 * s

    leaf_angles = [-2.5, -1.6, -0.6, 0.5, 1.6, 2.5]
    for i, a in enumerate(leaf_angles):
        a += 0.12 * math.sin(variant * 0.31 + i)
        length = 42.0 + 12.0 * math.sin(variant * 0.7 + i * 1.7)
        if length < 26:
            length = 26

        leaf = [(0, 0), (length * 0.45, -7), (length, 0), (length * 0.5, 8)]
        col = shade((35, 150, 55), 0.75 + 0.25 * (i % 2) + 0.08 * math.sin(variant + i))
        draw_shape(top_x, top_y, s, leaf, col, angle=a)

    if s > 0.25:
        pen.goto(top_x, top_y)
        pen.dot(max(2, int(7 * s)), (70, 45, 25))


def draw_tree(x, y, s, variant):
    if s <= 0.02:
        return

    trunk_col = shade((100, 65, 38), 0.9 + 0.2 * math.sin(variant))
    draw_shape(x, y, s, [(-6, 0), (6, 0), (4, 22), (-4, 22)], trunk_col)

    g = (35, 125 + int(abs(variant) % 45), 45)
    layers = [
        (40, 16, 60, 0.75),
        (31, 38, 78, 0.95),
        (22, 60, 96, 1.15),
    ]

    for w, h0, h1, f in layers:
        draw_shape(x, y, s, [(-w, h0), (w, h0), (0, h1)], shade(g, f))


def draw_rock(x, y, s, variant):
    if s <= 0.02:
        return

    g = 105 + (variant % 50)
    base = (g, g, g + 5)

    pts = [(-30, 0), (30, 0), (38, 12), (14, 26), (-16, 22), (-36, 10)]
    draw_shape(x, y, s, pts, shade(base, 0.95))

    highlight = [(-12, 5), (10, 8), (4, 18), (-10, 16)]
    draw_shape(x, y, s, highlight, shade(base, 1.25))


def draw_bush(x, y, s, variant):
    if s <= 0.02:
        return

    g = (40, 135, 55)
    blobs = [
        (-12, 7, 16, 0.8),
        (10, 8, 18, 1.0),
        (0, 15, 14, 1.2),
    ]

    for dx, dy, r, f in blobs:
        pen.goto(x + dx * s, y + dy * s)
        pen.dot(max(1, int(r * s * 2.0)), shade(g, f + 0.1 * math.sin(variant + dx)))


def draw_billboard(x, y, s, variant):
    if s <= 0.02:
        return

    post = (95, 95, 105)
    draw_shape(x, y, s, [(-18, 0), (-12, 0), (-13, 26), (-19, 26)], post)
    draw_shape(x, y, s, [(12, 0), (18, 0), (19, 26), (13, 26)], post)

    panel = mix((235, 235, 240), (255, 200, 70), (variant % 100) / 100.0)
    draw_shape(x, y, s, [(-42, 22), (42, 22), (42, 56), (-42, 56)], panel)
    draw_shape(x, y, s, [(-37, 26), (37, 26), (37, 52), (-37, 52)], shade(panel, 0.82))

    for i in range(3):
        sx = -24 + i * 18
        draw_shape(x, y, s, [(sx, 30), (sx + 8, 30), (sx + 8, 48), (sx, 48)], shade(panel, 0.65))

    if s > 0.18:
        pen.goto(x, y + 39 * s)
        pen.dot(max(2, int(10 * s)), (210, 60, 60))


def draw_enemy_car(x, y, s, color, variant):
    if s <= 0.03:
        return

    dark = shade(color, 0.62)
    glass = (115, 165, 205)

    # Shadow
    fill_poly(
        pen,
        [(x - 50 * s, y + 1 * s), (x + 50 * s, y + 1 * s),
         (x + 40 * s, y + 8 * s), (x - 40 * s, y + 8 * s)],
        (18, 18, 18)
    )

    # Wheels
    for sx in (-1, 1):
        wx = x + sx * 38 * s
        fill_poly(
            pen,
            [(wx - 9 * s, y), (wx + 9 * s, y),
             (wx + 9 * s, y + 14 * s), (wx - 9 * s, y + 14 * s)],
            (22, 22, 22)
        )

    # Body
    fill_poly(
        pen,
        [(x - 44 * s, y + 5 * s), (x + 44 * s, y + 5 * s),
         (x + 37 * s, y + 34 * s), (x - 37 * s, y + 34 * s)],
        color
    )

    # Bumper
    fill_poly(
        pen,
        [(x - 46 * s, y + 3 * s), (x + 46 * s, y + 3 * s),
         (x + 43 * s, y + 13 * s), (x - 43 * s, y + 13 * s)],
        dark
    )

    # Cabin / window
    fill_poly(
        pen,
        [(x - 27 * s, y + 32 * s), (x + 27 * s, y + 32 * s),
         (x + 19 * s, y + 50 * s), (x - 19 * s, y + 50 * s)],
        shade(color, 0.48)
    )
    fill_poly(
        pen,
        [(x - 22 * s, y + 34 * s), (x + 22 * s, y + 34 * s),
         (x + 16 * s, y + 46 * s), (x - 16 * s, y + 46 * s)],
        glass
    )

    # Tail lights
    light = (255, 90, 80) if variant % 3 else (190, 35, 35)
    for sx in (-1, 1):
        lx = x + sx * 32 * s
        fill_poly(
            pen,
            [(lx - 6 * s, y + 18 * s), (lx + 6 * s, y + 18 * s),
             (lx + 6 * s, y + 26 * s), (lx - 6 * s, y + 26 * s)],
            light
        )

    # Sometimes a spoiler
    if variant % 4 == 0:
        fill_poly(
            pen,
            [(x - 32 * s, y + 36 * s), (x + 32 * s, y + 36 * s),
             (x + 34 * s, y + 42 * s), (x - 34 * s, y + 42 * s)],
            dark
        )


def draw_decor(kind, x, y, s, variant):
    if kind == "palm":
        draw_palm(x, y, s, variant)
    elif kind == "tree":
        draw_tree(x, y, s, variant)
    elif kind == "rock":
        draw_rock(x, y, s, variant)
    elif kind == "bush":
        draw_bush(x, y, s, variant)
    elif kind == "billboard":
        draw_billboard(x, y, s, variant)


def draw_player_car(x, y, steer, braking, offroad, t):
    angle = -steer * 0.10

    bounce = math.sin(t * 24.0) * min(2.0, state["speed"] * 0.08)
    if offroad:
        bounce += math.sin(t * 55.0) * min(3.0, state["speed"] * 0.25)
    y += bounce

    body = (215, 45, 45)
    dark = shade(body, 0.58)
    glass = (120, 185, 225)

    # Shadow
    fill_poly(
        pen,
        [(x - 92, y - 6), (x + 92, y - 6),
         (x + 72, y + 10), (x - 72, y + 10)],
        (15, 15, 15)
    )

    # Wheels
    for sx in (-1, 1):
        pts = [
            (sx * 70 - 14, 0), (sx * 70 + 14, 0),
            (sx * 70 + 14, 26), (sx * 70 - 14, 26)
        ]
        draw_shape(x, y, 1.0, pts, (20, 20, 20), angle)

    # Body
    draw_shape(x, y, 1.0, [(-78, 8), (78, 8), (66, 56), (-66, 56)], body, angle)

    # Bumper
    draw_shape(x, y, 1.0, [(-82, 4), (82, 4), (78, 20), (-78, 20)], dark, angle)

    # Cabin
    draw_shape(x, y, 1.0, [(-50, 54), (50, 54), (36, 84), (-36, 84)], shade(body, 0.45), angle)
    draw_shape(x, y, 1.0, [(-42, 56), (42, 56), (32, 78), (-32, 78)], glass, angle)

    # Spoiler
    draw_shape(x, y, 1.0, [(-74, 60), (74, 60), (80, 70), (-80, 70)], dark, angle)

    # Tail lights
    light = (255, 110, 90) if braking else (180, 30, 30)
    for sx in (-1, 1):
        pts = [
            (sx * 52 - 8, 32), (sx * 52 + 8, 32),
            (sx * 52 + 8, 44), (sx * 52 - 8, 44)
        ]
        draw_shape(x, y, 1.0, pts, light, angle)

    # Exhaust flicker
    if state["speed"] > 1 and not braking:
        pen.goto(x - 28, y + 4)
        pen.dot(4, (130, 130, 130))
        pen.goto(x + 28, y + 4)
        pen.dot(4, (130, 130, 130))


def draw_hud():
    hud.clear()
    hud.pensize(1)
    hud.penup()

    hud.pencolor((245, 245, 255))
    hud.goto(-WIDTH / 2 + 16, HEIGHT / 2 - 36)
    hud.write(
        f"SPEED {int(state['speed'] * 12):3d} km/h   "
        f"LAP {state['lap']}   TIME {state['time']:06.1f}",
        font=("Courier", 14, "bold")
    )

    # Speed bar background
    hud.goto(-WIDTH / 2 + 16, HEIGHT / 2 - 56)
    hud.pensize(10)
    hud.pencolor((70, 70, 80))
    hud.pendown()
    hud.goto(-WIDTH / 2 + 216, HEIGHT / 2 - 56)
    hud.penup()

    # Speed bar fill
    if state["speed"] > 0.2:
        hud.goto(-WIDTH / 2 + 16, HEIGHT / 2 - 56)
        hud.pendown()
        hud.pencolor((255, 90, 80) if state["speed"] > MAX_SPEED * 0.85 else (255, 200, 80))
        hud.goto(-WIDTH / 2 + 16 + 200 * state["speed"] / MAX_SPEED, HEIGHT / 2 - 56)
        hud.penup()

    hud.pensize(1)
    hud.pencolor((220, 220, 230))
    hud.goto(-WIDTH / 2 + 16, -HEIGHT / 2 + 12)
    hud.write("ARROWS / WASD drive, SPACE brake", font=("Courier", 12, "bold"))


# ============================================================
# Main game loop
# ============================================================
def update():
    st = state

    now = time.perf_counter()
    dt = now - st["last"]
    if dt <= 0.0:
        dt = 0.001
    if dt > 0.05:
        dt = 0.05
    st["last"] = now

    # Input / steering visual smoothing
    steer = 0
    if keys["left"]:
        steer -= 1
    if keys["right"]:
        steer += 1
    st["tilt"] += (steer - st["tilt"]) * min(1.0, 8.0 * dt)

    base_idx = int(st["pos"]) % TRACK_LEN
    current_curve = track[base_idx]["curve"]

    # Throttle / brake
    if keys["up"]:
        st["speed"] += 14.0 * dt
    elif keys["down"]:
        st["speed"] -= 30.0 * dt
    else:
        st["speed"] -= 5.0 * dt

    # Steering and centrifugal drift
    st["player_x"] += steer * dt * (0.7 + st["speed"] * 0.085)
    st["player_x"] -= current_curve * st["speed"] * dt * 1.15

    # Off-road penalty
    offroad = abs(st["player_x"]) > 1.05
    if offroad:
        st["speed"] -= 20.0 * dt
        if st["speed"] > 9.0:
            st["speed"] = max(9.0, st["speed"] - 30.0 * dt)
        st["player_x"] = clamp(st["player_x"], -1.75, 1.75)
    else:
        st["player_x"] = clamp(st["player_x"], -2.3, 2.3)

    st["speed"] = clamp(st["speed"], 0.0, MAX_SPEED)

    # Update traffic cars
    for car in cars:
        car["pos"] = (car["pos"] + car["speed"] * dt) % TRACK_LEN

    # Simple collisions
    for car in cars:
        rel = car["pos"] - st["pos"]
        if rel < 0:
            rel += TRACK_LEN
        if rel > TRACK_LEN / 2:
            rel -= TRACK_LEN

        if 0.0 < rel < 0.85 and abs(st["player_x"] - car["offset"]) < 0.42:
            if st["speed"] > car["speed"]:
                st["speed"] = car["speed"] * 0.55
            st["player_x"] += (st["player_x"] - car["offset"]) * 3.0 * dt
            car["pos"] = (st["pos"] + 0.95) % TRACK_LEN

        elif -0.6 < rel < 0.0 and car["speed"] > st["speed"] + 2.0:
            st["speed"] = min(MAX_SPEED, st["speed"] + 3.0 * dt)

    # Move player
    st["pos"] += st["speed"] * dt
    if st["pos"] >= TRACK_LEN:
        st["pos"] -= TRACK_LEN
        st["lap"] += 1

    st["distance"] += st["speed"] * dt
    st["time"] += dt

    # ------------------------------------------------------------
    # Projection for this frame
    # ------------------------------------------------------------
    base = int(st["pos"]) % TRACK_LEN
    frac = st["pos"] - int(st["pos"])

    zs = []
    ys = []
    centers = []
    halfs = []

    x = 0.0
    dx = 0.0
    prev_z = NEAR

    for i in range(DRAW + 1):
        z = i - frac
        if z < NEAR:
            z = NEAR

        if i == 0:
            dz = 0.0
        else:
            dz = z - prev_z
            if dz < 0.0:
                dz = 0.0
            cv = track[(base + i - 1) % TRACK_LEN]["curve"]
            dx += cv * dz
            x += dx * dz

        seg_y = track[(base + i) % TRACK_LEN]["y"]
        p = 1.0 / z
        y = HORIZON - (CAM_HEIGHT - seg_y) * p * Y_SCALE
        half = ROAD_PROJ * p
        center = x * p * CURVE_PROJ - st["player_x"] * half

        zs.append(z)
        ys.append(y)
        centers.append(center)
        halfs.append(half)

        prev_z = z

    def interp(zq):
        """Interpolate road projection at arbitrary distance zq."""
        if zq < zs[0] or zq > zs[-1]:
            return None

        lo = 0
        hi = DRAW
        while lo < hi:
            mid = (lo + hi) // 2
            if zq <= zs[mid]:
                hi = mid
            else:
                lo = mid + 1

        i = max(0, lo - 1)
        if i >= DRAW:
            i = DRAW - 1

        denom = zs[i + 1] - zs[i]
        if denom <= 1e-6:
            return (ys[i + 1], centers[i + 1], halfs[i + 1], halfs[i + 1] / ROAD_PROJ, i)

        t = (zq - zs[i]) / denom
        t = clamp(t, 0.0, 1.0)

        y = ys[i] + (ys[i + 1] - ys[i]) * t
        c = centers[i] + (centers[i + 1] - centers[i]) * t
        h = halfs[i] + (halfs[i + 1] - halfs[i]) * t

        return (y, c, h, h / ROAD_PROJ, i)

    # Bucket sprites per road slice so nearer road can occlude far sprites.
    buckets = [[] for _ in range(DRAW)]

    # Roadside decorations
    for i in range(DRAW):
        idx = (base + i) % TRACK_LEN
        seg = track[idx]
        if not seg["decor"]:
            continue

        for side, kind, variant in seg["decor"]:
            zq = i + 0.5 - frac
            if zq < NEAR:
                continue

            pr = interp(zq)
            if pr is None:
                continue

            y, c, h, p, bucket_i = pr
            buckets[bucket_i].append({
                "z": zq,
                "x": c + side * h,
                "y": y,
                "s": p * SPRITE_SCALE,
                "kind": kind,
                "variant": variant,
            })

    # Traffic cars
    for car in cars:
        rel = car["pos"] - st["pos"]
        if rel < 0:
            rel += TRACK_LEN
        if rel < NEAR or rel > DRAW:
            continue

        pr = interp(rel)
        if pr is None:
            continue

        y, c, h, p, bucket_i = pr
        buckets[bucket_i].append({
            "z": rel,
            "x": c + car["offset"] * h,
            "y": y,
            "s": p * CAR_SCALE,
            "kind": "car",
            "color": car["color"],
            "variant": car["variant"],
        })

    # ------------------------------------------------------------
    # Render frame
    # ------------------------------------------------------------
    pen.clear()

    # Draw road far to near
    for i in range(DRAW - 1, -1, -1):
        y0 = ys[i]
        y1 = ys[i + 1]

        if y1 <= y0:
            continue
        if y1 < -HEIGHT / 2 - 40:
            continue

        idx = (base + i) % TRACK_LEN
        seg = track[idx]

        height = y1 - y0
        if height <= 0.0:
            height = 0.75
        mid = (y0 + y1) * 0.5

        # Grass strip as a thick horizontal line
        pen.pensize(max(1, int(height) + 1))
        pen.pencolor(seg["grass"])
        pen.penup()
        pen.goto(-WIDTH / 2, mid)
        pen.pendown()
        pen.goto(WIDTH / 2, mid)
        pen.pensize(1)

        c0 = centers[i]
        c1 = centers[i + 1]
        h0 = halfs[i]
        h1 = halfs[i + 1]

        # Rumble strips
        rb0 = max(3.0, h0 * 0.14)
        rb1 = max(2.0, h1 * 0.14)
        fill_poly(
            pen,
            [(c0 - h0 - rb0, y0), (c0 + h0 + rb0, y0),
             (c1 + h1 + rb1, y1), (c1 - h1 - rb1, y1)],
            seg["rumble"]
        )

        # Asphalt
        fill_poly(
            pen,
            [(c0 - h0, y0), (c0 + h0, y0),
             (c1 + h1, y1), (c1 - h1, y1)],
            seg["road"]
        )

        # Center lane dash
        if seg["lane"]:
            lw0 = max(1.5, h0 * 0.03)
            lw1 = max(1.0, h1 * 0.03)
            fill_poly(
                pen,
                [(c0 - lw0, y0), (c0 + lw0, y0),
                 (c1 + lw1, y1), (c1 - lw1, y1)],
                (235, 235, 235)
            )

        # Sprites in this slice
        if buckets[i]:
            for spr in sorted(buckets[i], key=lambda d: d["z"], reverse=True):
                if spr["y"] < -HEIGHT / 2 - 80 or spr["s"] <= 0.02:
                    continue

                if spr["kind"] == "car":
                    draw_enemy_car(spr["x"], spr["y"], spr["s"], spr["color"], spr["variant"])
                else:
                    draw_decor(spr["kind"], spr["x"], spr["y"], spr["s"], spr["variant"])

    # Player car and HUD
    draw_player_car(
        0,
        -HEIGHT / 2 + 88,
        st["tilt"],
        keys["down"],
        abs(st["player_x"]) > 1.05,
        st["time"]
    )

    draw_hud()

    screen.update()
    screen.ontimer(update, 16)


# ============================================================
# Start
# ============================================================
draw_background()
screen.update()
update()
screen.mainloop()