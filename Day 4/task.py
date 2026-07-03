import random
import my_module

# random_integer = random.randint(1, 5)
# print(my_module.my_favorite_number)

# random_number = random.random()
# print(random_number)

# random_h_t = random.randint(0, 1)

# if random_h_t == 0:
#     print('Heads')
# else:
#     print("Tails")

# List
# states_of_america = ['Delaware', 'Pennsylvania', 'New Jersey']

# states_of_america.append("Indonesia")

# print(states_of_america)

# Who will pay the bill?

# friends = ['Bob', 'Will', 'Robert', "Linda"]
# print(random.choice(friends))

#Rock, Paper, Scissors Game
player = int(input("What do you choose? Type 0 for Rock, 1 for Paper or 2 for Scissors.\n"))
computer = random.randint(0, 2)
print(f"Computer choice {computer}")

if player == 0 and computer == 2:
    print("You win")
elif computer > player:
    print("You lose")
elif player > computer:
    print("You win")
elif computer == player:
    print("It's a draw")
elif player >= 3 or player < 0:
    print("Invalid number!")