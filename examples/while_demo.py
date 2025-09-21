i = 0
while i < 5:
    i = i + 1
    if i == 3:
        continue
    if i == 4:
        break
    print("loop", i)
else:
    print("no break")

# Should NOT run else because we broke at 4
# Expected prints: loop 1, loop 2

j = 0
while j < 3:
    print("w", j)
    j = j + 1
else:
    print("while-else ran")  # should run (no break)
