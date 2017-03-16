#!/usr/bin/env python3

import readline
from c import Parse

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
        y = Eval(Parse(input(prompt)), env)
        if y is not None:
            print(y)


if __name__ == "__main__":
    Repl()
