# mypy: ignore-errors

a, b = (1, 2)
print(a, b)
x, y, z = [3, 4, 5]
print(x, y, z)

s = "abc"
p, q, r = s
print(p, q, r)

u = [0, 1, 2, 3, 4]
h, *rest, t = u
print(h, rest, t)
