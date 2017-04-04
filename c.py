#!/usr/bin/env python3

from enum import Enum
import re


def right_associative(x):
    return x and x in "$:"


def parens_match(left, right):
    return ((left == "(" and right == ")")
         or (left == "[" and right == "]")
         or (left == "{" and right == "}"))


class ParseError(Exception):
    pass


class DebugInfo:

    def __init__(self, start, end):
        self.start = start
        self.end = end
        self.lineno = None

    def __repr__(self):
        return (f"Debug(line={self.lineno}"
                f", start={self.start}"
                f", end={self.end})")


class Leaf:

    def __init__(self, tt, w, debug=None):
        self.tt = tt
        self.w = w
        self.debug = debug

    def show(n, function=False):
        # return str(f" {n.tt.name[:3].lower()}{n.w}")
        if isinstance(n.w, Tree):
            return n.w.show(function=n.tt == TT.FUNCTION)
        return str(n.w)

    def __repr__(self):
        if self.tt == TT.FUNCTION:
            return f"{{{self.w}}}"
        if self.tt == TT.CLOSURE:
            return f"{{{self.w[1]}}}"
        if self.tt == TT.THUNK:
            return f"[{self.w}]"
        if self.tt in (TT.PUNCTUATION, TT.NUM,
                       TT.SYMBOL, TT.STRING, TT.SEPARATOR):
            return str(self.w)
        return f"({self.w})"


class Tree:

    def __init__(self, L, H, R):
        self.L = L
        self.H = H
        self.R = R

    def show(n, function=False):
        # lparen = '{' if function else '['
        # rparen = '}' if function else ']'
        # return f"{lparen}{n.L} {n.H} {n.R}{rparen}"
        if n.H.tt == TT.SEPARATOR:
            return f"{n.L} |({n.R})"
        if n.H.tt == TT.SYMBOL:
            return f"({n.L} {n.H} {n.R})"
        if n.H.tt == TT.PUNCTUATION:
            if isinstance(n.H, Leaf) and right_associative(n.H.w):
                return f" ({n.L}{n.H}{n.R})"
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
    CLOSURE = 15
    NEWLINE = 16
    CONTINUATION = 17
    SPECIAL = 18


Void = Leaf(TT.VOID, "void")
EOF = Leaf(TT.END, "END")


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
            escaped = True
            continue
        if escaped:
            c = interpret(c)
            escaped = False
        yield c


def string(tok):
    # tok = tok[1:-1]
    return "".join(unescape(tok))


def symbol(tok):
    assert tok[0] == "`"
    # return tok[1:]
    return tok


def lex_(text):
    rules = (
        (TT.NUM, num, "[_0-9]+"),
        (TT.SYMBOL, identity, "[a-zA-Z][a-zA-Z0-9_]*"),
        (TT.STRING, string, r'"(\\.|[^"])*"'),
        (TT.COMMENT, comment, "#.*\n"),
        (TT.PUNCTUATION, identity, "[!$%&*+,-./:;<=>?@\\^`~]"),
        (TT.SEPARATOR, identity, "[|]"),
        (TT.NEWLINE, identity, "[\n\r]+"),
        (TT.SPACE, identity, "[ \t]+"),
        (TT.LPAREN, identity, "[({[]"),
        (TT.RPAREN, identity, "[]})]"),
    )
    rx = (f"(?P<{tt.name}>{defn})" for tt, _, defn in rules)
    rx = "|".join(rx)
    # print("DEBUG: lex by regex:", rx, file=sys.stderr)

    transform = {tt.name: fn for tt, fn, _ in rules}
    for x in re.finditer(rx, text):
        tt_name = x.lastgroup
        tt = TT[tt_name]
        tok = x.group(tt_name)
        tok = transform[tt_name](tok)
        span = x.span(x.lastindex)
        yield Leaf(tt, tok, debug=DebugInfo(span[0], span[1]))


def Lex(text):
    # add extra newline at the end as a sentinel for comments
    toks = list(lex_(text + "\n"))

    # Remove the \n sentinel if it wasn't used by comment
    if toks[-1].tt == TT.NEWLINE:
        toks = toks[:-1]

    # Add EOF token
    toks += [EOF]

    lines = 0
    for tok in toks:
        if tok.tt in (TT.COMMENT, TT.NEWLINE):
            lines += 1
        if tok.debug is not None:
            tok.debug.lineno = lines

    # print("TOK", [(x, x.debug) for x in toks])

    # Remove insignificant tokens - spaces and comments
    toks = [tok for tok in toks
            if tok.tt not in (TT.SPACE, TT.COMMENT, TT.NEWLINE)]
    return toks


def Parse(toks):
    # Revert list of tokens to form a stack
    stream = list(toks)[::-1]
    LParse(stream, EOF)
    return stream.pop()


def end_of_expr(x):
    return x.tt in (TT.RPAREN, TT.END)


def end_matches(end, expected):
    # print("END", end, expected)
    if end.tt == TT.RPAREN:
        assert expected in ")]}"
        return end.w == expected
    return expected is EOF


def quote(x, paren_type):
    if paren_type == '[':
        x = Leaf(TT.THUNK, x)
    elif paren_type == '{':
        x = Leaf(TT.FUNCTION, x)
    return x

def opposite_paren(paren):
    return {
        "(": ")",
        "[": "]",
        "{": "}",
    }[paren]


# Parse parenthesized subexpressions
# TODO check parenthesis type here or in lexing?
def ParenParse(stream):
    x = stream.pop()
    if isinstance(x, Leaf) and x.tt == TT.LPAREN:
        paren_type = x.w
        LParse(stream, opposite_paren(paren_type))
        x = quote(stream.pop(), paren_type)
    return x


def RParse(stream):
    rights = []
    while True:
        R = ParenParse(stream)
        rights.append(R)
        Y = stream.pop()

        if not right_associative(Y.w):
            stream.append(Y)
            break

        rights.append(Y)

    # Reduce right stack to one final tree node
    while len(rights) > 1:
        R = rights.pop()
        Y = rights.pop()
        L = rights.pop()
        rights.append(Tree(L, Y, R))

    assert len(rights) == 1
    return rights.pop()


def LParse(stream, expected_end):
    while len(stream) > 1:
        # Handle L
        L = ParenParse(stream)
        if isinstance(L, Leaf) and L.tt == TT.RPAREN:
            # TODO check if they match at least
            stream.append(Void)
            break

        # Handle H
        H = ParenParse(stream)
        if H.tt == TT.SEPARATOR:
            # Expression is separated by |
            LParse(stream, expected_end)
            R = stream.pop()
            stream.append(Tree(L, H, R))
            break

        if end_of_expr(H):
            # End of expression
            if not end_matches(H, expected_end):
                raise ParseError(f"Parentheses don't match."
                                 f"Expected {expected_end}, got {H.w}")
            stream.append(L)
            break

        # Parse right token, which could be right leaning
        R = RParse(stream)

        # Create new node from L, H, R gathered above
        stream.append(Tree(L, H, R))


if __name__ == "__main__":
    import sys
    inp = sys.stdin.read()[:-1]
    print(">", inp)
    tree = Parse(inp)
    print(tree)
