#!/usr/bin/env python3

from enum import Enum
import re
from typing import NamedTuple, Any



def right_associative(x):
    return x and x in ":$"

def parens_match(left, right):
    return ((left == "(" and right == ")")
         or (left == "[" and right == "]")
         or (left == "{" and right == "}"))


class ParseError(Exception):
    pass


class Leaf:

    def __init__(self, tt, w):
        self.tt = tt
        self.w = w

    def show(n, function=False):
        #return str(f" {n.tt.name[:3].lower()}{n.w}")
        if isinstance(n.w, Tree):
            return n.w.show(function=n.tt == TT.FUNCTION)
        return str(n.w)

    def __repr__(self):
        if self.tt == TT.FUNCTION:
            return f"{{{self.w}}}"
        if self.tt == TT.THUNK:
            return f"[{self.w}]"
        if self.tt in (TT.PUNCTUATION, TT.NUM,
                       TT.SYMBOL, TT.STRING, TT.SEPARATOR):
            return str(self.w)
        return f"({self.w})"


class Tree:

    def __init__(self, tt, L, H, R):
        self.tt = tt
        self.L = L
        self.H = H
        self.R = R

    def show(n, function=False):
        lparen = '{' if function else '['
        rparen = '}' if function else ']'
        #return f"{lparen}{n.L} {n.H} {n.R}{rparen}"
        if n.H.tt == TT.SEPARATOR:
            return f"{n.L} |({n.R})"
        if n.H.tt == TT.PUNCTUATION and right_associative(n.H.w):
            return f" {n.L}{n.H}{n.R}"
        if n.H.tt == TT.SYMBOL:
            return f"({n.L} {n.H} {n.R})"
        if n.H.tt == TT.PUNCTUATION:
            return f"({n.L} {n.H}{n.R})"
        return f"{n.L} {n.H}{n.R}"

    def __repr__(self):
        return self.show()


class TT(Enum):
    COMMENT = 1
    VOID = 2
    NUM = 3
    SYMBOL = 4
    STRING = 5
    PUNCTUATION = 6
    SEPARATOR = 7
    SPACE = 8
    LPAREN = 9
    RPAREN = 10
    THUNK = 11
    FUNCTION = 12
    BUILTIN = 13
    END = 14


Void = Leaf(TT.VOID, "void")


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
    #tok = tok[1:-1]
    return "".join(unescape(tok))

def symbol(tok):
    assert tok[0] == "`"
    # return tok[1:]
    return tok

def void(tok):
    return re.sub(f"{SPACE_RX}+", "", tok)


def lex_(text):
    rules = (
        (TT.NUM, num, "[_0-9]+"),
        (TT.SYMBOL, identity, "[a-zA-Z][a-zA-Z0-9_]*"),
        (TT.STRING, string, r'"(\\.|[^"])*"'),
        (TT.COMMENT, comment, "#.*\n"),
        (TT.PUNCTUATION, identity, "[!$%&*+,-./:;<=>?@\\^`~]"),
        (TT.SEPARATOR, identity, "[|]"),
        (TT.SPACE, identity, "[ \t\n\r]+"),
        (TT.LPAREN, identity, "[({[]"),
        (TT.RPAREN, identity, "[]})]"),
    )
    rx = (f"(?P<{tt.name}>{defn})" for tt, _, defn in rules)
    rx = "|".join(rx)
    #print("DEBUG: lex by regex:", rx, file=sys.stderr)

    transform = {tt.name: fn for tt, fn, _ in rules}
    for x in re.finditer(rx, text):
        tt_name = x.lastgroup
        tt = TT[tt_name]
        tok = x.group(tt_name)
        tok = transform[tt_name](tok)
        yield Leaf(tt, tok)


def Lex(text):
    # add extra newline at the end as a sentinel for comments
    toks = list(lex_(text + "\n"))

    # Remove the \n sentinel if it wasn't used by comment
    if toks[-1].tt == TT.SEPARATOR:
        toks = toks[:-1]

    # Add EOF token
    return toks + [Leaf(TT.END, "END")]


def find_voids(toks):
    continue_next = False
    for x, y in zip(toks, toks[1:] + [toks[:-1]]):
        if continue_next:
            continue_next = False
            continue
        if x.tt == TT.LPAREN and y.tt == TT.RPAREN:
            continue_next = True
            if parens_match(x.w, y.w):
                yield Void
            else:
                raise ParseError(f"Mismatched parentheses {x.w}{y.w}")
        else:
            yield x


def LexTransform(toks):
    # Remove insignificant tokens - spaces and comments
    toks = [tok for tok in toks if tok.tt not in (TT.SPACE, TT.COMMENT)]

    # Change (), [], {} to VOID
    toks = list(find_voids(toks))

    # Check for correctness
    n_toks = len([x for x in toks
                  if x.tt not in (TT.LPAREN, TT.RPAREN, TT.END)])
    if n_toks % 2 == 0:
        raise ParseError(f"Even number [{n_toks}] of tokens."
                         " Only odd allowed.")

    return toks


def Parse(toks):
    # Revert list of tokens to form a stack
    stream = toks[::-1]
    LParse(stream)
    return stream.pop()


def end_of_expr(x):
    return x.tt in (TT.RPAREN, TT.END)

def quote(stream, paren_type):
    x = stream.pop()
    if paren_type == '[':
        x = Leaf(TT.THUNK, x)
    elif paren_type == '{':
        x = Leaf(TT.FUNCTION, x)
    return x

def LParse(stream):
    while len(stream) > 1:
        # Handle L
        L = stream.pop()
        if L.tt == TT.LPAREN:
            paren_type = L.w
            # Case when first token is a nested expression
            LParse(stream)
            if len(stream) == 1:
                break
            L = quote(stream, paren_type)

        # This must be handled by lexing void
        assert L.tt != TT.RPAREN

        # Handle H
        H = stream.pop()
        if H.tt == TT.LPAREN:
            # Case when operator is wrapped in nested ewpression
            LParse(stream)
            H = quote(stream, H.w)

        if H.tt == TT.SEPARATOR:
            # Expression is separated by |
            LParse(stream)
            R = stream.pop()
            stream.append(Tree(H.tt, L, H, R))
            break

        if end_of_expr(H):
            # End of expression
            stream.append(L)
            break

        # Handle R
        R = stream.pop()
        if R.tt == TT.LPAREN:
            # Right parameter of expression is in nested subexpression
            LParse(stream)
            R = quote(stream, R.w)

        Z = stream.pop()
        if right_associative(Z.w):
            # Right associative operator found. Handle recursively
            LParse(stream)
            R = Tree(Z.tt, R, Z, stream.pop())
            stream.append(Tree(H.tt, L, H, R))
            break
        else:
            # Else just return the lookahead token back
            stream.append(Z)

        # Create new node from L, H, R gathered above
        stream.append(Tree(H.tt, L, H, R))


if __name__ == "__main__":
    import sys
    inp = sys.stdin.read()[:-1]
    print(">", inp)
    tree = Parse(inp)
    print(tree)
