#!/usr/bin/env python3

import sys

import readline
from c import Lex, LexTransform, Parse, \
              ParseError, TT, Tree, Leaf, Void


class Return(Exception):
    pass


def callcc(block, k, env):
    assert block.tt in (TT.THUNK, TT.FUNCTION)
    assert k.tt in (TT.SYMBOL, TT.STRING)

    brk = Return()
    def break_out(a, _, env):
        brk.retval = a
        raise brk

    env = Env(env)
    env.bind(k.w, Leaf(TT.BUILTIN, break_out))
    try:
        return Eval(Tree(block.tt, Void, block, Void), env)
    except Return as ret:
        if ret is brk:
            return ret.retval
        raise


def setenv(H, env):
    self_f = env.lookup("self", None)
    parent_env = env.parent if self_f is H else env
    env = Env(parent_env)
    return env


def get_type(a, b, env):
    return Leaf(TT.SYMBOL, a.tt.name)


def unwrap(H):
    assert H.tt in (TT.FUNCTION, TT.THUNK)
    return H.w


def bake(a, _, env):
    assert a.tt == TT.FUNCTION
    return Leaf(a.tt, bake_2(unwrap(a), env))


def bake_(x, env):
    if isinstance(x, Tree):
        L, H, R = bake_(x.L, env), bake_(x.H, env), bake_(x.R, env)
        if TT.THUNK not in (L.tt, H.tt, R.tt):
            x = Tree(H.tt, L, H, R)
            return Eval(x, env)
        L, H, R = unthunk(L, env), unthunk(H, env), unthunk(R, env)
        return Tree(H.tt, L, H, R)
    return unthunk(x, env)


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

def unthunk(x, env):
    if x.tt == TT.THUNK:
        return x.w
    elif x.tt == TT.FUNCTION:
        return x
    return Eval(x, env)


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
    "@": lambda a, b, env: env.assign(b.w, a),
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
    "callcc": callcc,
    "P": P,
}

VARIABLES = {
    "Vec": Leaf(TT.NUM, []),
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

    def assign(self, name, value):
        env = self.find_env(name) or self
        env.bind(name, value)
        return value


def Eval(x, env):
    while True:
        if isinstance(x, Leaf):
            return x

        assert isinstance(x, Tree)
        L, H, R = x.L, x.H, x.R

        if isinstance(L, Tree):
            L = Eval(L, env)
        if isinstance(H, Tree):
            H = Eval(H, env)
        # x = Tree(H.tt, L, H, R) # TODO why this??

        if H.tt == TT.SEPARATOR:
            # Tail recurse on separator '|' before R gets evaluated
            x = R
            continue

        if isinstance(R, Tree):
            R = Eval(R, env)

        # print("EVAL", x, file=sys.stderr)
        # print("L", L, file=sys.stderr)
        # print("R", R, file=sys.stderr)

        if H.tt == TT.THUNK:
            x = unwrap(H)
        elif H.tt == TT.FUNCTION:
            env = setenv(H, env)
            env.bind("self", H)
            env.bind("x", L)
            env.bind("y", R)
            x = unwrap(H)
        elif H.tt == TT.PUNCTUATION and H.w in ".:":
            return Tree(H.tt, L, H, R)
        elif H.tt in (TT.PUNCTUATION, TT.SYMBOL, TT.SEPARATOR):
            op = env.lookup(H.w, None)
            if op is None:
                raise Exception(f"Operator not found {H.w}")
            assert op.tt in (TT.BUILTIN, TT.THUNK, TT.FUNCTION)
            x = Tree(op.tt, L, op, R)
        elif H.tt == TT.BUILTIN:
            x = H.w(L, R, env)
        elif H.tt == TT.VOID:
            return H
        else:
            raise AssertionError(f"Can't process: {H} of {H.tt}")


def Repl(prompt="> "):
    builtins = {k: Leaf(TT.BUILTIN, x) for k, x in BUILTINS.items()}
    builtins = {**builtins, **VARIABLES}
    env = Env(None, from_dict=builtins)

    while True:
        try:
            y = input(prompt)
            y = Lex(y)
            y = LexTransform(y)
            #print("LEX", y)
            y = Parse(y)
            # print("PARSE", y)
            y = Eval(y, env)
            if y is not None:
                print(y)
        except ParseError as err:
            print(f"Parse error: {err}", file=sys.stderr)
        except (EOFError, KeyboardInterrupt):
            break


if __name__ == "__main__":
    readline.parse_and_bind('tab: complete')
    readline.parse_and_bind('set editing-mode vi')
    Repl()
