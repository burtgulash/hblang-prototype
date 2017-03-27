#!/usr/bin/env python3

from enum import Enum
import sys
import time

import readline
from c import Lex, Parse, \
              ParseError, TT, Tree, Leaf, Void



class CT(Enum):
    Return = 1
    Left = 2
    Head = 3
    Right = 4
    Delim = 5


class Frame:

    def __init__(self, ct, L, H, R, x, env):
        self.L = L
        self.H = H
        self.R = R
        self.ct = ct
        self.x = x
        self.env = env


def reset(a, b, cstack, env):
    cstack.append(Frame(CT.Delim, None, None, None, None, env))
    return a, cstack, env


def shift(a, b, cstack, env):
    st = []
    while True:
        c = cstack.pop()
        if c.tt == Delim:
            break
        st.append(c)

    continuation = Leaf(TT.CONTINUATION, (st, env))
    env.bind(a.w, continuation)
    assert b.tt == TT.THUNK
    return b.w, cstack, env


def setenv(H, env):
    self_f = env.lookup("self", None)
    if self_f is H:
        return env
    return Env(env)


def get_type(a, b, env):
    return Leaf(TT.SYMBOL, a.tt.name)


def unwrap(H):
    assert H.tt in (TT.FUNCTION, TT.THUNK)
    return H.w


def bake(a, _, env):
    assert a.tt == TT.FUNCTION
    return Leaf(a.tt, bake_2(unwrap(a), env))


# def bake_(x, env):
#     if isinstance(x, Tree):
#         L, H, R = bake_(x.L, env), bake_(x.H, env), bake_(x.R, env)
#         if TT.THUNK not in (L.tt, H.tt, R.tt):
#             x = Tree(H.tt, L, H, R)
#             return Eval(x, env)
#         L, H, R = unthunk(L, env), unthunk(H, env), unthunk(R, env)
#         return Tree(H.tt, L, H, R)
#     return unthunk(x, env)
# 
# 
def bake_2(x, env):
    if isinstance(x, Tree):
        L, H, R = bake_2(x.L, env), bake_2(x.H, env), bake_2(x.R, env)
        x = Tree(H.tt, L, H, R)
        #if TT.THUNK not in (L.tt, H.tt, R.tt):
        #    x = Eval(x, env)
    elif isinstance(x, Leaf) and x.tt == TT.THUNK:
        x = unwrap(x)
        #if x.tt != TT.THUNK:
        #    x = Eval(x, env)
    return x

# def unthunk(x, env):
#     if x.tt == TT.THUNK:
#         return x.w
#     elif x.tt == TT.FUNCTION:
#         return x
#     return Eval(x, nv)


def then(a, b, env):
    assert b.tt == TT.PUNCTUATION and isinstance(b, Tree)
    conseq = b.R if a.w == 0 else b.L
    if conseq.tt in (TT.FUNCTION, TT.THUNK):
        conseq = conseq.w
    return conseq

le = lambda a, b, env: Leaf(TT.NUM, 1 if a.w < b.w else 0),
ge = lambda a, b, env: Leaf(TT.NUM, 1 if a.w > b.w else 0),

def app(a, b, env):
    if a.tt == "vec":
        return Leaf("vec", a.w + [b.w])
    return Leaf("vec", [a.w, b.w])

def P(a, _, env):
    print(a)
    return a

def wait(a, b, env):
    assert b.tt == TT.NUM and b.w >= 0
    time.sleep(b.w)
    return a


