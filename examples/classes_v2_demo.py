class A:
    def __init__(self, x):
        self.x = x
    
    def inc(self, d=1):
        self.x = self.x + d


class B(A):
    def __init__(self, x, y):
        super().__init__(x)   # initialize base first
        super().inc(2)        # then bump by 2
        self.y = y
    
    def add(self):
        return self.x + self.y


b = B(5, 10)
print(b.x, b.y)     # 7 10
print(b.add())      # 17
