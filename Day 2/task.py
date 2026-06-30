print("Hello"[4])


print("Welcome to tip calculator!")

bill = input("What was the total bill? $")
tip = input("How much tip would you like to give? 10, 12, or 15 ")
people = input("How many people to split the bill? ")

bill_and_tip = float(bill) + (int(tip) / 100) 
calculate_total = float(bill_and_tip) / int(people)

print(f"Each person should pay: ${calculate_total}")