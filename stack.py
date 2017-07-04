from enum import Enum
from typing import Union


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


class Stack:

    def __init__(self, tag):
        self.tag = tag
        self.s = []

    def empty(self):
        return len(self.s) == 0

    def push(self, x: Frame):
        self.s.append(x)

    def pop(self):
        return self.s.pop()

    def peek(self):
        if self.empty():
            return None
        return self.s[-1]


class Cactus:

    class Empty(Exception):

        def __init__(self, tag):
            super().__init__()
            self.tag = tag

    def __init__(self, tag: str):
        self.rope = []
        self.reset(tag)

    def _push_st(self, st: Stack):
        self.rope.append(st)

    def reset(self, tag: str):
        self.spush(tag)

    def spush(self, tag: str):
        self._push_st(Stack(tag))

    def spop(self, tag: str):
        while True:
            if not self.rope:
                raise Cactus.Empty(tag)
            st = self.rope.pop()
            if st.tag == tag:
                return st

    def scopy(self, st: Stack):
        self.spush(st.tag)
        # TODO Refactor loop. Insert into stack directly and then push stack onto cactus stack.
        for x in st.s:
            self.push(x)

    def push(self, x: Frame):
        self.rope[-1].push(x)

    def peek(self) -> Union[Frame, None]:
        if not self.rope: # TODO include this? Not tested...
            raise Cactus.Empty("__peek__")
        return self.rope[-1].peek()

    def pop(self) -> Union[Frame, None]:
        assert self.rope
        while self.rope[-1].empty():
            self.rope.pop()
        assert self.rope and not self.rope[-1].empty()
        return self.rope[-1].pop()
