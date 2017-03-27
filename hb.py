#!/usr/bin/env python3

from enum import Enum
import sys
import time

import readline
from c import Lex, Parse, \
              ParseError, TT, Tree, Leaf, Void



class CT(Enum):
    Leaf = 0
    Tree = 1
    Left = 2
    Head = 3
    Right = 4
    Return = 5
    Delim = 6
    Function = 7

    def __lt__(self, other):
        return self.value < other.value

    def __eq__(self, other):
        return self.value == other.value

    def __le__(self, other):
        return self.value <= other.value


class Frame:

    def __init__(self, ct, L, H, R, x, env):
        self.L = L
        self.H = H
        self.R = R
        self.ct = ct
        self.x = x
        self.env = env

    def __repr__(s):
        return f"F {s.ct} ({s.L} {s.H} {s.R})"


def reset(a, b, cstack, env):
    cstack.append(Frame(CT.Delim, None, None, None, None, env))
    if b.tt == TT.THUNK:
        b = b.w
    return b, cstack, env


def shift(a, b, cstack, env):
    st = []
    while True:
        c = cstack.pop()
        if c.ct == CT.Delim:
            break
        st.append(c)

    st = st[::-1]
    # Don't let the continuation binding propagate to parent environment
    env = Env(env)
    # So far continuation is just a pair of st and env
    continuation = Leaf(TT.CONTINUATION, (st, env))
    env.bind(a.w, continuation)
    if b.tt == TT.THUNK:
        b = b.w
    return b, cstack, env


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

    def __repr__(self):
        return repr(self.e)


def next_ins(x):
    if isinstance(x, Leaf):
        return CT.Leaf
    elif isinstance(x, Tree):
        return CT.Tree
    assert False


def Eval(x, env):
    # Stack of continuations
    cstack = [Frame(CT.Return, None, None, None, x, env)]
    # Stored instruction pointer
    ins = next_ins(x)

    while True:
        if ins >= CT.Tree:
            if ins == CT.Tree:
                L, H, R = x.L, x.H, x.R
            if ins < CT.Left and isinstance(L, Tree):
                cstack.append(Frame(CT.Left, L, H, R, x, env))
                x, ins = L, next_ins(L)
                continue
            if ins < CT.Head and isinstance(H, Tree):
                cstack.append(Frame(CT.Head, L, H, R, x, env))
                x, ins = H, next_ins(H)
                continue
            if H.tt == TT.SEPARATOR:
                # Tail recurse on separator '|' before R gets evaluated
                x, ins = R, next_ins(R)
                continue
            if ins < CT.Right and isinstance(R, Tree):
                cstack.append(Frame(CT.Right, L, H, R, x, env))
                x, ins = R, next_ins(R)
                continue

            # print("EVAL", x, file=sys.stderr)
            # print("L", L, file=sys.stderr)
            # print("R", R, file=sys.stderr)

            # TODO reorder by frequency of invocation. BUILTIN to top?
            if H.tt == TT.VOID:
                x = H
            elif H.tt == TT.CONTINUATION:
                st, env = H.w
                # TODO add another delim?? MinCaml does
                # cstack.append(Frame(CT.Delim, None, None, None, L, env))
                cstack.extend(st)
                x, ins = L, next_ins(L)
            elif H.tt == TT.PUNCTUATION and H.w in ".:":
                x = Tree(H.tt, L, H, R)
            elif H.tt in (TT.PUNCTUATION, TT.SYMBOL, TT.SEPARATOR):
                op = env.lookup(H.w, None)
                if op is None:
                    raise Exception(f"Operator not found {H.w}")
                assert op.tt in (TT.CONTINUATION, TT.SPECIAL,\
                                 TT.BUILTIN, TT.THUNK, TT.FUNCTION)
                x = Tree(op.tt, L, op, R)
                ins = next_ins(x)
                continue
            elif H.tt == TT.BUILTIN:
                x = H.w(L, R, env)
                ins = next_ins(x)
                continue
            elif H.tt == TT.SPECIAL:
                x, cstack, env = H.w(L, R, cstack, env)
                ins = next_ins(x)
                continue
            elif H.tt == TT.THUNK:
                x = unwrap(H)
                ins = next_ins(x)
                continue
            elif H.tt == TT.FUNCTION:
                cstack.append(Frame(CT.Function, L, H, R, x, env))
                env = Env(env)
                env.bind("x", L)
                env.bind("self", H)
                env.bind("y", R)
                x = unwrap(H)
                ins = next_ins(x)
                continue
            else:
                raise AssertionError(f"Can't process: {H} of {H.tt}")

        # Skip delims
        if cstack[-1].ct == CT.Delim:
            continue

        # Restore stack frame and apply continuation
        c = cstack.pop()
        ins = c.ct
        if ins == CT.Return:
            return x

        L, H, R, env = c.L, c.H, c.R, c.env
        # print("Restore", L, H, R, c.ct.name, id(env), env)
        if c.ct == CT.Function:
            ins = next_ins(x)
        elif c.ct == CT.Left:
            L = x
        elif c.ct == CT.Head:
            H = x
        elif c.ct == CT.Right:
            R = x
        else:
            assert False
        # print("R", L, H, R)


def Repl(prompt="> "):
    builtins = {k: Leaf(TT.BUILTIN, x) for k, x in BUILTINS.items()}
    special = {k: Leaf(TT.SPECIAL, x) for k, x in SPECIAL.items()}
    env = Env(None, from_dict={
        **special,
        **builtins,
    })
    env = Env(env) # dummy env

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
