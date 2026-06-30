print("Hello"[4])


print("Welcome to tip calculator!")

bill = float(input("What was the total bill? $"))
tip = int(input("How much tip would you like to give? 10, 12, or 15 "))
people = int(input("How many people to split the bill? "))

bill_and_tip = bill + (tip / 100) 
calculate_total = float(bill_and_tip) / people

print(f"Each person should pay: ${calculate_total}")