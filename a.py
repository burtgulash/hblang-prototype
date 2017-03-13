#!/usr/bin/env python3

def parse(stream):

class Error(Exception):

    def __init__(self, msg, s):
        self.msg = msg
        self.L = L
        self.X = X
        self.R = R

class S:

    def __init__(self, s):
        self.L = L
        self.X = X
        self.R = R

    def shift(self):
        self.L, self.X, self.R = self.L + [self.X], self.R[0], self.R[1:]


def Finish(result, stream):
    if stream == []:
        return result
    else:
        result.append(Error("Non empty stream"))
        return result

def Either(s, *a):
    for f in a:
        try:
            parsed, s = f(s)
            return parsed, s
        except Error as err:
            pass
    raise Error("No matching rule", s)


def E(s):
    return Either(s, [E1, E2])

def E1_(name, rparen, s):
    s.shift()
    a, s = E(s)
    if s.X == rparen:
        s.shift()
        p, s = T(s)
        return [name, p, s.X], s
    raise Error("[f{name}] right parenthesis missing", s)

def E1(s):
    if s.X == "(":
        return E1_("E1.(", ")", s)
    if s.X == "{":
        return E1_("E1.{", "}", s)

    a, s = A(s)
    return ["E1.a", a], s

def E2(s):
    a, s = A(s)
    t, s = Tn(s)
    return ["E2", a, t], s

def T(s):
    return Either(s, [Tn, Te])

def Tn(s):
    if s.X == ":":
        s.shift()
        p, s = E1(s)
        return ["Tn.1", p]

    a, s = E(s)
    b, s = E(s)
    return ["Tn.2", a, b], s

def Te(s):
    return ["Empty"], s

def A(s):
    return Either(s, [Punc, Number, String])

def Punc(s):
    char = s.X
    assert len(char) == 1
    symbols = "!$%&'*+,-./:;<=>?@\^`|~"
    if char in symbols:
        s.shift()
        return ["Punc", char], s
    raise Error("f{s.X} is not a punctuation symbol")

def Number_(s):
    digit = s.X
    assert len(digit) == 1
    if digit.isnumeric():
        s.shift()
        return digit, Number_(s), s
    return "", "", s

def Number(s):
    x, xs, s = Number_(s)
    if x == "":
        raise Error("Can't parse number", s)

    try:
        num = x + xs
        return int(num)
    except ValueError:
        return Error("f{num} can't be parsed as a number", s)

def String(s):
    return Either(s, [Simple_string, Enclosed_string])

def Simple_string_(s):
    char = s.X
    assert len(char) == 1
    symbols = "_abcdefghijklmnopqrstuvwxyz"
    if char.lower() in symbols:
        s.shift()
        return char, Simple_string_(s), s
    return "", "", s

def Simple_string(s):
    x, xs, s = Simple_string_(s)
    if x == "":
        raise Error("Can't parse 'Simple string'", s)
    return ["Simple_string", x + xs], s

def Enclosed_string_(s):
    char = s.X
    assert len(char) == 1
    if char == '"':
        return "", s
    s.shift()
    return char, Enclosed_string_(s), s

def Enclosed_string(s):
    if s.X != '"':
        raise Error("String doesn't start with '\"'", s)
    x, xs, s = Enclosed_string_(s)
    return ["Enclosed_string", x + xs], s
