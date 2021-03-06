#!/usr/bin/env python3

from enum import Enum
import re


class WitnessedError(Exception):

    def __init__(self, msg, witness):
        super().__init__(msg)
        self.msg = msg
        self.witness = witness


class ParseError(WitnessedError):
    pass


class DebugInfo:

    def __init__(self, start, end, lineno):
        self.start = start
        self.end = end
        self.lineno = lineno

    @staticmethod
    def from_lr(L, R):
        # Inherit line from start # NOTE merge start to end lines in error report
        start = L.debug.start if L.debug is not None else None
        end = R.debug.end if R.debug is not None else None
        lineno = L.debug.start if L.debug is not None else None
        return DebugInfo(start, end, lineno)

    def __str__(self):
        return (f"Debug(line={self.lineno}"
                f", start={self.start}"
                f", end={self.end})")

    def __repr__(self):
        return str(self)


class Leaf:

    def __init__(self, tt, w, debug=None):
        self.tt = tt
        self.w = w
        self.debug = debug
        # if debug is None:
        #     import sys
        #     print("WARNING: None debug", tt, w, file=sys.stderr)

    def show(n, function=False):
        # return str(f" {n.tt.name[:3].lower()}{n.w}")
        if isinstance(n.w, Tree):
            return n.w.show(function=n.tt == TT.FUNCTION)
        return str(n.w)

    def __repr__(self):
        if self.tt in (TT.FUNCTION, TT.FUNTHUNK):
            return "{" + str(self.w) + "}"
        if self.tt == TT.THUNK:
            return f"[{self.w}]"
        if self.tt == TT.UNIT:
            return "()"
        # if self.tt in (TT.PUNCTUATION, TT.NUM, TT.CONS,
        #                TT.SYMBOL, TT.STRING, TT.SEPARATOR):
        #     return str(self.w)
        if self.tt == TT.OBJECT:
            # Print object, don't follow parent pointer
            return repr({k: v for k, v in self.w.e.items() if k != ":"})
        return f"{self.w}"


class Tree:

    def __init__(self, L, H, R, debug=None):
        self.L = L
        self.H = H
        self.R = R
        self.debug = debug

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
        if n.H.tt == TT.PUNCTUATION:
            if isinstance(n.H, Leaf) and right_associative(n.H):
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
    NEWLINE = 15
    CONTINUATION = 16
    SPECIAL = 17
    TREE = 18
    OBJECT = 19
    #CONS = 20
    NATIVE_OBJECT = 20
    ERROR = 21
    FUNTHUNK = 22

    def __str__(self):
        return self.name

    def __eq__(self, other):
        return self.name == str(other)

    def __hash__(self):
        return hash(self.name)


Unit = Leaf(TT.UNIT, "", debug=DebugInfo(0, 0, 0))
#EOF = Leaf(TT.END, "END")


def right_associative(x):
    return x and x.tt == TT.PUNCTUATION and x.w.startswith(":")
    # return x and x in [":", "$", "%", "!%"]


def parens_match(left, right):
    return ((left == "(" and right == ")")
         or (left == "[" and right == "]")
         or (left == "{" and right == "}"))


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
        (TT.SYMBOL, identity, "_*[a-zA-Z][a-zA-Z0-9_]*"),
        (TT.NUM, num, "[_0-9]+"),
        (TT.STRING, string, r'"(\\.|[^"])*"'),
        (TT.COMMENT, comment, "#.*\n"),
        #(TT.CONS, identity, "[:.]"),
        (TT.PUNCTUATION, identity, r"[-$@&!%*+,?=<>/\^`~;:]+|\."),
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
        yield Leaf(tt, tok, debug=DebugInfo(span[0], span[1], None))


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

    last = Leaf(TT.UNIT, None, debug=DebugInfo(0, 0, 0))
    for tok in toks:
        last = tok
        # print((last, last.debug), file=sys.stderr)
        yield tok

    yield Leaf(TT.END, "END", debug=DebugInfo(last.debug.end, last.debug.end + 1, last.debug.lineno))


def end_of_expr(x):
    return x.tt in (TT.RPAREN, TT.END)


def end_matches(end, expected):
    # print("END", end, expected)
    if end.tt == TT.RPAREN:
        # assert expected in ")]}"
        return end.w == expected
    # return expected is EOF
    return expected == TT.END


def quote(x, paren_type):
    if paren_type == '[':
        x = Leaf(TT.THUNK, x, debug=x.debug)
    elif paren_type == '{':
        x = Leaf(TT.FUNTHUNK, x, debug=x.debug)
        #x = Tree(Leaf(TT.THUNK, x, debug=x.debug), Leaf(TT.SYMBOL, "func"), Unit)
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
    return LParse(stream, TT.END)


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
            raise ParseError(f"Invalid expression. R can't be END token: '{R}'", R)

        rights.append(R)
        H = stream.next()

        if not right_associative(H):
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
            raise ParseError(f"Parentheses don't match. "
                             f"Expected {expected_end}, got {L.w}", L)
        return Unit

    while True:
        # Handle H
        H = ParenParse(stream)
        if end_of_expr(H):
            # End of expression
            if not end_matches(H, expected_end):
                raise ParseError(f"Parentheses don't match. "
                                 f"Expected {expected_end}, got {H.w}", H)
            return L

        if H.tt == TT.SEPARATOR:
            # Expression is separated by |
            R = LParse(stream, expected_end)
            return Tree(L, H, R, debug=DebugInfo.from_lr(L, R))

        # Parse right token, which could be right leaning
        R = RParse(stream)

        # Create new node from L, H, R gathered above
        L = Tree(L, H, R, debug=DebugInfo.from_lr(L, R))


if __name__ == "__main__":
    import sys
    inp = sys.stdin.read()
    print(">", inp)
    toks = Lex(inp)
    # print("LEX", y)
    tree = Parse(toks)
    print(tree)
