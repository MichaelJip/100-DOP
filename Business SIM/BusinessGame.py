"""
AI Business Simulation
-----------------------
Agent-based simulation: several AI-controlled businesses compete in a
shared market. Each tick, every business decides on price, production,
and marketing spend, then the market clears (demand gets allocated
across businesses based on price/marketing/reputation), and
capital updates based on profit/loss. Businesses that run out of
capital go bankrupt, and are occasionally replaced by new startups.

The decision logic in Business.decide() is intentionally simple and
rule-based right now -- it's written so you can later swap it out for
a learned policy (e.g. a small RL agent per business, state = market
signals, action = price/production/marketing deltas, reward = profit)
if you want to extend this toward the RL game AI stuff.

Controls:
  SPACE       pause / resume
  + / -       speed up / slow down simulation
  ESC         quit
"""

import pygame
import random
import sys
from dataclasses import dataclass, field
from typing import List

# ---------------- Config ----------------
WIDTH, HEIGHT = 1000, 650
FPS = 60
TICK_INTERVAL_MS = 500       # simulation tick every 0.5s at 1x speed
STARTING_CAPITAL = 10000.0
PRODUCTION_COST = 5.0        # cost per unit produced
FIXED_COST = 150.0           # per-tick overhead
BASE_DEMAND = 500.0          # total units the market wants per tick at a "fair" price
HISTORY_LEN = 200

COLORS = [
    (231, 76, 60), (52, 152, 219), (46, 204, 113), (241, 196, 15),
    (155, 89, 182), (26, 188, 156), (230, 126, 34), (149, 165, 166),
]

NAMES = [
    "Nusantara Co", "Delta Corp", "Horizon Inc", "Vertex Group",
    "Meridian Ltd", "Pinnacle Biz", "Solstice Co", "Zenith Corp",
]


@dataclass
class Business:
    name: str
    color: tuple
    capital: float = STARTING_CAPITAL
    price: float = 20.0
    production: float = 60.0
    marketing: float = 20.0
    reputation: float = 1.0
    history: List[float] = field(default_factory=list)
    alive: bool = True
    ticks_alive: int = 0

    def decide(self, market_avg_price: float, rng: random.Random) -> None:
        """Simple heuristic AI. Swap this out with a learned policy later."""
        if not self.alive:
            return
        drift = rng.uniform(-0.06, 0.06)
        if self.price > market_avg_price * 1.05:
            self.price *= 0.97  # too expensive relative to market, cut price
        elif self.price < market_avg_price * 0.9:
            self.price *= 1.03  # room to raise price
        self.price *= (1 + drift)
        self.price = max(5.0, self.price)

        target = self.production * (1.05 if rng.random() < 0.5 else 0.97)
        self.production = max(10.0, min(300.0, target))

        self.marketing = max(0.0, min(80.0, self.capital * 0.003))

    def apply_tick_result(self, revenue: float, cost: float) -> None:
        profit = revenue - cost
        self.capital += profit
        self.ticks_alive += 1
        self.history.append(self.capital)
        if len(self.history) > HISTORY_LEN:
            self.history.pop(0)
        if self.capital <= 0:
            self.alive = False


class Market:
    def __init__(self, businesses: List[Business], rng: random.Random):
        self.businesses = businesses
        self.rng = rng
        self.tick_count = 0

    def clear_tick(self) -> None:
        alive = [b for b in self.businesses if b.alive]
        if alive:
            avg_price = sum(b.price for b in alive) / len(alive)

            for b in alive:
                b.decide(avg_price, self.rng)

            demand_multiplier = 1 + self.rng.uniform(-0.15, 0.15)
            total_demand = BASE_DEMAND * demand_multiplier

            scores = []
            for b in alive:
                price_score = max(0.1, (avg_price * 1.4 - b.price))
                score = price_score * (1 + b.marketing / 100) * b.reputation
                scores.append(max(0.01, score))
            total_score = sum(scores)

            for b, score in zip(alive, scores):
                share = score / total_score
                demanded = total_demand * share
                units_sold = min(b.production, demanded)
                revenue = units_sold * b.price
                cost = b.production * PRODUCTION_COST + FIXED_COST + b.marketing
                b.apply_tick_result(revenue, cost)

                if demanded > b.production * 1.2:
                    b.reputation = min(1.5, b.reputation + 0.01)
                elif units_sold < b.production * 0.5:
                    b.reputation = max(0.5, b.reputation - 0.01)

        self.tick_count += 1

        # occasionally respawn a bankrupt business as a fresh startup
        for b in self.businesses:
            if not b.alive and self.rng.random() < 0.01:
                b.capital = STARTING_CAPITAL * 0.6
                avg_price_for_respawn = (
                    sum(x.price for x in self.businesses if x.alive) / max(1, len([x for x in self.businesses if x.alive]))
                    if any(x.alive for x in self.businesses) else 20.0
                )
                b.price = avg_price_for_respawn * self.rng.uniform(0.85, 1.05)
                b.production = 60.0
                b.marketing = 15.0
                b.reputation = 1.0
                b.alive = True
                b.history.clear()


