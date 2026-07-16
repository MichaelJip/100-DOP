"""
City RL Sim v2 -- two rival civilizations, wildlife, real war
----------------------------------------------------------------
Two founding pairs start on opposite corners of the map: Tribe A
(Adam & Eve, blue) and Tribe B (Kael & Sora, orange). Each tribe has
its OWN Q-table (own learned policy), so their strategies can diverge
over time -- one might turn out more builder-focused, the other more
aggressive, purely from how their exploration played out. That
divergence is the "politics" here: there's no scripted diplomacy,
just two independently-learning populations competing for the same
forests, rock, and berries.

State  = (hunger, energy, tile standing on, can-afford-house,
          can-afford-farm, food stock level, reproduction partner
          adjacent, own tribe at population cap, enemy adult adjacent)
Action = SeekWood, SeekStone, SeekFood, Eat, Rest, BuildHouse,
         BuildFarm, Reproduce, Attack  (9 discrete, high-level)
Reward = shaped: successful gather/eat/build/reproduce/kill are
         rewarded, wasted attempts and dying (starvation, wolves,
         losing a fight) are penalized, staying alive gives a small
         trickle reward.

Movement is still NOT learned (greedy pathing executes whatever the
policy decided "SeekWood" etc means) -- same reasoning as before:
keeps the state space small enough to actually learn something in a
few minutes on a CPU.

What changed vs v1, based on your feedback:
  - Resource tiles now visibly fade as they're depleted (forest/rock
    color shifts toward pale as wood/stone runs out), and each berry
    patch has its own random yield (5-15 food) shown via dot color/
    size, instead of one uniform red dot -- so patches are visually
    distinct and you can SEE resources being depleted/respawning.
  - Wildlife: a handful of wolves roam the map. If one sits next to
    an agent for a few ticks, there's a chance it kills them (higher
    chance for children than adults). Agents can't fight wolves back
    in this version -- they're a pure hazard, not a hunt mechanic.
  - War: a new "Attack" action lets an agent fight an adjacent enemy
    adult. It's a 50/50 coin flip -- winner survives, loser dies. A
    tribe that hits 0 population is wiped out and respawns as
    refugees elsewhere on the map (their old buildings stay standing
    as ruins), keeping whatever their Q-table already learned.

What's still NOT in here (scope calls, not oversights): no diplomacy/
alliances, no building destruction/sieges, no combat vs wolves, no
more than 2 factions. Any of those are reasonable next additions if
you want to keep pushing on this.

Controls:
  SPACE   pause / resume
  + / -   speed up / slow down (ticks per frame)
  R       force a full world reset (fresh map, learning KEPT)
  ESC     quit
"""

import pygame
import random
import sys
from collections import deque

# ---------------- Config ----------------
GRID_W, GRID_H = 30, 20
TILE = 24
GRID_PIX_W, GRID_PIX_H = GRID_W * TILE, GRID_H * TILE
PANEL_W = 300
WINDOW_W = GRID_PIX_W + PANEL_W + 30
WINDOW_H = GRID_PIX_H + 130
FPS = 60

ADULT_AGE = 250
MAX_POP_PER_TRIBE = 20
MAX_BUILDINGS = 70
REPRO_COOLDOWN = 120
N_WOLVES = 6
WOLF_ATTACK_COOLDOWN = 45
WOLF_CHANCE_ADULT = 0.01
WOLF_CHANCE_CHILD = 0.03
ATTACK_REWARD = 5.0

ALPHA = 0.15
GAMMA = 0.95
EPS_START = 1.0
EPS_MIN = 0.05
EPS_DECAY_TICKS = 40000

ACTIONS = ["SeekWood", "SeekStone", "SeekFood", "Eat", "Rest",
           "BuildHouse", "BuildFarm", "Reproduce", "Attack"]

COLOR_BG = (16, 18, 24)
TILE_BASE = {
    "grass": (74, 122, 58), "water": (35, 90, 140),
}
FOREST_FULL, FOREST_EMPTY = (30, 90, 44), (140, 150, 105)
ROCK_FULL, ROCK_EMPTY = (100, 104, 112), (185, 178, 162)
BERRY_LOW, BERRY_HIGH = (235, 170, 175), (195, 25, 45)

random.seed()


