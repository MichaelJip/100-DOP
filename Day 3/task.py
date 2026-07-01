# print("Welcome to the rollercoaster!")
# height = int(input("What is your height in cm? "))

# if height > 120:
#     print("You can ride the rollercoaster!")
# else:
#     print("Sorry you have to grow taller before you can ride.")


#modulo
# number_to_check = int(input("What is the number you want to check? "))

# if number_to_check % 2 == 0:
#     print("Even")
# else: 
#     print("Odd")

#else if statements
# print("Welcome to the rollercoaster!")
# height = int(input("What is your height in cm? "))
# age = int(input("What is your age? "))
# photos = input("Do you want photos? Yes or No. ")
# bill = 0

# if height > 120:
#     print("You can ride the rollercoaster!")
#     if age <= 12:
#         bill = 5
#         print(f"Child tickets pay ${bill}")
#     elif age <=18:
#         bill = 10
#         print(f"Youth tickets pay ${10}")
#     elif age >= 45 and age <= 55:
#         print("Everything is going to be okay. Have a free ride on us!")
#     else:
#         bill = 17
#         print(f"Adult tickets pay ${bill}")
    
#     if photos == "Yes":
#         bill += 3
    
#     print(f"Your final bill is ${bill}")

# else:
#     print("Sorry you have to grow taller before you can ride.")

#Pizza Quiz
# print("Welcome to python Pizza Deliveries")
# size = input("What size pizza do you want? S, M, or L: ")
# pepperoni = input("Do you want pepperoni on your pizza? Y or N: ")
# extra_cheese = input("Do you want extra cheese? Y or N: ")
# bill = 0

# if size == "S":
#     bill += 15
# elif size == "M":
#     bill += 20
# elif size == "L":
#     bill += 25 
# else:
#     print("There is no size of that pizza!")

# if pepperoni == "Y":
#     if size == "S":
#         bill += 2
#     else:
#         bill += 3
        
# if extra_cheese == "Y":
#     bill += 1
        
# print(f"Your final bill is ${bill}") 

#Treasure Island Game
print("Welcome to Treasure Island. \nYour mission is to find the treasure.")
path = input("You're at the cross road. Where do you want to go? \n Type ""left"" or ""right"" \n")
if path == "left":
    swim_or_wait = input("You've come to a lake. There is an island in the middle of the lake. \n Type ""wait"" to wait for a boat. Type ""swim"" to swim across. \n")
    if swim_or_wait == "wait":
        door = input("There mysterious door in front of you \n Type which door you want to choose ""red"", ""yellow"", or ""blue"" door \n Be wise of what you choose. \n")
        if door == 'red':
            print("You go in the red door, \nand suddenly the door close and the room start \ncreating fire and you burned alive. Game Over.")
        elif door == 'blue':
            print("You go in the blue door, \nyou see a sky the door close behind you and suddenly the floor become water, \nyou try to swim but you getting tired and drown. Game Over.")
        elif door == 'yellow':
            print("You go in the yellow door, \nyou see the light and you finally see gold and take the treasure door behind you slowly close but you \ntake so many treasure and you able to escape. You Win.")
        else:
            print("You wander some where else, \nat first you see the treasure but it just a lie, suddenly the floor disappear and you drop to the void. Game Over.")
    else:
        print("You are attacked by trout. Game Over")  
else:
    print("Fall into a hole Game Over.")