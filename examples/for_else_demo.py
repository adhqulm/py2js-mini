for i in range(5):
    if i == 3:
        break
    print("loop", i)
else:
    print("no break")  # should NOT run

for j in range(3):
    print("w", j)
else:
    print("for-else ran")  # should run
