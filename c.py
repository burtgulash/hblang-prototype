#!/usr/bin/env python3

from enum import Enum
import re


def right_associative(x):
    return x and x in ":$%"


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
            return "{" + str(self.w) + "}"
        if self.tt == TT.FUNCTION_STUB:
            return "{" + str(self.w) + "}"
        if self.tt == TT.THUNK:
            return f"[{self.w}]"
        if self.tt in (TT.PUNCTUATION, TT.NUM, TT.CONS,
                       TT.SYMBOL, TT.STRING, TT.SEPARATOR):
            return str(self.w)
        return f"({self.w})"


class Tree:

    def __init__(self, L, H, R):
        self.L = L
        self.H = H
        self.R = R

    @property
    def tt(self):
        return TT.TREE

    def show(n, function=False):
        # lparen = '{' if function else '['
        # rparen = '}' if function else ']'
        # return f"{lparen}{n.L} {n.H} {n.R}{rparen}"
        if n.H.tt == TT.SEPARATOR:
            return f"{n.L} | ({n.R})"
        if n.H.tt == TT.SYMBOL:
            return f"({n.L} {n.H} {n.R})"
        if n.H.tt in (TT.PUNCTUATION, TT.CONS):
            if isinstance(n.H, Leaf) and right_associative(n.H.w):
                return f" ({n.L}{n.H}{n.R})"
            return f"({n.L} {n.H}{n.R})"
        return f"{n.L} {n.H}{n.R}"

    def __repr__(self):
        return self.show()


class TT(Enum):
    COMMENT = 1
    UNIT = 2
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
    FUNCTION_STUB = 15
    NEWLINE = 16
    CONTINUATION = 17
    SPECIAL = 18
    TREE = 19
    OBJECT = 20
    CONS = 21

    def __str__(self):
        return self.name


Unit = Leaf(TT.UNIT, "")
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
    tok = tok[1:-1]  # strip quotes
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
        (TT.CONS, identity, "[:.]"),
        (TT.PUNCTUATION, identity, "[-$@&!%*+,?=<>/\\^`~;~]+"),
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


def add_debug_info(toks):
    lines = 0
    for tok in toks:
        if tok.tt in (TT.COMMENT, TT.NEWLINE):
            lines += 1
        if tok.debug is not None:
            tok.debug.lineno = lines
        yield tok


def Lex(text):
    # add extra newline at the end as a sentinel for comments
    toks = lex_(text + "\n")
    toks = add_debug_info(toks)

    # Remove insignificant tokens - spaces and comments
    toks = (tok for tok in toks
            if tok.tt not in (TT.SPACE, TT.COMMENT, TT.NEWLINE))

    yield from toks
    yield EOF


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
        x = Leaf(TT.FUNCTION_STUB, x)
    return x


def opposite_paren(paren):
    return {
        "(": ")",
        "[": "]",
        "{": "}",
    }[paren]


class Buf:

    def __init__(self, stream):
        self.stream = stream
        self.xs = []

    def consume(self):
        """ For debug printing """
        ys = []
        try:
            while True:
                ys += [self.next()]
        except StopIteration:
            pass

        for y in ys[::-1]:
            self.push(y)
        return ys

    def next(self):
        if self.xs:
            return self.xs.pop()
        return next(self.stream)

    def pop(self):
        return self.xs.pop()

    def push(self, x):
        self.xs.append(x)


def Parse(toks):
    stream = Buf(toks)
    # import sys; print(stream.consume(), file=sys.stderr) # TODO debug print
    return LParse(stream, EOF)


# Parse parenthesized subexpressions
# TODO check parenthesis type here or in lexing?
def ParenParse(stream):
    x = stream.next()
    if isinstance(x, Leaf) and x.tt == TT.LPAREN:
        paren_type = x.w
        x = LParse(stream, opposite_paren(paren_type))
        x = quote(x, paren_type)
    return x


def RParse(stream):
    rights = []
    while True:
        R = ParenParse(stream)
        if isinstance(R, Leaf) and end_of_expr(R):
            raise ParseError(f"Invalid expression. R can't be END token: '{R}'")

        rights.append(R)
        H = stream.next()

        if not right_associative(H.w):
            stream.push(H)
            break

        rights.append(H)

    # Reduce right stack to one final tree node
    while len(rights) > 1:
        R = rights.pop()
        H = rights.pop()
        L = rights.pop()
        rights.append(Tree(L, H, R))

    assert len(rights) == 1
    return rights.pop()


def LParse(stream, expected_end):
    # Handle L
    L = ParenParse(stream)
    if end_of_expr(L):
        if not end_matches(L, expected_end):
            raise ParseError(f"Parentheses don't match."
                             f"Expected {expected_end}, got {L.w}")
        return Unit

    while True:
        # Handle H
        H = ParenParse(stream)
        if end_of_expr(H):
            # End of expression
            if not end_matches(H, expected_end):
                raise ParseError(f"Parentheses don't match."
                                 f"Expected {expected_end}, got {H.w}")
            return L

        if H.tt == TT.SEPARATOR:
            # Expression is separated by |
            R = LParse(stream, expected_end)
            return Tree(L, H, R)

        # Parse right token, which could be right leaning
        R = RParse(stream)

        # Create new node from L, H, R gathered above
        L = Tree(L, H, R)


if __name__ == "__main__":
    import sys
    inp = sys.stdin.read()
    print(">", inp)
    toks = Lex(inp)
    # print("LEX", y)
    tree = Parse(toks)
    print(tree)
