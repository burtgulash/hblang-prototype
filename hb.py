#!/usr/bin/env python3

import sys

import readline
from c import Lex, Parse, ParseError, TT, Node, Tok

readline.parse_and_bind('tab: complete')
readline.parse_and_bind('set editing-mode vi')

global_env = {
    "+": lambda a, b: Tok(TT.NUM, a + b),
    "-": lambda a, b: Tok(TT.NUM, a - b),
    "*": lambda a, b: Tok(TT.NUM, a * b),
    "/": lambda a, b: Tok(TT.NUM, a // b),
    ".": lambda a, b: Node(TT.PUNCTUATION, a, ".", b),
    ":": lambda a, b: Node(TT.PUNCTUATION, a, ":", b),
}

class Env:

    def __init__(self, parent, from_dict=None):
        self.parent = parent
        self.e = {**from_dict} or {}

    def lookup(self, name: str):
        assert isinstance(name, str)
        env = self.find_env(name)
        if not env:
            return None
        return env.e[name]

    def find_env(self, name: str):
        assert isinstance(name, str)
        if name in self.e:
            return self
        elif self.parent is not None:
            return self.parent.find_env(name)
        return None

    def bind(self, name: str, value):
        assert isinstance(name, str)
        self.e[name] = value

    def assign(self, name: str, value):
        assert isinstance(name, str)
        env = self.find_env(name) or self
        env.bind(name, value)
        

def apply(x, env):
    L, X, R = x.L, x.X, x.R
    op = env.lookup(X.x)
    if isinstance(x.L, Node):
        L = Eval(x.L, env)
    if isinstance(x.R, Node):
        R = Eval(x.R, env)
    return op(L.x, R.x)


def Eval(x, env):
    if x.tt == TT.PUNCTUATION:
        return apply(x, env)
    return x


def Repl(prompt="> "):
    env = Env(None, from_dict=global_env)
    while True:
        try:
            y = input(prompt)
            y = Lex(y)
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
