def div(a, b):
    if b == 0:
        raise ValueError("division by zero")
    return a / b


try:
    print(div(10, 2))
    print(div(3, 0))
except ValueError as e:
    print("caught", e)
else:
    print("no errors")
finally:
    print("finally runs")

try:
    raise KeyError("missing")
except KeyError:
    print("key error ok")
