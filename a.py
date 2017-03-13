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
    assert len(s) == 1
    if s.X in "!$%&'*+,-./:;<=>?@\^`|~":
        return ["Punc", s.X]


