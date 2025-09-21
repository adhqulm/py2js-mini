# mypy: ignore-errors

class Capture:
    def __init__(self, buf):
        self.buf = buf

    def __enter__(self):
        self.buf.append("enter")
        return 42

    def __exit__(self, exc_type, exc, tb):
        self.buf.append("exit")


log = []
with Capture(log) as v:
    print(v)
print(log)
