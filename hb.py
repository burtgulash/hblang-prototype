#!/usr/bin/env python3

import sys

import readline
from c import Lex, LexTransform, Parse, ParseError, TT, Tree, Leaf

readline.parse_and_bind('tab: complete')
readline.parse_and_bind('set editing-mode vi')

global_env = {
    "+": lambda a, b, env: Leaf(TT.NUM, a.w + b.w),
    "-": lambda a, b, env: Leaf(TT.NUM, a.w - b.w),
    "*": lambda a, b, env: Leaf(TT.NUM, a.w * b.w),
    "/": lambda a, b, env: Leaf(TT.NUM, a.w // b.w),
    ".": lambda a, b, env: Tree(TT.PUNCTUATION, a, ".", b),
    ":": lambda a, b, env: Tree(TT.PUNCTUATION, a, ":", b),
    "|": lambda a, b, env: b,
    "$": lambda a, b, env: env.lookup(b.w, a),
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
        

def apply(x, env):
    L, H, R = x.L, x.H, x.R
    op = env.lookup(H.w, None)
    if isinstance(L, Tree):
        L = Eval(L, env)
    if isinstance(R, Tree):
        R = Eval(R, env)

    assert op is not None
    return op(L, R, env)


def Eval(x, env):
    if isinstance(x, Leaf):
        pass
    elif isinstance(x, Tree):
        if isinstance(x.H, Tree):
            y = Eval(x.H, env)
            y = Tree(x.L, y, x.R)
            if y.tt == TT.PUNCTUATION:
                y = apply(y, env)
            x = Eval(y, env)

        x = apply(x, env)

    return x


def Repl(prompt="> "):
    env = Env(None, from_dict=global_env)
    while True:
        try:
            y = input(prompt)
            y = Lex(y)
            y = LexTransform(y)
            #print("LEX", y)
            y = Parse(y)
            y = Eval(y, env)
            if y is not None:
                print(y)
        except ParseError as err:
            print(f"Parse error: {err}", file=sys.stderr)
        except (EOFError, KeyboardInterrupt):
            break


if __name__ == "__main__":
    Repl()
