
import pygame
import random
import math

pygame.init()

# ---------- SETTINGS ----------
W, H = 900, 650
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("CYBER STRIKE: NEON WARFARE")
clock = pygame.time.Clock()

BLACK = (5, 5, 18)
CYAN = (0, 240, 255)
PINK = (255, 30, 140)
PURPLE = (150, 50, 255)
WHITE = (240, 245, 255)
GREEN = (40, 255, 120)
RED = (255, 65, 75)

font = pygame.font.SysFont("consolas", 22, bold=True)
big_font = pygame.font.SysFont("consolas", 48, bold=True)

# ---------- GAME STATE ----------
player = pygame.Rect(W // 2 - 20, H - 90, 40, 35)
player_speed = 6
health = 100
score = 0
wave = 1
boss = None
boss_health = 0

bullets = []
enemy_bullets = []
enemies = []
particles = []
powerups = []

shoot_cooldown = 0
enemy_timer = 0
power_timer = 0
invincible = 0
game_over = False
victory = False
paused = False

# Starfield
stars = [
    [random.randrange(W), random.randrange(H),
     random.choice([1, 1, 2, 3])]
    for _ in range(100)
]


def draw_text(text, x, y, color=WHITE, font_obj=font):
    img = font_obj.render(str(text), True, color)
    screen.blit(img, (x, y))


def explosion(x, y, color, amount=14):
    for _ in range(amount):
        angle = random.random() * math.tau
        speed = random.uniform(1, 5)
        particles.append([
            float(x), float(y),
            math.cos(angle) * speed,
            math.sin(angle) * speed,
            random.randint(15, 30), color
        ])


def spawn_enemy():
    kind = random.choices(
        ["normal", "fast", "tank"], weights=[6, 3, 2]
    )[0]

    size = 28 if kind != "tank" else 42
    enemy = {
        "rect": pygame.Rect(
            random.randint(10, W - size - 10), -size,
            size, size
        ),
        "kind": kind,
        "hp": 1 if kind != "tank" else 4,
        "max_hp": 1 if kind != "tank" else 4,
        "speed": (
            random.uniform(2.2, 3.5)
            if kind == "fast"
            else random.uniform(1.1, 2.0)
        ),
        "phase": random.random() * math.tau
    }
    enemies.append(enemy)


def spawn_boss():
    global boss, boss_health
    boss = pygame.Rect(W // 2 - 85, 55, 170, 75)
    boss_health = 40 + wave * 10


def reset_game():
    global player, health, score, wave, boss, boss_health
    global bullets, enemy_bullets, enemies, particles, powerups
    global shoot_cooldown, enemy_timer, power_timer
    global invincible, game_over, victory, paused

    player = pygame.Rect(W // 2 - 20, H - 90, 40, 35)
    health = 100
    score = 0
    wave = 1
    boss = None
    boss_health = 0
    bullets = []
    enemy_bullets = []
    enemies = []
    particles = []
    powerups = []
    shoot_cooldown = 0
    enemy_timer = 0
    power_timer = 0
    invincible = 0
    game_over = False
    victory = False
    paused = False


def draw_player():
    if invincible > 0 and invincible % 6 < 3:
        return

    # Neon ship
    points = [
        (player.centerx, player.top),
        (player.left, player.bottom),
        (player.centerx, player.bottom - 10),
        (player.right, player.bottom)
    ]

    pygame.draw.polygon(screen, CYAN, points, 3)
    pygame.draw.line(
        screen, PINK,
        (player.centerx, player.bottom - 7),
        (player.centerx, player.bottom + 7), 3
    )


def draw_boss():
    if boss is None:
        return

    pygame.draw.rect(screen, PURPLE, boss, border_radius=12)
    pygame.draw.rect(screen, PINK, boss, 3, border_radius=12)

    pygame.draw.circle(screen, RED, (boss.centerx, boss.centery), 18)
    pygame.draw.circle(screen, WHITE, (boss.centerx, boss.centery), 7)

    bar_width = 300
    ratio = max(0, boss_health) / (40 + wave * 10)
    pygame.draw.rect(screen, (50, 30, 50),
                     (W // 2 - bar_width // 2, 18, bar_width, 12))
    pygame.draw.rect(screen, PINK,
                     (W // 2 - bar_width // 2, 18,
                      int(bar_width * ratio), 12))
    draw_text("BOSS", W // 2 - 28, 34, PINK)


def draw_background():
    screen.fill(BLACK)

    for star in stars:
        star[1] += star[2]
        if star[1] >= H:
            star[0] = random.randrange(W)
            star[1] = 0

        color = (40, 70, 110) if star[2] < 3 else CYAN
        pygame.draw.circle(
            screen, color, (star[0], star[1]), star[2] // 2 + 1
        )

    # Neon grid near bottom
    for x in range(0, W, 60):
        pygame.draw.line(screen, (15, 20, 50),
                         (x, H - 130), (x, H))
    for y in range(H - 130, H, 25):
        pygame.draw.line(screen, (15, 20, 50),
                         (0, y), (W, y))


def update_particles():
    for p in particles[:]:
        p[0] += p[2]
        p[1] += p[3]
        p[4] -= 1

        if p[4] <= 0:
            particles.remove(p)
            continue

        radius = max(1, p[4] // 6)
        pygame.draw.circle(
            screen, p[5],
            (int(p[0]), int(p[1])), radius
        )


def main():
    global health, score, wave, boss, boss_health
    global shoot_cooldown, enemy_timer, power_timer
    global invincible, game_over, victory, paused

    running = True

    while running:
        clock.tick(60)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False

                if event.key == pygame.K_p and not game_over:
                    paused = not paused

                if event.key == pygame.K_r and (game_over or victory):
                    reset_game()

                if event.key == pygame.K_RETURN and (game_over or victory):
                    reset_game()

        keys = pygame.key.get_pressed()

        if not game_over and not victory and not paused:

            # Movement
            dx = int(keys[pygame.K_RIGHT] or keys[pygame.K_d]) \
                - int(keys[pygame.K_LEFT] or keys[pygame.K_a])
            dy = int(keys[pygame.K_DOWN] or keys[pygame.K_s]) \
                - int(keys[pygame.K_UP] or keys[pygame.K_w])

            player.x += dx * player_speed
            player.y += dy * player_speed

            player.clamp_ip(screen.get_rect())

            # Shooting
            if shoot_cooldown > 0:
                shoot_cooldown -= 1

            if (keys[pygame.K_SPACE] or keys[pygame.K_j]) \
                    and shoot_cooldown == 0:
                bullets.append(
                    pygame.Rect(player.centerx - 3, player.top - 15, 6, 18)
                )
                bullets.append(
                    pygame.Rect(player.centerx - 13, player.top, 4, 13)
                )
                bullets.append(
                    pygame.Rect(player.centerx + 9, player.top, 4, 13)
                )
                shoot_cooldown = 10

            # Wave and boss logic
            if boss is None and not enemies:
                if wave > 1:
                    health = min(100, health + 15)

                if wave % 5 == 0:
                    spawn_boss()
                else:
                    # Each wave brings more enemies
                    for _ in range(min(4 + wave * 2, 24)):
                        spawn_enemy()

            # Enemy spawning
            if boss is None:
                enemy_timer += 1

            if enemy_timer >= max(12, 42 - wave * 2) and boss is None:
                enemy_timer = 0
                if len(enemies) < min(5 + wave, 18):
                    spawn_enemy()

            # Bullets
            for b in bullets[:]:
                b.y -= 10
                if b.bottom < 0:
                    bullets.remove(b)

            # Enemy movement
            for e in enemies[:]:
                rect = e["rect"]
                rect.y += e["speed"]
                rect.x += math.sin(pygame.time.get_ticks() / 250
                                   + e["phase"]) * 1.4

                if rect.top > H:
                    enemies.remove(e)
                    health -= 8
                    continue

                if rect.colliderect(player):
                    enemies.remove(e)
                    explosion(rect.centerx, rect.centery, RED)
                    if invincible == 0:
                        health -= 15
                        invincible = 60

            # Enemy shooting
            if random.random() < 0.025 + wave * 0.002:
                if enemies:
                    e = random.choice(enemies)
                    enemy_bullets.append(
                        pygame.Rect(e["rect"].centerx - 3,
                                    e["rect"].bottom, 6, 12)
                    )

            # Boss movement and attacks
            if boss is not None:
                boss.x += round(math.sin(
                    pygame.time.get_ticks() / 500
                ) * 4)

                boss.clamp_ip(pygame.Rect(0, 25, W, H))

                if random.random() < 0.07:
                    for offset in [-55, 0, 55]:
                        enemy_bullets.append(
                            pygame.Rect(boss.centerx + offset,
                                        boss.bottom, 8, 15)
                        )

                if boss_health <= 0:
                    explosion(boss.centerx, boss.centery, PURPLE, 70)
                    score += 1000
                    boss = None
                    wave += 1
                    health = min(100, health + 25)

            # Enemy bullets
            for b in enemy_bullets[:]:
                b.y += 6 + wave * 0.15

                if b.top > H:
                    enemy_bullets.remove(b)
                elif b.colliderect(player):
                    enemy_bullets.remove(b)
                    if invincible == 0:
                        health -= 10
                        invincible = 60

            # Bullet-enemy collisions
            for b in bullets[:]:
                hit = False

                for e in enemies[:]:
                    if b.colliderect(e["rect"]):
                        e["hp"] -= 1
                        hit = True

                        if e["hp"] <= 0:
                            explosion(
                                e["rect"].centerx,
                                e["rect"].centery, PINK
                            )
                            score += 30 if e["kind"] != "tank" else 70
                            enemies.remove(e)

                            if random.random() < 0.14:
                                powerups.append(
                                    pygame.Rect(
                                        e["rect"].centerx - 10,
                                        e["rect"].centery - 10,
                                        20, 20
                                    )
                                )
                        break

                    if boss is not None and b.colliderect(boss):
                        boss_health -= 1
                        score += 2
                        hit = True
                        break

                if hit and b in bullets:
                    bullets.remove(b)

            # Power-ups
            for p in powerups[:]:
                p.y += 2

                if p.top > H:
                    powerups.remove(p)
                elif p.colliderect(player):
                    health = min(100, health + 25)
                    score += 50
                    powerups.remove(p)
                    explosion(p.centerx, p.centery, GREEN, 20)

            if invincible > 0:
                invincible -= 1

            if health <= 0:
                health = 0
                game_over = True

            # Reach wave 15 to win
            if wave > 15:
                victory = True

        # ---------- DRAW ----------
        draw_background()

        for b in bullets:
            pygame.draw.rect(screen, CYAN, b, border_radius=3)
            pygame.draw.circle(screen, WHITE, b.center, 3)

        for b in enemy_bullets:
            pygame.draw.rect(screen, RED, b, border_radius=3)

        for e in enemies:
            rect = e["rect"]
            color = (
                PINK if e["kind"] == "fast"
                else PURPLE if e["kind"] == "tank"
                else RED
            )
            pygame.draw.polygon(
                screen, color,
                [(rect.centerx, rect.bottom),
                 (rect.left, rect.top),
                 (rect.right, rect.top)]
            )
            pygame.draw.polygon(
                screen, WHITE,
                [(rect.centerx, rect.bottom),
                 (rect.left, rect.top),
                 (rect.right, rect.top)], 2
            )

            if e["max_hp"] > 1:
                pygame.draw.rect(
                    screen, RED,
                    (rect.x, rect.y - 8, rect.width, 4)
                )
                pygame.draw.rect(
                    screen, GREEN,
                    (rect.x, rect.y - 8,
                     rect.width * e["hp"] / e["max_hp"], 4)
                )

        for p in powerups:
            pygame.draw.circle(screen, GREEN, p.center, 12, 2)
            pygame.draw.line(screen, GREEN,
                             (p.centerx, p.top + 5),
                             (p.centerx, p.bottom - 5), 3)
            pygame.draw.line(screen, GREEN,
                             (p.left + 5, p.centery),
                             (p.right - 5, p.centery), 3)

        draw_boss()
        draw_player()
        update_particles()

        # HUD
        pygame.draw.rect(screen, (45, 20, 35), (20, 20, 205, 18))
        pygame.draw.rect(
            screen, GREEN if health > 30 else RED,
            (20, 20, int(205 * health / 100), 18)
        )
        pygame.draw.rect(screen, WHITE, (20, 20, 205, 18), 2)

        draw_text(f"HP: {health}/100", 20, 43, GREEN)
        draw_text(f"SCORE: {score}", 20, 75, CYAN)
        draw_text(f"WAVE: {wave}", W - 150, 25, PINK)
        draw_text("SPACE: FIRE", W - 190, H - 55, CYAN)
        draw_text("WASD/ARROWS: MOVE", W - 290, H - 30, WHITE)

        if paused:
            draw_text("PAUSED", W // 2 - 100, H // 2 - 40,
                      CYAN, big_font)
            draw_text("Press P to resume", W // 2 - 110,
                      H // 2 + 20)

        if game_over or victory:
            overlay = pygame.Surface((W, H), pygame.SRCALPHA)
            overlay.fill((0, 0, 10, 210))
            screen.blit(overlay, (0, 0))

            title = "YOU WIN!" if victory else "GAME OVER"
            color = CYAN if victory else RED

            title_img = big_font.render(title, True, color)
            screen.blit(title_img, title_img.get_rect(
                center=(W // 2, H // 2 - 70)
            ))

            draw_text(f"FINAL SCORE: {score}",
                      W // 2 - 105, H // 2, WHITE)
            draw_text("Press R or ENTER to play again",
                      W // 2 - 205, H // 2 + 50, CYAN)

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
