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
    COMMENT = 1
    NUM = 2
    VAR = 3
    SYMBOL = 4
    STRING = 5
    PUNCTUATION = 6
    SEPARATOR = 7
    SPACE = 8
    LPAREN = 9
    RPAREN = 10
    END = 11

def comment(tok):
    return tok[1:-1]

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

def interpret(c):
    return {
        "n": "\n",
        "r": "\r",
        "t": "\t",
        '"': '"',
        "'": "'",
    }[c]

def unescape(s):
    escaped = False
    for c in s:
        if c == "\\":
            escaped=True
            continue
        if escaped:
            c = interpret(c)
            escaped = False
        yield c

def string(tok):
    tok = tok[1:-1]
    return "".join(unescape(tok))

def symbol(tok):
    assert tok[0] == "`"
    # return tok[1:]
    return tok

SYMBOL_RX = "[a-zA-Z][a-zA-Z_]*"

def lex(text):
    rules = (
        (TT.NUM, num, "[_0-9]+"),
        (TT.VAR, identity, SYMBOL_RX),
        # use backtick for symbol because of bash escaping
        (TT.SYMBOL, symbol, "`" + SYMBOL_RX),
        (TT.STRING, string, '"(?:[^"]|\\\")*"'),
        (TT.COMMENT, comment, "#.*\n"),
        (TT.PUNCTUATION, identity, "[!$%&*+,-./:;<=>?@\\^`~]"),
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


def Parse(text):
    toks = lex(text + "\n")  # extra newline as a sentinel for comments
    toks = (tok for tok in toks if tok.tt not in (TT.SPACE, TT.COMMENT))
    toks = list(toks)

    # Remove the \n sentinel if it wasn't used by comment
    if toks[-1].tt == TT.SEPARATOR:
        toks = toks[:-1]

    toks = toks + [Tok(TT.END, "")]

    # Revert list to form a stack
    stream = toks[::-1]
    LParse(stream)
    return stream.pop()

def RParse(stream):
    L = stream.pop()
    X = stream.pop()
    if X.x == ":":
        return Node(X.tt, L, X, RParse(stream))
    else:
        # return ")", "\0", or whatever back
        stream.append(X)
        return L

def end_of_expr(x):
    return x.tt in (TT.RPAREN, TT.END)

def LParse(stream):
    while len(stream) > 1:
        L = stream.pop()
        if L.tt == TT.LPAREN:
            LParse(stream)
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
            LParse(stream)
            R = stream.pop()

        Z = stream.pop()
        if Z.x == ":":
            R = Node(Z.tt, R, Z, RParse(stream))
        else:
            stream.append(Z)

        z = Node(X.tt, L, X, R)
        stream.append(z)


if __name__ == "__main__":
    import sys
    inp = sys.stdin.read()[:-1]
    print(">", inp)
    tree = Parse(inp)
    print(tree)
