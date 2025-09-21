def greet(name="world", times=1):
    for i in range(times):
        print("Hello,", name)


greet()
greet("Alice")
greet("Bob", 3)
