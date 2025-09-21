class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def move(self, dx, dy):
        self.x = self.x + dx
        self.y = self.y + dy


p = Point(1, 2)
p.move(3, 4)
print(p.x, p.y)    # 4 6

q = Point(0, 0)
print(q.x, q.y)    # 0 0
