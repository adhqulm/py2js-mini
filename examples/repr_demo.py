class Point:
    def __init__(self, x, y):
        self.x, self.y = x, y

    def __repr__(self):
        return f"<Point {self.x},{self.y}>"


p = Point(2, 3)
print(p)
