import random

world_list = ['mobile', 'love', 'relax']
chosen_character = random.choice(world_list)
hidden = "_" * len(chosen_character)
original_lives = len(chosen_character)
lives = len(chosen_character)
game_over = False
guessed_letter = []

print(f"{chosen_character}")
print(f"{hidden}")





while not game_over: 
    print(f"You have {lives}/{original_lives} left")
    guess = input("Guess a letter: ").lower()

    current_progress = ""

    for letter in chosen_character:
        if letter == guess:
          current_progress += letter
          guessed_letter.append(letter)
        elif letter in guessed_letter:
          current_progress += letter
        else:
          current_progress += "_"

    if guess not in chosen_character:
       lives -= 1
       if lives == 0:
          game_over = True
          print("You Lose")
    
    print(current_progress)
    
    if "_" not in current_progress:
         print(f'You Won, you guess the letter "{current_progress}" ')
         game_over = True
    