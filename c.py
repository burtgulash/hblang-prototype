#!/usr/bin/env python3

from enum import Enum
import re
from typing import NamedTuple, Any


class Tok:

    def __init__(self, tt, x):
        self.tt = tt
        self.x = x

    def __repr__(n):
        return str(n.x)


class Node:

    def __init__(self, tt, L, X, R):
        self.tt = tt
        self.L = L
        self.X = X
        self.R = R

    def __str__(n):
        return f"[{n.L} {n.X} {n.R}]"


class TT(Enum):
    NUM = 1
    SYMBOL = 2
    STRING = 3
    PUNCTUATION = 4
    SEPARATOR = 5
    SPACE = 6
    LPAREN = 7
    RPAREN = 8
    END = 9


def num(tok):
    if tok == "_":
        return ["Num", "Inf"]
    if tok == "__":
        return ["Num", "-Inf"]
    negative = tok[0] == "_"
    tok = tok.replace("_", "")
    num = int(tok)
    num = -num if negative else num
    return num

def identity(x):
    return x

def string(tok):
    return tok[1:-1]


def lex(text):
    rules = (
        (TT.NUM, num, "[_0-9]+"),
        (TT.SYMBOL, identity, "[a-zA-Z][a-zA-Z_]*"),
        (TT.STRING, string, '"([^"]|\\.)*"'),
        (TT.PUNCTUATION, identity, "[!$%&'*+,-./:;<=>?@\\^`~]"),
        (TT.SEPARATOR, identity, "[|\n]"),
        (TT.SPACE, identity, "[ \t]+"),
        (TT.LPAREN, identity, "[({[]"),
        (TT.RPAREN, identity, "[]})]"),
    )
    rx = (f"(?P<{tt.name}>{defn})" for tt, _, defn in rules)
    rx = "|".join(rx)

    transform = {tt.name: fn for tt, fn, _ in rules}
    for x in re.finditer(rx, text):
        tt_name = x.lastgroup
        tt = TT[tt_name]
        tok = x.group(tt_name)
        tok = transform[tt_name](tok)
        yield Tok(tt, tok)


def parse(text):
    toks = lex(text)
    toks = (tok for tok in toks if tok.tt != TT.SPACE)
    toks = list(toks) + [Tok(TT.END, "")]
    stream = toks[::-1]
    Eval(stream)
    return stream.pop()

def REval(stream):
    L = stream.pop()
    X = stream.pop()
    if X.x == ":":
        return Node(X.tt, L, X, REval(stream))
    else:
        # return ")", "\0", or whatever back
        stream.append(X)
        return L

def end_of_expr(x):
    return x.tt in (TT.RPAREN, TT.END)

def Eval(stream):
    while len(stream) > 1:
        L = stream.pop()
        if L.tt == TT.LPAREN:
            Eval(stream)
            if len(stream) == 1:
                break
            L = stream.pop()
        elif L.tt == TT.RPAREN:
            L = "Void"

        X = stream.pop()
        if end_of_expr(X):
            stream.append(L)
            break

        R = stream.pop()
        if R.tt == TT.LPAREN:
            Eval(stream)
            R = stream.pop()

        Z = stream.pop()
        if Z.x == ":":
            R = Node(Z.tt, R, Z, REval(stream))
        else:
            stream.append(Z)

        z = Node(X.tt, L, X, R)
        stream.append(z)

if __name__ == "__main__":
    import sys
    inp = sys.stdin.read()[:-1]
    print(">", inp)
    out = parse(inp)
    print(out)
