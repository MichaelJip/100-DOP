# fruits = ['Apple', 'Banana', "Watermelon", "Melon"]

# for fruit in fruits:
#     print(fruit)


student_scored = [150, 142, 120, 185, 171, 184, 24, 59]

# total_exams_score = sum(student_scored)
# print(total_exams_score)

# num = 0
# for score in student_scored:
#     num += score
    
# print(f"total: {num}")

# max_number_score = print(max(student_scored))

# max_score = student_scored[0]
# for max in student_scored:
#     if max > max_score:
#         max_score = max

# print(max_score)

# total = 0
# for number in range(1,101):
#     total += number

# print(total)

import random
#Strong Password Generator
alphabet = ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m", "n", "o", "p", "q", "r", "s", "t", "u", "v", "w", "x", "y", "z"]
number = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "0"]
special_character = ['!', '@', '#', '$', '%', '^', '&', '*', '(', ')', '_', '+', '-', '=', '[', ']', '{', '}', ';', ':', '\'', '"', ',', '.', '<', '>', '/', '?'];

print("Welcome to Password Generator")
nr_alpha = int(input("How many letters would you like in your password?\n"))
nr_number = int(input("How many numbers would you like?\n"))
nr_special = int(input("How many symbol would you like?\n"))

get_alpha = random.choices(alphabet, k=nr_alpha)
get_number = random.choices(number, k=nr_number)
get_symbol = random.choices(special_character, k=nr_special)

final_list = get_alpha + get_number + get_symbol 
random.shuffle(final_list)

password = ""
for char in final_list:
    password += char

print(f"Your password is: {password}")