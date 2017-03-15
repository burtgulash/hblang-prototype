#!/usr/bin/env python3

import re

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
        ("num", num, "[_0-9]+"),
        ("symbol", identity, "[a-zA-Z][a-zA-Z_]*"),
        ("string", string, '"([^"]|\\.)*"'),
        ("punctuation", identity, "[!$%&'*+,-./:;<=>?@\\^`~]"),
        ("separator", identity, "[|\n]"),
        ("space", identity, "[ \t]+"),
        ("lparen", identity, "[({[]"),
        ("rparen", identity, "[]})]"),
    )
    rx = (f"(?P<{name}>{defn})" for name, _, defn in rules)
    rx = "|".join(rx)

    transform = {name: fn for name, fn, _ in rules}
    for x in re.finditer(rx, text):
        tok_type = x.lastgroup
        tok = x.group(tok_type)
        tok = transform[tok_type](tok)
        yield tok_type, tok


def parse(text):
    toks = list(lex(text))
    print("TOKS", toks)
    toks = [tok for tt, tok in toks if tt != "space"]
    
    stream = (list(toks) + ["\0"])[::-1]
    Eval(stream)
    return stream.pop()

def REval(stream):
    L = stream.pop()
    X = stream.pop()
    if X == ":":
        return [L, X, REval(stream)]
    else:
        # return ")", "\0", or whatever back
        print("RETURN", X, stream[::-1])
        stream.append(X)
        return L


def Eval(stream):
    while len(stream) > 1:
        print("S", stream[::-1])
        L = stream.pop()
        if L == "(":
            Eval(stream)
            if len(stream) == 1:
                break
            L = stream.pop()
        elif L == ")":
            L = "Void"

        X = stream.pop()
        if X in (")", "\0"):
            stream.append(L)
            break

        R = stream.pop()
        if R == "(":
            Eval(stream)
            R = stream.pop()

        Z = stream.pop()
        if Z == ":":
            R = [R, Z, REval(stream)]
        else:
            stream.append(Z)

        print("I", stream[::-1])
        z = [L, X, R]
        stream.append(z)

if __name__ == "__main__":
    import sys
    inp = sys.stdin.read()[:-1]
    print(">", inp)
    out = parse(inp)
    print(out)
