#!/usr/bin/env python3

import sys

import readline
from c import Lex, LexTransform, Parse, ParseError, TT, Tree, Leaf

readline.parse_and_bind('tab: complete')
readline.parse_and_bind('set editing-mode vi')

BUILTINS = {
    "+": lambda a, b, env: Leaf(TT.NUM, a.w + b.w),
    "-": lambda a, b, env: Leaf(TT.NUM, a.w - b.w),
    "*": lambda a, b, env: Leaf(TT.NUM, a.w * b.w),
    "/": lambda a, b, env: Leaf(TT.NUM, a.w // b.w),
    ".": lambda a, b, env: Tree(TT.PUNCTUATION, a, ".", b),
    ":": lambda a, b, env: Tree(TT.PUNCTUATION, a, ":", b),
    "|": lambda a, b, env: b,
    "$": lambda a, b, env: env.lookup(a.w, b),
    "@": lambda a, b, env: env.assign(b.w, a),
}

class Env:

    def __init__(self, parent, from_dict=None):
        self.parent = parent
        self.e = {**from_dict} or {}

    def lookup(self, name, or_else):
        env = self.find_env(name)
        if not env:
            return or_else
        return env.e[name]

    def find_env(self, name):
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


def apply(L, H, R, env):
    if isinstance(L, Tree):
        L = Eval(L, env)
    if isinstance(R, Tree):
        R = Eval(R, env)

    return H(L, R, env)

def apply_thunk(L, H, R, env):
    if isinstance(L, Tree):
        L = Eval(L, env)
    if isinstance(R, Tree):
        R = Eval(R, env)

    env.bind("x", L)
    env.bind("y", R)
    return Eval(H, env)

def apply_function(L, H, R, env):
    F = Leaf(TT.THUNK, H)
    env = Env(env)
    env.bind("F", F)
    return apply_thunk(L, F.w, R, env)


def Eval(x, env):
    if isinstance(x, Leaf):
        return x
    elif isinstance(x, Tree):
        if x.H.tt == TT.VOID:
            return x.H

        if isinstance(x.H, Tree):
            print("ISTREE", x.tt)
            x = Eval(x.H, env)

        print("TT", x, x.H, x.H.tt)
        if x.H.tt in (TT.PUNCTUATION, TT.SYMBOL, TT.SEPARATOR):
            op = env.lookup(x.H.w, None)
            assert op is not None
            if op.tt == TT.BUILTIN:
                return apply(x.L, op.w, x.R, env)
            if op.tt == TT.FUNCTION:
                return apply_function(x.L, op.w, x.R, env)
        elif x.H.tt == TT.THUNK:
            return apply_thunk(x.L, x.H.w, x.R, env)
        elif x.H.tt == TT.FUNCTION:
            return apply_function(x.L, x.H.w, x.R, env)

    assert False


def Repl(prompt="> "):
    builtins = {k: Leaf(TT.BUILTIN, x) for k, x in BUILTINS.items()}
    env = Env(None, from_dict=builtins)
    while True:
        try:
            y = input(prompt)
            y = Lex(y)
            y = LexTransform(y)
            #print("LEX", y)
            y = Parse(y)
            print("PARSE", y)
            y = Eval(y, env)
            if y is not None:
                print(y)
        except ParseError as err:
            print(f"Parse error: {err}", file=sys.stderr)
        except (EOFError, KeyboardInterrupt):
            break


if __name__ == "__main__":
    Repl()
