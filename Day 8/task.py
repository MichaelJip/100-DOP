# def greet(name):
#     print(f"Hallo {name}")
#     print(f"How is your day {name}?")


# greet("Michael")

# def greet_with(name, location):
#     print(f"Hello {name}")
#     print(f"What is it like in {location}?")

# greet_with(location="London", name="Bob")

# Caesar Cipher
alphabet = ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m", "n", "o", "p", "q", "r", "s", "t", "u", "v", "w", "x", "y", "z"]
array_length = len(alphabet)

def encrypt(text, shift):
    indices = [(alphabet.index(char) + shift) % array_length for char in text]
    shifted_letters = [alphabet[index] for index in indices]
    new_word = ''.join(shifted_letters)
    print(f"Here is the encode word: {new_word}")

def decrypt(text, shift):
    indices = [(alphabet.index(char) - shift) % array_length  for char in text]
    shifted_letters = [alphabet[index] for index in indices]
    new_word = ''.join(shifted_letters)
    print(f"Here is the decode word: {new_word}")

def caesar(text, shift, type):
    if type == 'decode':
        shift *= -1

    if not text.lower().isalpha():
        print("Do not accept number, space, or special character") 
        return
    else:
        indices = [(alphabet.index(char) + shift) % array_length for char in text]
        shifted_letters = [alphabet[index] for index in indices]
        new_word = ''.join(shifted_letters)
        print(f"Here the {type}d result: {new_word}")

should_continue = True

while should_continue:
    direction = input("Type 'encode' to encrypt, type 'decode' to decrypt:\n").lower()
    text = input("Input your message:\n").lower()
    shift = int(input('Type the shift number:\n'))
    caesar(text, shift, type=direction)
    restart = input("Type 'yes' if you want to go again. Otherwise, type 'no'.\n").lower()

    if restart == 'no':
        should_continue = False
        print("Goodbye")