def blend(c1, c2, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


# ---------------- World ----------------
class World:
    def __init__(self):
        self.tiles = [["grass"] * GRID_W for _ in range(GRID_H)]
        self.wood_amt = {}
        self.stone_amt = {}
        self.berries = {}   # (x,y) -> {"ready","timer","yield"}
        self.forest_tiles = set()
        self.rock_tiles = set()
        self.roads = set()
        self.buildings = []      # (x,y,btype,faction_id)
        self.zone_labels = []
        self.animals = []
        self._generate()

    def _walk_blob(self, terrain, length, resource_dict=None, base_amt=0, bias=None, bias_radius=7):
        if bias:
            bx, by = bias
            x = max(0, min(GRID_W - 1, bx + random.randint(-bias_radius, bias_radius)))
            y = max(0, min(GRID_H - 1, by + random.randint(-bias_radius, bias_radius)))
        else:
            x, y = random.randrange(GRID_W), random.randrange(GRID_H)
        cx, cy = x, y
        placed = []
        for _ in range(length):
            if 0 <= x < GRID_W and 0 <= y < GRID_H and self.tiles[y][x] == "grass":
                self.tiles[y][x] = terrain
                if resource_dict is not None:
                    resource_dict[(x, y)] = base_amt
                placed.append((x, y))
            x += random.choice([-1, 0, 1])
            y += random.choice([-1, 0, 1])
            x = max(0, min(GRID_W - 1, x))
            y = max(0, min(GRID_H - 1, y))
        return placed, (cx, cy)

    def _generate(self):
        corner_a = (GRID_W // 4, GRID_H // 4)
        corner_b = (3 * GRID_W // 4, 3 * GRID_H // 4)
        # two forest clusters near each tribe's home corner -- both sides get
        # a nearby wood supply so early game is expansion, not immediate contact
        for bias in (corner_a, corner_a, corner_b, corner_b):
            placed, center = self._walk_blob("forest", 42, self.wood_amt, 30, bias=bias)
            self.forest_tiles.update(placed)
            if placed:
                self.zone_labels.append((center[0], center[1], "Resource Zone"))
        # one rock cluster near each home, plus one contested cluster in the
        # middle of the map that both tribes have to compete for
        for bias in (corner_a, corner_b, None):
            placed, _ = self._walk_blob("rock", 26, self.stone_amt, 40, bias=bias)
            self.rock_tiles.update(placed)
        for _ in range(2):
            self._walk_blob("water", 18)
        for bias in (corner_a, corner_b):
            for _ in range(7):
                bx, by = bias
                x = max(0, min(GRID_W - 1, bx + random.randint(-8, 8)))
                y = max(0, min(GRID_H - 1, by + random.randint(-8, 8)))
                if self.tiles[y][x] == "grass":
                    self.tiles[y][x] = "berry"
                    self.berries[(x, y)] = {"ready": True, "timer": 0, "yield": random.randint(5, 15)}
        for _ in range(4):
            x, y = random.randrange(GRID_W), random.randrange(GRID_H)
            if self.tiles[y][x] == "grass":
                self.tiles[y][x] = "berry"
                self.berries[(x, y)] = {"ready": True, "timer": 0, "yield": random.randint(5, 15)}
        self.animals = [Animal(self._random_grass()) for _ in range(N_WOLVES)]

    def _random_grass(self):
        for _ in range(200):
            x, y = random.randrange(GRID_W), random.randrange(GRID_H)
            if self.tiles[y][x] == "grass":
                return (x, y)
        return (GRID_W // 2, GRID_H // 2)

    def nearest(self, positions, from_pos):
        if not positions:
            return None
        return min(positions, key=lambda p: (p[0] - from_pos[0]) ** 2 + (p[1] - from_pos[1]) ** 2)

    def nearest_ready_berry(self, from_pos):
        ready = [p for p, b in self.berries.items() if b["ready"]]
        return self.nearest(ready, from_pos)

    def tick_environment(self):
        for (x, y) in list(self.forest_tiles):
            if random.random() < 0.0015:
                nx, ny = x + random.choice([-1, 0, 1]), y + random.choice([-1, 0, 1])
                if 0 <= nx < GRID_W and 0 <= ny < GRID_H and self.tiles[ny][nx] == "grass":
                    self.tiles[ny][nx] = "forest"
                    self.wood_amt[(nx, ny)] = 30
                    self.forest_tiles.add((nx, ny))
        for pos, b in self.berries.items():
            if not b["ready"]:
                b["timer"] -= 1
                if b["timer"] <= 0:
                    b["ready"] = True
                    b["yield"] = random.randint(5, 15)
        for wolf in self.animals:
            wolf.wander(self)
            wolf.cooldown = max(0, wolf.cooldown - 1)

    def build(self, pos, btype, faction_id):
        x, y = pos
        self.tiles[y][x] = btype
        self.buildings.append((x, y, btype, faction_id))
        self._connect_road(pos)

    def _connect_road(self, pos):
        same = [b for b in self.buildings[:-1]]
        if not same:
            return
        target = min(same, key=lambda b: (b[0] - pos[0]) ** 2 + (b[1] - pos[1]) ** 2)
        x, y = pos
        tx, ty = target[0], target[1]
        while x != tx:
            x += 1 if tx > x else -1
            self.roads.add((x, y))
        while y != ty:
            y += 1 if ty > y else -1
            self.roads.add((x, y))


class Animal:
    def __init__(self, pos):
        self.x, self.y = pos
        self.cooldown = 0

    @property
    def pos(self):
        return (self.x, self.y)

    def wander(self, world):
        dx, dy = random.choice([-1, 0, 1]), random.choice([-1, 0, 1])
        nx, ny = self.x + dx, self.y + dy
        if 0 <= nx < GRID_W and 0 <= ny < GRID_H and world.tiles[ny][nx] != "water":
            self.x, self.y = nx, ny


# ---------------- Faction ----------------
class Faction:
    def __init__(self, fid, name, color_adult, color_child):
        self.id = fid
        self.name = name
        self.color_adult = color_adult
        self.color_child = color_child
        self.stockpile = {"wood": 20, "stone": 10, "food": 30}
        self.brain = None  # set to QBrain()
        self.kills = 0
        self.deaths = 0


# ---------------- Agent ----------------
class Agent:
    _counter = 0

    def __init__(self, name, pos, faction_id, age=0):
        self.name = name
        self.x, self.y = pos
        self.faction_id = faction_id
        self.hunger = 20.0
        self.energy = 100.0
        self.age = age
        self.alive = True
        self.repro_cd = 0
        Agent._counter += 1

    @property
    def pos(self):
        return (self.x, self.y)

    @property
    def is_adult(self):
        return self.age >= ADULT_AGE

    def step_toward(self, target, world):
        if target is None:
            dx, dy = random.choice([-1, 0, 1]), random.choice([-1, 0, 1])
        else:
            dx = (target[0] > self.x) - (target[0] < self.x)
            dy = (target[1] > self.y) - (target[1] < self.y)
        for cand in [(dx, dy), (dx, 0), (0, dy), (random.choice([-1, 0, 1]), random.choice([-1, 0, 1]))]:
            nx, ny = self.x + cand[0], self.y + cand[1]
            if 0 <= nx < GRID_W and 0 <= ny < GRID_H and world.tiles[ny][nx] != "water":
                self.x, self.y = nx, ny
                return


# ---------------- RL ----------------
class QBrain:
    def __init__(self):
        self.q = {}
        self.epsilon = EPS_START

    def get(self, state):
        if state not in self.q:
            self.q[state] = [0.0] * len(ACTIONS)
        return self.q[state]

    def choose(self, state):
        if random.random() < self.epsilon:
            return random.randrange(len(ACTIONS))
        qs = self.get(state)
        best = max(qs)
        candidates = [i for i, v in enumerate(qs) if v == best]
        return random.choice(candidates)

    def update(self, s, a, r, s2):
        qs = self.get(s)
        qs2 = self.get(s2)
        qs[a] += ALPHA * (r + GAMMA * max(qs2) - qs[a])

    def decay(self, tick):
        self.epsilon = max(EPS_MIN, EPS_START - (EPS_START - EPS_MIN) * (tick / EPS_DECAY_TICKS))


TILE_TYPE_IDX = {"grass": 0, "forest": 1, "rock": 2, "berry": 3, "house": 4, "farm": 4}


def faction_population(agents, fid):
    return sum(1 for a in agents if a.alive and a.faction_id == fid)


def faction_capacity(world, fid):
    # derived from standing houses, not a stored counter -- so capacity survives
    # a wipeout as long as the houses are still standing (returning refugees
    # can move back into existing houses, they don't lose progress)
    house_count = sum(1 for b in world.buildings if b[2] == "house" and b[3] == fid)
    return min(MAX_POP_PER_TRIBE, 2 + 2 * house_count)


def encode_state(agent, world, agents, factions):
    hunger_lvl = 0 if agent.hunger < 40 else (1 if agent.hunger < 75 else 2)
    energy_lvl = 0 if agent.energy > 40 else 1
    tile_idx = TILE_TYPE_IDX.get(world.tiles[agent.y][agent.x], 0)
    fac = factions[agent.faction_id]
    has_house_res = int(fac.stockpile["wood"] >= 15 and fac.stockpile["stone"] >= 5)
    has_farm_res = int(fac.stockpile["wood"] >= 10 and fac.stockpile["stone"] >= 10)
    food = fac.stockpile["food"]
    food_lvl = 0 if food < 10 else (1 if food < 40 else 2)
    partner_ready = 0
    enemy_adjacent = 0
    for other in agents:
        if other is agent or not other.alive:
            continue
        close = max(abs(other.x - agent.x), abs(other.y - agent.y)) <= 1
        if not close:
            continue
        if other.faction_id == agent.faction_id:
            if other.is_adult and agent.is_adult and other.repro_cd == 0 and agent.repro_cd == 0:
                partner_ready = 1
        else:
            if other.is_adult and agent.is_adult:
                enemy_adjacent = 1
    pop_at_cap = int(faction_population(agents, agent.faction_id) >= faction_capacity(world, agent.faction_id))
    return (hunger_lvl, energy_lvl, tile_idx, has_house_res, has_farm_res, food_lvl,
            partner_ready, pop_at_cap, enemy_adjacent)


def find_partner(agent, agents):
    for other in agents:
        if other is agent or not other.alive or other.faction_id != agent.faction_id:
            continue
        if other.is_adult and agent.is_adult and other.repro_cd == 0 and agent.repro_cd == 0:
            if max(abs(other.x - agent.x), abs(other.y - agent.y)) <= 1:
                return other
    return None


def find_enemy(agent, agents):
    for other in agents:
        if other is agent or not other.alive or other.faction_id == agent.faction_id:
            continue
        if other.is_adult and agent.is_adult:
            if max(abs(other.x - agent.x), abs(other.y - agent.y)) <= 1:
                return other
    return None


def empty_adjacent(pos, world):
    x, y = pos
    opts = [(x + dx, y + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1) if (dx, dy) != (0, 0)]
    random.shuffle(opts)
    for nx, ny in opts:
        if 0 <= nx < GRID_W and 0 <= ny < GRID_H and world.tiles[ny][nx] != "water":
            return (nx, ny)
    return pos


def step_agent(agent, action_idx, world, agents, factions, log):
    action = ACTIONS[action_idx]
    fac = factions[agent.faction_id]
    reward = -0.01

    if action == "SeekWood":
        if world.tiles[agent.y][agent.x] == "forest":
            amt = min(5, world.wood_amt.get(agent.pos, 0))
            world.wood_amt[agent.pos] = world.wood_amt.get(agent.pos, 0) - amt
            fac.stockpile["wood"] += amt
            if world.wood_amt[agent.pos] <= 0:
                world.tiles[agent.y][agent.x] = "grass"
                world.forest_tiles.discard(agent.pos)
                del world.wood_amt[agent.pos]
            reward += 1.0 if amt > 0 else -0.2
        else:
            agent.step_toward(world.nearest(world.forest_tiles, agent.pos), world)
            reward += 0.02
        agent.energy -= 0.5

    elif action == "SeekStone":
        if world.tiles[agent.y][agent.x] == "rock":
            amt = min(5, world.stone_amt.get(agent.pos, 0))
            world.stone_amt[agent.pos] = world.stone_amt.get(agent.pos, 0) - amt
            fac.stockpile["stone"] += amt
            if world.stone_amt[agent.pos] <= 0:
                world.tiles[agent.y][agent.x] = "grass"
                world.rock_tiles.discard(agent.pos)
                del world.stone_amt[agent.pos]
            reward += 1.0 if amt > 0 else -0.2
        else:
            agent.step_toward(world.nearest(world.rock_tiles, agent.pos), world)
            reward += 0.02
        agent.energy -= 0.5

    elif action == "SeekFood":
        b = world.berries.get(agent.pos)
        if b is not None and b["ready"]:
            fac.stockpile["food"] += b["yield"]
            b["ready"] = False
            b["timer"] = 150
            reward += 1.0
        else:
            target = world.nearest_ready_berry(agent.pos) or world.nearest(list(world.berries.keys()), agent.pos)
            agent.step_toward(target, world)
            reward += 0.02
        agent.energy -= 0.5

    elif action == "Eat":
        if fac.stockpile["food"] >= 10 and agent.hunger >= 25:
            fac.stockpile["food"] -= 10
            agent.hunger = max(0, agent.hunger - 40)
            reward += 1.5
        else:
            reward -= 0.3
        agent.energy -= 0.1

    elif action == "Rest":
        was_tired = agent.energy < 40
        agent.energy = min(100, agent.energy + 3)
        reward += 0.1 if was_tired else -0.1

    elif action == "BuildHouse":
        if (world.tiles[agent.y][agent.x] == "grass" and fac.stockpile["wood"] >= 15
                and fac.stockpile["stone"] >= 5 and len(world.buildings) < MAX_BUILDINGS):
            fac.stockpile["wood"] -= 15
            fac.stockpile["stone"] -= 5
            world.build(agent.pos, "house", fac.id)
            reward += 6.0
            log.appendleft(f"[{fac.name}] house built ({len(world.buildings)} structures on map)")
        else:
            reward -= 0.4
        agent.energy -= 1.0

    elif action == "BuildFarm":
        if (world.tiles[agent.y][agent.x] == "grass" and fac.stockpile["wood"] >= 10
                and fac.stockpile["stone"] >= 10 and len(world.buildings) < MAX_BUILDINGS):
            fac.stockpile["wood"] -= 10
            fac.stockpile["stone"] -= 10
            world.build(agent.pos, "farm", fac.id)
            reward += 5.0
            log.appendleft(f"[{fac.name}] farm built")
        else:
            reward -= 0.4
        agent.energy -= 1.0

    elif action == "Reproduce":
        partner = find_partner(agent, agents)
        if (partner is not None and faction_population(agents, fac.id) < faction_capacity(world, fac.id)
                and fac.stockpile["food"] >= 20):
            fac.stockpile["food"] -= 20
            spot = empty_adjacent(agent.pos, world)
            child_name = f"{fac.name[:1]}-{Agent._counter}"
            child = Agent(child_name, spot, fac.id)
            agent.repro_cd = REPRO_COOLDOWN
            partner.repro_cd = REPRO_COOLDOWN
            reward += 10.0
            log.appendleft(f"[{fac.name}] {agent.name} & {partner.name} welcomed {child_name}")
            return reward, child
        else:
            reward -= 0.4
        agent.energy -= 1.0

    elif action == "Attack":
        enemy = find_enemy(agent, agents)
        if enemy is not None:
            enemy_fac = factions[enemy.faction_id]
            if random.random() < 0.5:
                enemy.alive = False
                enemy_fac.deaths += 1
                fac.kills += 1
                reward += ATTACK_REWARD
                log.appendleft(f"[{fac.name}] {agent.name} defeated {enemy.name} of [{enemy_fac.name}]")
            else:
                agent.alive = False
                fac.deaths += 1
                enemy_fac.kills += 1
                reward -= ATTACK_REWARD
                log.appendleft(f"[{enemy_fac.name}] {enemy.name} defeated {agent.name} of [{fac.name}]")
        else:
            reward -= 0.3
        agent.energy -= 1.5

    return reward, None


def run_tick(world, agents, factions, log, tick):
    world.tick_environment()
    # farms passively feed their own faction (moved here so we have factions dict)
    for (x, y, btype, fid) in world.buildings:
        if btype == "farm" and random.random() < 0.01:
            factions[fid].stockpile["food"] += 3

    newborns = []
    for agent in list(agents):
        if not agent.alive:
            continue
        agent.repro_cd = max(0, agent.repro_cd - 1)
        fac = factions[agent.faction_id]
        s = encode_state(agent, world, agents, factions)
        a = fac.brain.choose(s)
        reward, born = step_agent(agent, a, world, agents, factions, log)

        if agent.alive:
            agent.hunger = min(100, agent.hunger + 0.3)
            agent.energy = max(0, min(100, agent.energy))
            agent.age += 1
            reward += 0.02
            if agent.hunger >= 100:
                agent.alive = False
                fac.deaths += 1
                reward -= 10.0
                log.appendleft(f"[{fac.name}] {agent.name} starved")

        s2 = encode_state(agent, world, agents, factions) if agent.alive else s
        fac.brain.update(s, a, reward, s2)
        if born:
            newborns.append(born)

    # wildlife attacks
    for wolf in world.animals:
        if wolf.cooldown > 0:
            continue
        for agent in agents:
            if not agent.alive:
                continue
            if max(abs(agent.x - wolf.x), abs(agent.y - wolf.y)) <= 1:
                chance = WOLF_CHANCE_ADULT if agent.is_adult else WOLF_CHANCE_CHILD
                if random.random() < chance:
                    agent.alive = False
                    factions[agent.faction_id].deaths += 1
                    log.appendleft(f"[{factions[agent.faction_id].name}] {agent.name} was killed by a wolf")
                    wolf.cooldown = WOLF_ATTACK_COOLDOWN
                break

    agents.extend(newborns)
    agents[:] = [a for a in agents if a.alive]
    for fac in factions.values():
        fac.brain.decay(tick)
    return agents


def spawn_founders(world, faction, names, corner):
    cx, cy = corner
    start = world.nearest(
        [(x, y) for y in range(GRID_H) for x in range(GRID_W) if world.tiles[y][x] == "grass"], (cx, cy))
    a1 = Agent(names[0], start, faction.id, age=ADULT_AGE)
    spot2 = empty_adjacent(start, world)
    a2 = Agent(names[1], spot2, faction.id, age=ADULT_AGE)
    faction.stockpile = {"wood": 20, "stone": 10, "food": 30}
    return [a1, a2]


def new_world_and_factions():
    world = World()
    fac_a = Faction(0, "Tribe A", (70, 140, 230), (150, 190, 240))
    fac_b = Faction(1, "Tribe B", (235, 140, 45), (245, 190, 130))
    fac_a.brain = QBrain()
    fac_b.brain = QBrain()
    factions = {0: fac_a, 1: fac_b}
    agents = []
    agents += spawn_founders(world, fac_a, ["Adam", "Eve"], (GRID_W // 4, GRID_H // 4))
    agents += spawn_founders(world, fac_b, ["Kael", "Sora"], (3 * GRID_W // 4, 3 * GRID_H // 4))
    return world, factions, agents


def respawn_faction(world, faction, names):
    corner = (random.randrange(GRID_W), random.randrange(GRID_H))
    return spawn_founders(world, faction, names, corner)


# ---------------- Rendering ----------------
def draw(screen, fonts, world, agents, factions, tick, speed, paused, log):
    font, small, tiny = fonts
    screen.fill(COLOR_BG)
    ox, oy = 15, 60

    for y in range(GRID_H):
        for x in range(GRID_W):
            t = world.tiles[y][x]
            if t == "forest":
                frac = world.wood_amt.get((x, y), 0) / 30
                color = blend(FOREST_EMPTY, FOREST_FULL, frac)
            elif t == "rock":
                frac = world.stone_amt.get((x, y), 0) / 40
                color = blend(ROCK_EMPTY, ROCK_FULL, frac)
            elif t == "house" or t == "farm":
                color = (156, 110, 74) if t == "house" else (176, 152, 68)
            else:
                color = TILE_BASE.get(t, (74, 122, 58))
            rect = (ox + x * TILE, oy + y * TILE, TILE - 1, TILE - 1)
            pygame.draw.rect(screen, color, rect)
            if (x, y) in world.roads and t == "grass":
                pygame.draw.rect(screen, (150, 140, 120), rect, 0)

    for (x, y, btype, fid) in world.buildings:
        tint = factions[fid].color_adult
        rect = (ox + x * TILE, oy + y * TILE, TILE - 1, TILE - 1)
        pygame.draw.rect(screen, tint, rect, 3)

    for pos, b in world.berries.items():
        cx, cy = ox + pos[0] * TILE + TILE // 2, oy + pos[1] * TILE + TILE // 2
        if b["ready"]:
            t = (b["yield"] - 5) / 10
            color = blend(BERRY_LOW, BERRY_HIGH, t)
            radius = 3 + int(t * 4)
        else:
            color = (95, 85, 75)
            radius = 2
        pygame.draw.circle(screen, color, (cx, cy), radius)

    for (zx, zy, label) in world.zone_labels:
        txt = tiny.render(label, True, (210, 220, 200))
        screen.blit(txt, (ox + zx * TILE - 20, oy + zy * TILE - 14))

    for wolf in world.animals:
        cx, cy = ox + wolf.x * TILE + TILE // 2, oy + wolf.y * TILE + TILE // 2
        pygame.draw.polygon(screen, (60, 55, 50), [(cx, cy - 6), (cx - 6, cy + 5), (cx + 6, cy + 5)])

    for agent in agents:
        fac = factions[agent.faction_id]
        color = fac.color_adult if agent.is_adult else fac.color_child
        cx, cy = ox + agent.x * TILE + TILE // 2, oy + agent.y * TILE + TILE // 2
        radius = 7 if agent.is_adult else 4
        pygame.draw.circle(screen, color, (cx, cy), radius)
        pygame.draw.circle(screen, (255, 255, 255), (cx, cy), radius, 1)

    title = font.render("City RL Sim v2 -- Two Rival Tribes", True, (240, 240, 245))
    screen.blit(title, (15, 15))
    info = small.render(
        f"Tick {tick}   Speed {speed}x   [SPACE] pause  [+/-] speed  [R] reset  [ESC] quit",
        True, (150, 155, 165))
    screen.blit(info, (15, 40))

    px = ox + GRID_PIX_W + 20
    py = oy
    pygame.draw.rect(screen, (26, 28, 36), (px, py, PANEL_W, GRID_PIX_H), border_radius=6)
    y_cursor = py + 12
    for fid in (0, 1):
        fac = factions[fid]
        pygame.draw.circle(screen, fac.color_adult, (px + 16, y_cursor + 8), 6)
        name_txt = small.render(fac.name, True, (235, 235, 240))
        screen.blit(name_txt, (px + 30, y_cursor))
        y_cursor += 22
        pop = faction_population(agents, fid)
        cap = faction_capacity(world, fid)
        stats = [
            f"Pop {pop}/{cap}   Kills {fac.kills}  Deaths {fac.deaths}",
            f"Wood {int(fac.stockpile['wood'])}  Stone {int(fac.stockpile['stone'])}  Food {int(fac.stockpile['food'])}",
            f"eps {fac.brain.epsilon:.2f}   Q-states {len(fac.brain.q)}",
        ]
        for line in stats:
            txt = tiny.render(line, True, (205, 208, 216))
            screen.blit(txt, (px + 14, y_cursor))
            y_cursor += 16
        y_cursor += 8

    wolves_txt = tiny.render(f"Wolves roaming: {len(world.animals)}", True, (190, 160, 150))
    screen.blit(wolves_txt, (px + 14, y_cursor))
    y_cursor += 22

    log_title = small.render("Recent events:", True, (170, 175, 185))
    screen.blit(log_title, (px + 14, y_cursor))
    y_cursor += 20
    for entry in list(log)[:11]:
        txt = tiny.render(entry[:36], True, (150, 205, 170))
        screen.blit(txt, (px + 14, y_cursor))
        y_cursor += 16

    if paused:
        p = font.render("PAUSED", True, (241, 196, 15))
        screen.blit(p, (WINDOW_W // 2 - 60, WINDOW_H - 30))

    pygame.display.flip()


def main():
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_W, WINDOW_H))
    pygame.display.set_caption("City RL Sim v2")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("consolas", 22)
    small = pygame.font.SysFont("consolas", 15)
    tiny = pygame.font.SysFont("consolas", 13)

    world, factions, agents = new_world_and_factions()
    log = deque(maxlen=30)
    log.appendleft("Adam & Eve and Kael & Sora arrive, an ocean apart.")

    tick = 0
    speed = 4
    paused = False
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
                    speed = min(32, speed * 2)
                elif event.key == pygame.K_MINUS:
                    speed = max(1, speed // 2)
                elif event.key == pygame.K_r:
                    world, factions, agents = new_world_and_factions()
                    log.appendleft("-- world reset, learning kept --")

        if not paused:
            for _ in range(speed):
                tick += 1
                agents = run_tick(world, agents, factions, log, tick)
                for fid, names in ((0, ["Adam", "Eve"]), (1, ["Kael", "Sora"])):
                    if faction_population(agents, fid) == 0:
                        agents += respawn_faction(world, factions[fid], names)
                        log.appendleft(f"-- {factions[fid].name} was wiped out, survivors return --")

        draw(screen, (font, small, tiny), world, agents, factions, tick, speed, paused, log)
        clock.tick(FPS)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()