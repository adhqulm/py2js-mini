def say(x):
    print("say", x)
    return x


print(say(0) and say(1))  # short-circuit on 0 -> prints "say 0" then outputs 0
print(say(1) and say(2))   # prints say 1, say 2 -> outputs 2
print(say("") or say("ok"))  # prints say "" then say "ok" -> outputs "ok"
print(not 0, not 1, not "x")
