import torch
import random
import numpy as np
from collections import deque
from game import SnakeGameAI, Direction, Point
from model import Linear_QNet, QTrainer
from helper import plot

MAX_MEMORY = 100_000
BATCH_SIZE = 1000
LR = 0.001
EPS_START = 1.0 # 100% random at the very beginning
EPS_MIN = 0.002 # never explore less than 2%
EPS_DECAY = 0.96 # multiply by this every game

class Agent:

    def __init__(self):
        self.n_game = 0
        self.epsilon = 0 # randomness
        self.gamma = 0.9 # discount rate
        self.memory = deque(maxlen=MAX_MEMORY) # popleft()
        self.model = Linear_QNet(18, 265, 3)
        if self.model.load():
            print("Loaded existing model!")
            self.loaded = True
        else:
            print("Starting fresh")
            self.loaded = False
        self.trainer = QTrainer(self.model, lr = LR, gamma=self.gamma)

    def get_state(self, game):
        head = game.snake[0]
        point_l = Point(head.x - 20, head.y)
        point_r = Point(head.x + 20, head.y)
        point_u = Point(head.x, head.y - 20)
        point_d = Point(head.x, head.y + 20)

        point_l2 = Point(head.x - 40, head.y)
        point_r2 = Point(head.x + 40, head.y)
        point_u2 = Point(head.x, head.y - 40)
        point_d2 = Point(head.x, head.y + 40)

        dir_l = game.direction == Direction.LEFT
        dir_r = game.direction == Direction.RIGHT
        dir_u = game.direction == Direction.UP
        dir_d = game.direction == Direction.DOWN

        state = [
            #Danger straight
            (dir_r and game.is_collision(point_r)) or
            (dir_l and game.is_collision(point_l)) or
            (dir_u and game.is_collision(point_u)) or
            (dir_d and game.is_collision(point_d)),

            #Danger right
            (dir_u and game.is_collision(point_r)) or
            (dir_d and game.is_collision(point_l)) or
            (dir_l and game.is_collision(point_u)) or
            (dir_r and game.is_collision(point_d)),

            #Danger left
            (dir_d and game.is_collision(point_r)) or
            (dir_u and game.is_collision(point_l)) or
            (dir_r and game.is_collision(point_u)) or
            (dir_l and game.is_collision(point_d)),

            #Danger straight (2 head)
            (dir_r and game.is_collision(point_r2)) or
            (dir_l and game.is_collision(point_l2)) or
            (dir_u and game.is_collision(point_u2)) or
            (dir_d and game.is_collision(point_d2)),

            #Danger right (2 head)
            (dir_u and game.is_collision(point_r2)) or
            (dir_d and game.is_collision(point_l2)) or
            (dir_l and game.is_collision(point_u2)) or
            (dir_r and game.is_collision(point_d2)),

            #Danger left (2 head)
            (dir_d and game.is_collision(point_r2)) or
            (dir_u and game.is_collision(point_l2)) or
            (dir_r and game.is_collision(point_u2)) or
            (dir_l and game.is_collision(point_d2)),

            #Move direction
            dir_l,
            dir_r,
            dir_u,
            dir_d,

            #Open space (flood fill): is there room to survive each way?
            # game.flood_fill(point_l) >= len(game.snake),
            # game.flood_fill(point_r) >= len(game.snake),
            # game.flood_fill(point_u) >= len(game.snake),
            # game.flood_fill(point_d) >= len(game.snake),
            
            #V2 Open space (flood fill): HOW MUCH room each way (0.0 to 1.0)
            game.flood_fill(point_l) / 768.0,
            game.flood_fill(point_r) / 768.0,
            game.flood_fill(point_u) / 768.0,
            game.flood_fill(point_d) / 768.0,


            #Food location
            game.food.x < game.head.x, # food left
            game.food.x > game.head.x,# food right
            game.food.y < game.head.y, # food up
            game.food.y > game.head.y, # food down
        ]

        # return np.array(state, dtype=int)
        return np.array(state, dtype=float)

    def remember(self, state, action, reward, next_state, done):
        self.memory.append((state, action, reward, next_state, done)) # popleft if MAX_MEMORY is reach

    def train_long_memory(self):
        if len(self.memory) > BATCH_SIZE:
            mini_sample = random.sample(self.memory, BATCH_SIZE) # list of tuples
        else: 
            mini_sample = self.memory
        
        states, actions, rewards, next_states, dones = zip(*mini_sample)
        self.trainer.train_step(states, actions, rewards, next_states, dones)

    def train_short_memory(self, state, action, reward, next_state, done):
        self.trainer.train_step(state, action, reward, next_state, done)

    # def get_action(self, state):
    #     # random moves: tradeOff exploration / exploitation
    #     if self.loaded:
    #         self.epsilon = 0
    #     else:
    #         self.epsilon = 80 - self.n_game
            
    #     final_move = [0, 0 ,0]

    #     if random.randint(0,200) < self.epsilon:
    #         move = random.randint(0, 2)
    #         final_move[move] = 1
    #     else:
    #         state0 = torch.tensor(state, dtype=torch.float)
    #         prediction = self.model(state0)
    #         move = torch.argmax(prediction).item()
    #         final_move[move] = 1

    #     return final_move

    def get_action(self, state):
            # exploration/exploitation tradeoff: epsilon = chance of a random move
            if self.loaded:
                self.epsilon = max(EPS_MIN, 0.05 * (EPS_DECAY ** self.n_game))
            else:
                self.epsilon = max(EPS_MIN, EPS_START * (EPS_DECAY ** self.n_game))
                
            final_move = [0, 0 ,0]

            if random.random() < self.epsilon:
                move = random.randint(0, 2)
                final_move[move] = 1
            else:
                state0 = torch.tensor(state, dtype=torch.float)
                prediction = self.model(state0)
                move = torch.argmax(prediction).item()
                final_move[move] = 1

            return final_move

def train():
    plot_score = []
    plot_mean_score = []
    total_score = 0
    record = 0
    agent = Agent()
    game = SnakeGameAI()

    while True:
        # get old state
        state_old = agent.get_state(game)

        # get move
        final_move = agent.get_action(state_old)

        # perform move and get new state
        reward, done, score = game.play_step(final_move)
        state_new = agent.get_state(game)

        #train short memory
        agent.train_short_memory(state_old, final_move, reward, state_new, done)

        # remember
        agent.remember(state_old, final_move, reward, state_new, done)

        if done:
            # train long memory, plot result
            game.reset()
            agent.n_game += 1
            agent.train_long_memory()

            if score > record:
                record = score
                agent.model.save()

            print('Game', agent.n_game, 'Score', score, 'Record:', record)

            #TODO: Plot

            plot_score.append(score)
            total_score += score
            mean_score = total_score/agent.n_game
            plot_mean_score.append(mean_score)
            plot(plot_score, plot_mean_score)


if __name__ == '__main__':
    train()