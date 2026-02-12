x = 10
x += 5
x -= 3
x *= 2
print(x)

print(17 % 5)

val = None
print(val is None)
print(val is not None)
print(42 is not None)

nums = [3, 1, 4, 1, 5]
print(sorted(nums))
print(min(nums))
print(max(nums))
print(sum(nums))
print(min(1, 2, 3))
print(max(7, 8, 9))

a = [1, 2, 3]
b = ["a", "b", "c"]
for pair in zip(a, b):
    print(pair)

if x > 10:
    print("big")
elif x > 5:
    print("medium")
elif x > 0:
    print("small")
else:
    print("zero")
