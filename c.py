#!/usr/bin/env python3


def parse(stream):
    stream = (list(stream) + ["\0"])[::-1]
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
    inp = sys.stdin.read().strip()
    print(">", inp)
    out = parse(inp)
    print(out)
