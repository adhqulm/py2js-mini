def pack(a, *rest):
    print("a=", a, "rest=", rest)


pack(1)
pack(1, 2, 3)

xs = [4, 5]
pack(*xs)
pack(9, *xs, 10)
