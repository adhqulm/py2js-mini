d = {"a": 1, "b": 2}
print(len(d), "a" in d, "z" in d)

print(d["a"])
nums = [1, 2, 3]
print(2 in nums, 5 in nums)

for k in d:
    print(k, d[k])


def add(x, y):
    z = x + y
    return z


print(add(10, 5))
