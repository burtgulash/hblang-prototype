from enum import Enum


class CT(Enum):
    Leaf = 0
    Tree = 1
    Left = 2
    Head = 3
    Right = 4
    Return = 5
    Function = 6

    def __lt__(self, other):
        return self.value < other.value

    def __eq__(self, other):
        return self.value == other.value

    def __le__(self, other):
        return self.value <= other.value


class Frame:

    def __init__(self, ct, L, H, R, env):
        self.ct = ct
        self.L = L
        self.H = H
        self.R = R
        self.env = env

    def __repr__(s):
        return str(s.ct)
        # return f"F {s.ct} ({s.L} {s.H} {s.R})"


class Cactus:

    def __init__(self):
        self.rope = [[]]

    def spush(self):
        self.rope.append([])

    def spop(self):
        assert self.rope
        return self.rope.pop()

    def scopy(self, st):
        self.spush()
        for x in st:
            self.push(x)

    def push(self, x):
        self.rope[-1].append(x)

    def peek(self):
        if not self.rope[-1]:
            return None
        return self.rope[-1][-1]

    def pop(self):
        assert self.rope
        while not self.rope[-1]:
            self.spop()
        assert self.rope and self.rope[-1]
        return self.rope[-1].pop()
