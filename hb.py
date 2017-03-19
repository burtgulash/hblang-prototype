#!/usr/bin/env python3

import sys

import readline
from c import Lex, LexTransform, Parse, \
              ParseError, TT, Tree, Leaf, Void

readline.parse_and_bind('tab: complete')
readline.parse_and_bind('set editing-mode vi')

def apply_fn(a, b, env):
    if b.tt == TT.SYMBOL:
        fn = env.lookup(b.w, None)
        if fn is None:
            raise Exception(f"Function not found: {b.w}")
    elif b.tt in (TT.THUNK, TT.FUNCTION):
        fn = b
    else:
        raise AssertionError(f"Apply_fn can't be applied to {b.tt}")
    return Eval(Tree(fn.tt, a, fn, Void), env)


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
    "!": apply_fn,
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
        # print("EVAL", x, file=sys.stderr)
        if isinstance(x, Leaf):
            return x

        assert isinstance(x, Tree)
        L, H, R = x.L, x.H, x.R

        if isinstance(L, Tree):
            L = Eval(L, env)
        if isinstance(R, Tree):
            R = Eval(R, env)

        if H.tt == TT.VOID:
            return H
        elif isinstance(H, Tree):
            H = Eval(H, env)
            x = Tree(H.tt, L, H, R)
        elif H.tt in (TT.PUNCTUATION, TT.SYMBOL, TT.SEPARATOR):
            op = env.lookup(H.w, None)
            assert op is not None
            assert op.tt in (TT.BUILTIN, TT.THUNK, TT.FUNCTION)
            x = Tree(op.tt, L, op, R)
        elif H.tt == TT.BUILTIN:
            return H.w(L, R, env)
        elif H.tt == TT.THUNK:
            env.bind("x", L)
            env.bind("y", R)
            x = H.w
        elif H.tt == TT.FUNCTION:
            env = Env(env)
            env.bind("F", H)
            x = Tree(H.tt, L, H.w, R)
        else:
            raise AssertionError(f"Can't process: {H} of {H.tt}")


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
            # print("PARSE", y)
            y = Eval(y, env)
            if y is not None:
                print(y)
        except ParseError as err:
            print(f"Parse error: {err}", file=sys.stderr)
        except (EOFError, KeyboardInterrupt):
            break


if __name__ == "__main__":
    Repl()
