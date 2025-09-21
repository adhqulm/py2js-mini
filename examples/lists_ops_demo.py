# flake8: noqa

print([1, 2] + [3])      # [1, 2, 3]
print([9] * 3)          # [9, 9, 9]
print(2 * [7, 8])        # [7, 8, 7, 8]
xs = [1]; xs.append(2); xs.append(3)
print(xs)               # [1, 2, 3]
print(xs.pop())         # 3
print(xs)               # [1, 2]
