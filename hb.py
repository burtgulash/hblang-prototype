#!/usr/bin/env python3

import sys

import readline
from c import Lex, Parse, ParseError

readline.parse_and_bind('tab: complete')
readline.parse_and_bind('set editing-mode vi')


class Env:

    def __init__(self, parent):
        self.parent = parent


def Eval(x, env):
    return x


def Repl(prompt="> "):
    env = Env(None)
    while True:
        try:
            y = Eval(Parse(Lex(input(prompt))), env)
            if y is not None:
                print(y)
        except ParseError as err:
            print(f"Parse error: {err}", file=sys.stderr)
        except EOFError:
            break


if __name__ == "__main__":
    Repl()
