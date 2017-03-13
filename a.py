#!/usr/bin/env python3

import sys


class Error(Exception):

    def __init__(self, msg, s):
        self.msg = msg
        self.L = s.L
        self.X = s.X
        self.R = s.R

class NoMatch(Exception):
    pass


class S:

    def __init__(self, L, X, R):
        self.L = L
        self.X = X
        self.R = R

    def shift(self):
        return S(self.L + self.X, self.R[0], self.R[1:])

    def __str__(self):
        return f"'{self.L}|{self.X}|{self.R}'"

    def __repr__(self):
        return f"S({str(self)})"


def Finish(result, stream):
    if stream == []:
        return result
    else:
        result.append(Error("Non empty stream"))
        return result

def Either(s, fs):
    for f in fs:
        try:
            # print(f"TRYING {f.__name__} '{(s.X)}'")
            parsed, s = f(s)
            return parsed, s
        except Error as err:
            pass

    raise NoMatch("No matching rule", s)

def E(s):
    s = Space(s)
    p, s = E_(s)
    s = Space(s)
    return p, s

def Eh(name, rparen, s):
    a, s = E(s.shift())
    if s.X == rparen:
        p, s = T(s.shift())
        return [name, a, p], s
    raise Error("[f{name}] right parenthesis missing", s)

def E_(s):
    if s.X == "(":
        return Eh("E.(", ")", s)
    if s.X == "{":
        return Eh("E.{", "}", s)

    a, s = A(s)
    t, s = Ts(s)
    return ["E.a", a, t], s

def Ts(s):
    s = Space(s)
    return T(s)

def T(s):
    if s.X == ":":
        p, s = E(s.shift())
        return ["T.:", p], s

    ss = s
    try:
        a, s = E(s)
        b, s = E(s)
        return ["T.E", a, b], s
    except NoMatch as err:
        return ["Eps"], ss

def A(s):
    return Either(s, [Punc, Number, String])

def Space(s):
    char = s.X
    if char in " \t":
        return Space(s.shift())
    return s

def Punc(s):
    char = s.X
    assert len(char) == 1
    symbols = "!$%&'*+,-./:;<=>?@\^`|~"
    if char in symbols:
        return ["Punc", char], s.shift()
    raise Error(f"{char} is not a punctuation symbol", s)

def Number_(s):
    digit = s.X
    assert len(digit) == 1
    if digit == "_" or digit.isnumeric():
        rest, s = Number_(s.shift())
        return digit + rest, s
    return "", s

def Number(s):
    x, s = Number_(s)
    if x == "":
        raise Error("Can't parse number", s)
    return ["Num", x], s

def String(s):
    return Either(s, [Simple_string, Enclosed_string])

def Simple_string_(s):
    char = s.X
    assert len(char) == 1
    symbols = "_abcdefghijklmnopqrstuvwxyz"
    if char.lower() in symbols:
        s = s.shift()
        print("CHAR", char)
        string, s = Simple_string_(s)
        return char + string, s
    return "", s

def Simple_string(s):
    string, s = Simple_string_(s)
    if string == "":
        raise Error("Can't parse 'Simple string'", s)
    return ["Simple_string", string], s

def Enclosed_string_(s):
    char = s.X
    assert len(char) == 1
    if char == '"':
        return "", s
    string, s = Enclosed_string_(s.shift())
    return char, string, s

def Enclosed_string(s):
    if s.X != '"':
        raise Error("String doesn't start with '\"'", s)
    x, xs, s = Enclosed_string_(s)
    return ["Enclosed_string", x + xs], s

def parse(text):
    L, X, R = "", text[0], text[1:] + "\0"
    s = S(L, X, R)
    try:
        p, s = E(s)
        if len(s.R) > 0:
            raise Error("Tail not consumed", s)
        return p, s
    except Error as err:
        print(f"Parse error: {err.msg} in {s}", file=sys.stderr)
        return ["Error", err]

def main():
    text = sys.stdin.read().rstrip("\n")
    print(f"Parsing '{text}'")
    tree, seq = parse(text)
    print(tree)

if __name__ == "__main__":
    main()