BUILTINS = {
    "+": lambda a, b, env: Leaf(TT.NUM, a.w + b.w),
    "-": lambda a, b, env: Leaf(TT.NUM, a.w - b.w),
    "*": lambda a, b, env: Leaf(TT.NUM, a.w * b.w),
    "/": lambda a, b, env: Leaf(TT.NUM, a.w // b.w),
    "=": lambda a, b, env: Leaf(TT.NUM, 1 if a.w == b.w else 0),
    "<": le,
    ">": ge,
    "le": le,
    "ge": ge,
    "lte": lambda a, b, env: Leaf(TT.NUM, 1 if a.w <= b.w else 0),
    "gte": lambda a, b, env: Leaf(TT.NUM, 1 if a.w >= b.w else 0),
    "$": lambda a, b, env: env.lookup(a.w, b),
    "to": lambda a, b, env: env.assign(b.w, a),
    "as": lambda a, b, env: env.bind(b.w, a),
    "is": lambda a, b, env: env.bind(a.w, b),
    "?": then,
    "then": then,
    "t": get_type,
    "|": lambda a, b, env: b,
    "bake": bake,
    "L": lambda a, _, env: a.L,
    "H": lambda a, _, env: a.H,
    "R": lambda a, _, env: a.R,
    "open": lambda a, _, env: unwrap(a),
    "unwrap": lambda a, _, env: unwrap(a),
    ",": app,
    "vec": lambda a, _, env: Leaf("vec", []),
    # "callcc": callcc,
    "P": P,
    "wait": wait,
}


SPECIAL = {
    "reset": reset,
    "shift": shift,
}



class Env:

    def __init__(self, parent, from_dict=None):
        self.parent = parent
        self.e = {**(from_dict or {})}

    def lookup(self, name, or_else):
        env = self.find_env(name)
        if not env:
            return or_else
        return env.e[name]

    def find_env(self, name):
        # TODO optimize self-recursion in tail calls by reusing env
        if name in self.e:
            return self
        elif self.parent is not None:
            return self.parent.find_env(name)
        return None

    def bind(self, name, value):
        self.e[name] = value
        return value

    def assign(self, name, value):
        env = self.find_env(name) or self
        env.bind(name, value)
        return value


def Eval(x, env):
    cstack = [Frame(CT.Return, None, None, None, x, env)]

    while True:
        if isinstance(x, Leaf):
            pass
        elif isinstance(x, Tree):
            L, H, R = x.L, x.H, x.R

            if isinstance(L, Tree):
                cstack.append(Frame(CT.Left, None, None, None, x, env))
                x = L
                continue
            if isinstance(H, Tree):
                cstack.append(Frame(CT.Head, L, None, None, x, env))
                x = H
                continue
            # x = Tree(H.tt, L, H, R) # TODO why this??

            if H.tt == TT.SEPARATOR:
                # Tail recurse on separator '|' before R gets evaluated
                x = R
                continue

            if isinstance(R, Tree):
                cstack.append(Frame(CT.Right, L, H, None, x, env))
                x = R
                continue

            # print("EVAL", x, file=sys.stderr)
            # print("L", L, file=sys.stderr)
            # print("R", R, file=sys.stderr)

            # TODO reorder by frequency of invocation. BUILTIN to top?
            if H.tt == TT.THUNK:
                x = unwrap(H)
                continue
            elif H.tt == TT.FUNCTION:
                env = setenv(H, env)
                env.bind("self", H)
                env.bind("x", L)
                env.bind("y", R)
                x = unwrap(H)
                continue
            elif H.tt == TT.CONTINUATION:
                st, env = x.w
                x = L
                cstack.append(Frame(CT.Delim, None, None, None, x, env))
                while st:
                    cstack.append(st.pop())
            elif H.tt == TT.PUNCTUATION and H.w in ".:":
                x = Tree(H.tt, L, H, R)
            elif H.tt in (TT.PUNCTUATION, TT.SYMBOL, TT.SEPARATOR):
                op = env.lookup(H.w, None)
                if op is None:
                    raise Exception(f"Operator not found {H.w}")
                assert op.tt in (TT.BUILTIN, TT.THUNK, TT.FUNCTION)
                x = Tree(op.tt, L, op, R)
                continue
            elif H.tt == TT.BUILTIN:
                x = H.w(L, R, env)
                continue
            elif H.tt == TT.SPECIAL:
                x, cstack, env = H.w(L, R, cstack, env)
            elif H.tt == TT.VOID:
                x = H
            else:
                raise AssertionError(f"Can't process: {H} of {H.tt}")

        # Apply continuation
        c = cstack.pop()
        if c.ct == CT.Return:
            return x

        L, H, R = c.L, c.H, c.R
        if c.ct == CT.Left:
            x = Tree(c.x.tt, x, c.x.H, c.x.R)
            env = c.env
        elif c.ct == CT.Head:
            x = Tree(H.tt, L, x, c.x.R)
            env = c.env
        elif c.ct == CT.Right:
            x = Tree(H.tt, L, H, x)
            env = c.env
        elif c.ct == CT.Delim:
            env = c.env
        else:
            assert False


def Repl(prompt="> "):
    builtins = {k: Leaf(TT.BUILTIN, x) for k, x in BUILTINS.items()}
    special = {k: Leaf(TT.SPECIAL, x) for k, x in SPECIAL.items()}
    env = Env(None, from_dict={
        **special,
        **builtins,
    })

    while True:
        try:
            x = input(prompt)
            x = Lex(x)
            #print("LEX", y)
            x = Parse(x)
            # print("PARSE", y)
            x = Eval(x, env)
            if x is not None:
                print(x)
        except ParseError as err:
            print(f"Parse error: {err}", file=sys.stderr)
        except (EOFError, KeyboardInterrupt):
            break


if __name__ == "__main__":
    readline.parse_and_bind('tab: complete')
    readline.parse_and_bind('set editing-mode vi')
    Repl()