def make_businesses(n: int = 6) -> List[Business]:
    rng = random.Random(42)
    businesses = []
    for i in range(n):
        b = Business(
            name=NAMES[i % len(NAMES)],
            color=COLORS[i % len(COLORS)],
            price=rng.uniform(15, 25),
            production=rng.uniform(40, 80),
        )
        businesses.append(b)
    return businesses


def draw(screen, font, small_font, businesses, market, paused, speed):
    screen.fill((18, 20, 26))

    title = font.render("AI Business Simulation", True, (240, 240, 245))
    screen.blit(title, (20, 15))
    info = small_font.render(
        f"Tick: {market.tick_count}   Speed: {speed}x   "
        f"[SPACE] pause  [+/-] speed  [ESC] quit",
        True, (150, 155, 165))
    screen.blit(info, (20, 45))

    # Capital-over-time chart
    chart_x, chart_y, chart_w, chart_h = 20, 80, 620, 300
    pygame.draw.rect(screen, (28, 30, 38), (chart_x, chart_y, chart_w, chart_h), border_radius=6)
    max_cap = max([max(b.history) if b.history else STARTING_CAPITAL for b in businesses] + [STARTING_CAPITAL])
    max_cap = max(max_cap, 1)
    for b in businesses:
        if len(b.history) < 2:
            continue
        pts = []
        for i, cap in enumerate(b.history):
            x = chart_x + (i / max(1, HISTORY_LEN - 1)) * chart_w
            y = chart_y + chart_h - (max(0, cap) / max_cap) * (chart_h - 10) - 5
            pts.append((x, y))
        color = b.color if b.alive else (80, 80, 80)
        pygame.draw.lines(screen, color, False, pts, 2)

    # Leaderboard
    table_x, table_y = 660, 80
    header = small_font.render(f"{'Business':<14}{'Capital':>10}{'Price':>8}{'Share':>7}", True, (200, 200, 210))
    screen.blit(header, (table_x, table_y))
    alive_biz = [b for b in businesses if b.alive]
    total_prod = sum(b.production for b in alive_biz) or 1
    sorted_biz = sorted(businesses, key=lambda b: b.capital, reverse=True)
    for i, b in enumerate(sorted_biz):
        y = table_y + 28 + i * 26
        status_color = b.color if b.alive else (90, 90, 90)
        pygame.draw.circle(screen, status_color, (table_x + 6, y + 8), 5)
        share = (b.production / total_prod * 100) if b.alive else 0
        label = f"{b.name:<14}{int(b.capital):>10}{b.price:>8.1f}{share:>6.1f}%"
        txt = small_font.render(label, True, (220, 220, 225) if b.alive else (110, 110, 110))
        screen.blit(txt, (table_x + 18, y))
        if not b.alive:
            bankrupt = small_font.render("BANKRUPT", True, (231, 76, 60))
            screen.blit(bankrupt, (table_x + 250, y))

    # Market map: bubble position = price/production, size = capital
    bubble_area_y = 400
    bubble_h = 220
    pygame.draw.rect(screen, (28, 30, 38), (20, bubble_area_y, 620, bubble_h), border_radius=6)
    label = small_font.render("Market Map (x=price, y=production)", True, (150, 155, 165))
    screen.blit(label, (28, bubble_area_y + 6))
    prices = [b.price for b in businesses]
    prods = [b.production for b in businesses]
    min_p, max_p = min(prices), (max(prices) if max(prices) != min(prices) else min(prices) + 1)
    min_q, max_q = min(prods), (max(prods) if max(prods) != min(prods) else min(prods) + 1)
    for b in businesses:
        if not b.alive:
            continue
        px = 60 + ((b.price - min_p) / max(1, (max_p - min_p))) * 520
        py = bubble_area_y + bubble_h - 30 - ((b.production - min_q) / max(1, (max_q - min_q))) * (bubble_h - 60)
        radius = max(6, min(28, int(b.capital / 800)))
        pygame.draw.circle(screen, b.color, (int(px), int(py)), radius)
        name_txt = small_font.render(b.name.split()[0], True, (200, 200, 205))
        screen.blit(name_txt, (px - 20, py + radius + 2))

    if paused:
        pause_txt = font.render("PAUSED", True, (241, 196, 15))
        screen.blit(pause_txt, (WIDTH // 2 - 60, HEIGHT - 40))

    pygame.display.flip()


def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("AI Business Simulation")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("consolas", 22)
    small_font = pygame.font.SysFont("consolas", 16)

    rng = random.Random(42)
    businesses = make_businesses(6)
    market = Market(businesses, rng)

    paused = False
    speed = 1
    last_tick = pygame.time.get_ticks()

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_SPACE:
                    paused = not paused
                elif event.key in (pygame.K_PLUS, pygame.K_EQUALS):
                    speed = min(8, speed + 1)
                elif event.key == pygame.K_MINUS:
                    speed = max(1, speed - 1)

        now = pygame.time.get_ticks()
        if not paused and now - last_tick >= TICK_INTERVAL_MS / speed:
            market.clear_tick()
            last_tick = now

        draw(screen, font, small_font, businesses, market, paused, speed)
        clock.tick(FPS)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()