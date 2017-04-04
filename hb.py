#!/usr/bin/env python3

import sys
import time

import readline
from c import Lex, Parse, \
              ParseError, TT, Tree, Leaf, Void

from stack import Cactus, CT, Frame


DISPATCH_SEP = ":"

class NoDispatch(Exception):
    pass


class CantReduce(Exception):
    pass


def reset(a, b, cstack, env):
    cstack.spush()
    if isinstance(b, Leaf) and b.tt == TT.THUNK:
        b = b.w
    return b, cstack, env


def shift(a, b, cstack, env):
    cc = cstack.spop()
    # Don't let the continuation binding propagate to parent environment
    env = Env(env)
    # So far continuation is just a pair of st and env
    continuation = Leaf(TT.CONTINUATION, (cc, env))
    env.bind("cc", continuation)
    if isinstance(b, Leaf) and b.tt == TT.THUNK:
        b = b.w
    return b, cstack, env


def setenv(H, env):
    self_f = env.lookup("self", None)
    if self_f is H:
        return env
    return Env(env)


def get_type(a, b, env):
    if isinstance(a, Tree):
        return Leaf(TT.SYMBOL, "Tree")
    return Leaf(TT.SYMBOL, a.tt.name)


def unwrap(H):
    assert H.tt in (TT.FUNCTION, TT.THUNK, TT.CLOSURE)
    if H.tt == TT.CLOSURE:
        return H.w[1]
    return H.w


# def bake(a, _, env):
#     assert a.tt == TT.FUNCTION
#     return Leaf(a.tt, bake_2(unwrap(a), env))


# def bake_(x, env):
#     if isinstance(x, Tree):
#         L, H, R = bake_(x.L, env), bake_(x.H, env), bake_(x.R, env)
#         if TT.THUNK not in (L.tt, H.tt, R.tt):
#             x = Tree(H.tt, L, H, R)
#             return Eval(x, env)
#         L, H, R = unthunk(L, env), unthunk(H, env), unthunk(R, env)
#         return Tree(H.tt, L, H, R)
#     return unthunk(x, env)
#
#
 # def bake_2(x, env):
 #     if isinstance(x, Tree):
 #         L, H, R = bake_2(x.L, env), bake_2(x.H, env), bake_2(x.R, env)
 #         x = Tree(H.tt, L, H, R)
 #         # if TT.THUNK not in (L.tt, H.tt, R.tt):
 #         #     x = Eval(x, env)
 #     elif isinstance(x, Leaf) and x.tt == TT.THUNK:
 #         x = unwrap(x)
 #         # if x.tt != TT.THUNK:
 #         #     x = Eval(x, env)
 #     return x

# def unthunk(x, env):
#     if x.tt == TT.THUNK:
#         return x.w
#     elif x.tt == TT.FUNCTION:
#         return x
#     return Eval(x, nv)


def bake(a, b, env):
     assert a.tt == TT.FUNCTION
     assert b.tt in (TT.SYMBOL, TT.STRING)
     return Leaf(a.tt, bake_(unwrap(a), b.w, env))


def bake_(x, var, env):
    if isinstance(x, Tree):
        if isinstance(x.H, Leaf) and x.H.w == "$" and x.R.w == var:
            return env.lookup(var, x.L)
        return Tree(bake_(x.L, var, env), bake_(x.H, var, env), bake_(x.R, var, env))
    elif x.tt == TT.THUNK:
        return Leaf(x.tt, bake_(unwrap(x), var, env))
    return x




def invoke(a, b, env):
    return Tree(a, b, Void)


def if_(a, b, env):
    assert a.tt == TT.PUNCTUATION and isinstance(a, Tree)
    conseq = a.R if b.w == 0 else a.L
    if conseq.tt in (TT.FUNCTION, TT.THUNK):
        conseq = conseq.w
    return conseq


le = lambda a, b, env: Leaf(TT.NUM, 1 if a.w < b.w else 0)
ge = lambda a, b, env: Leaf(TT.NUM, 1 if a.w > b.w else 0)


def app(a, b, env):
    if a.tt == "vec":
        return Leaf("vec", a.w + [b.w])
    return Leaf("vec", [a.w, b.w])


def print_fn(a, _, env):
    print(a)
    return a


def wait(a, b, env):
    assert b.tt == TT.NUM and b.w >= 0
    time.sleep(b.w)
    return a


def set_dispatch(a, b, env):
    fn_name = b.L.w
    if isinstance(b.R, Tree):
        left_tt, right_tt = b.R.L.w, b.R.R.w
        dispatch_str = f"{fn_name}{DISPATCH_SEP}{left_tt}{DISPATCH_SEP}{right_tt}"
    else:
        left_tt = b.R.w
        dispatch_str = f"{fn_name}{DISPATCH_SEP}{left_tt}"

    env.bind(dispatch_str, a)
    return a


BUILTINS = {
    "+": lambda a, b, env: Leaf(TT.NUM, a.w + b.w),
    "-": lambda a, b, env: Leaf(TT.NUM, a.w - b.w),
    "*": lambda a, b, env: Leaf(TT.NUM, a.w * b.w),
    "/": lambda a, b, env: Leaf(TT.NUM, a.w // b.w),
    "=": lambda a, b, env: Leaf(TT.NUM, 1 if a.w == b.w else 0),
    "dec": lambda a, b, env: env.assign(a.w, Leaf(TT.NUM, env.lookup(a.w, Leaf(TT.NUM, 1)).w - b.w)),
    "inc": lambda a, b, env: env.assign(a.w, Leaf(TT.NUM, env.lookup(a.w, Leaf(TT.NUM, 0)).w + b.w)),
    "T": get_type,
    "sametype": lambda a, b, env: Leaf(TT.NUM, 1 if a.tt == b.tt else 0),
    "dispatch": set_dispatch,
    "<": le,
    ">": ge,
    "le": le,
    "ge": ge,
    "lt": lambda a, b, env: Leaf(TT.NUM, 1 if a.w <= b.w else 0),
    "gt": lambda a, b, env: Leaf(TT.NUM, 1 if a.w >= b.w else 0),
    "$": lambda a, b, env: env.lookup(b.w, a),
    "to": lambda a, b, env: Leaf("vec", list(range(a.w, b.w))),
    "as": lambda a, b, env: env.bind(b.w, a),
    "assign": lambda a, b, env: env.assign(b.w, a),
    "is": lambda a, b, env: env.assign(a.w, b),
    "if": if_,
    "then": lambda a, b, env: if_(b, a, env),
    "not": lambda a, b, env: Leaf(TT.NUM, 1 - a.w),
    "?": lambda a, b, env: if_(b, a, env),
    "|": lambda a, b, env: b,
    "bake": bake,
    "L": lambda a, _, env: a.L,
    "H": lambda a, _, env: a.H,
    "R": lambda a, _, env: a.R,
    "open": lambda a, _, env: unwrap(a),
    "unwrap": lambda a, _, env: unwrap(a),
    ",": app,
    "vec": lambda a, _, env: Leaf("vec", []),
    # "callcc": callcc,
    "print": print_fn,
    "wait": wait,
    "!": invoke,
}


SPECIAL = {
    "cpush": reset,
    "cpop": shift,
}


class Env:

    def __init__(self, parent, from_dict=None):
        self.parent = parent
        self.e = {**(from_dict or {})}

    def lookup(self, name, or_else):
        env = self.find_env(name)
        if not env:
            return or_else
        return env.e[name]

    def find_env(self, name):
        # TODO optimize self-recursion in tail calls by reusing env
        if name in self.e:
            return self
        elif self.parent is not None:
            return self.parent.find_env(name)
        return None

    def bind(self, name, value):
        self.e[name] = value
        return value

    def assign(self, name, value):
        env = self.find_env(name) or self
        env.bind(name, value)
        return value

    def __repr__(self):
        return repr(self.e)


def next_ins(x):
    if isinstance(x, Leaf):
        return CT.Leaf
    elif isinstance(x, Tree):
        return CT.Tree
    assert False


def Eval(x, env):
    # Stack of continuations
    cstack = Cactus()
    cstack.push(Frame(CT.Return, None, None, None, env))
    # Stored instruction pointer
    ins = next_ins(x)

    while True:
        if ins >= CT.Tree:
            if ins == CT.Tree:
                L, H, R = x.L, x.H, x.R
            if ins < CT.Left and isinstance(L, Tree):
                cstack.push(Frame(CT.Left, L, H, R, env))
                x, ins = L, next_ins(L)
                continue
            if ins < CT.Head and isinstance(H, Tree):
                cstack.push(Frame(CT.Head, L, H, R, env))
                x, ins = H, next_ins(H)
                continue
            if H.tt == TT.SEPARATOR:
                # Tail recurse on separator '|' before R gets evaluated
                x, ins = R, next_ins(R)
                continue
            if ins < CT.Right and isinstance(R, Tree):
                cstack.push(Frame(CT.Right, L, H, R, env))
                x, ins = R, next_ins(R)
                continue

            # print("EVAL", x, file=sys.stderr)
            # print("L", L, file=sys.stderr)
            # print("R", R, file=sys.stderr)

            # TODO reorder by frequency of invocation. BUILTIN to top?
            if H.tt == TT.VOID:
                x = H
            elif H.tt == TT.CONTINUATION:
                cc, env = H.w
                # TODO add another delim?? MinCaml does
                # cstack.push(Frame(CT.Delim, L, H, R, env))
                cstack.scopy(cc)
                x, ins = L, next_ins(L)
            elif H.tt == TT.PUNCTUATION and H.w in ".:`":
                x = Tree(L, H, R)
            elif H.tt == TT.BUILTIN:
                x = H.w(L, R, env)
                ins = next_ins(x)
                continue
            elif H.tt == TT.SPECIAL:
                x, cstack, env = H.w(L, R, cstack, env)
                ins = next_ins(x)
                continue
            elif H.tt == TT.THUNK:
                x = unwrap(H)
                ins = next_ins(x)
                continue
            elif H.tt == TT.FUNCTION:
                # Tail optimize cstack and env if the last frame would
                # be effectively the same as the new one
                self_h = env.lookup("self", None)
                last_frame = cstack.peek()
                if (last_frame and last_frame.ct != CT.Function) \
                    or self_h is not H:
                    cstack.push(Frame(CT.Function, L, H, R, env))
                    env = Env(env)
                # print("ENV", id(env))

                env.bind("x", L)
                env.bind("self", H)
                env.bind("y", R)
                x = unwrap(H)
                ins = next_ins(x)
                continue
            elif H.tt in (TT.PUNCTUATION, TT.SYMBOL, TT.SEPARATOR):
                if R.tt in (TT.PUNCTUATION, TT.SYMBOL, TT.NUM):
                    # Dispatch on L.type and R.value
                    dispatch_str = f"{H.w}:{L.tt}:{R.w}"
                    op = env.lookup(dispatch_str, None)
                if op is None:
                    # Dispatch on L.type and R.type
                    dispatch_str = f"{H.w}:{L.tt}:{R.tt}"
                    op = env.lookup(dispatch_str, None)
                if op is None:
                    # Dispatch on L.type and Fn name
                    dispatch_str = f"{H.w}:{L.tt}"
                    op = env.lookup(dispatch_str, None)
                if op is None:
                    op = env.lookup(H.w, None)
                if op is None:
                    raise NoDispatch(f"Can't dispatch {H.w} on L: {L.tt}")
                assert op.tt in (TT.CONTINUATION, TT.SPECIAL,
                                 TT.FUNCTION, TT.CLOSURE,
                                 TT.BUILTIN, TT.THUNK)
                H = op
                ins = CT.Right
                continue
            elif H.tt == TT.CLOSURE:
                cstack.push(Frame(CT.Function, L, H, R, env))
                env, H = H.w
                ins = CT.Right
                continue
            else:
                raise CantReduce(f"Can't reduce node: {H} of {H.tt}")

        # Capture current environment and close over it
        if isinstance(x, Leaf) and x.tt == TT.FUNCTION:
            x = Leaf(TT.CLOSURE, (env, x))

        # Restore stack frame and apply continuation
        c = cstack.pop()
        ins = c.ct
        if ins == CT.Return:
            return x

        L, H, R, env = c.L, c.H, c.R, c.env
        # print("Restore", L, H, R, c.ct.name, id(env), env)
        if c.ct == CT.Function:
            ins = next_ins(x)
        elif c.ct == CT.Left:
            L = x
        elif c.ct == CT.Head:
            H = x
        elif c.ct == CT.Right:
            R = x
        else:
            assert False


def left(a, b, env):
    return a


def right(a, b, env):
    return b


def fold(a, b, env):
    if isinstance(b, Tree):
        zero = b.R.w
        op = b.L.w
    else:
        op = b.w
        zero = {
            "+": 0,
            "-": 0,
            "*": 1,
            "/": 1,
        }[op]

    op = {
        "+": lambda a, b: a + b,
        "-": lambda a, b: a - b,
        "*": lambda a, b: a * b,
        "/": lambda a, b: a // b,
    }[op]

    acc = zero
    for x in a.w:
        acc = op(acc, x)
    return Leaf(TT.NUM, acc)


def scan(a, b, env):
    if isinstance(b, Tree):
        zero = b.R.w
        op = b.L.w
    else:
        op = b.w
        zero = {
            "+": 0,
            "-": 0,
            "*": 1,
            "/": 1,
        }[op]

    op = {
        "+": lambda a, b: a + b,
        "-": lambda a, b: a - b,
        "*": lambda a, b: a * b,
        "/": lambda a, b: a // b,
    }[op]

    acc = zero
    r = []
    for x in a.w:
        acc = op(acc, x)
        r += [acc]
    return Leaf("vec", r)


dispatch = {
    ("+", "vec"): lambda a, b, env: Leaf("vec", [x + y for x, y in zip(a.w, b.w)]),
    ("-", "vec"): lambda a, b, env: Leaf("vec", [x - y for x, y in zip(a.w, b.w)]),
    ("*", "vec"): lambda a, b, env: Leaf("vec", [x * y for x, y in zip(a.w, b.w)]),
    ("/", "vec"): lambda a, b, env: Leaf("vec", [x // y for x, y in zip(a.w, b.w)]),
    ("+", "vec", TT.NUM): lambda a, b, env: Leaf("vec", [x + b.w for x in a.w]),
    ("-", "vec", TT.NUM): lambda a, b, env: Leaf("vec", [x - b.w for x in a.w]),
    ("*", "vec", TT.NUM): lambda a, b, env: Leaf("vec", [x * b.w for x in a.w]),
    ("/", "vec", TT.NUM): lambda a, b, env: Leaf("vec", [x // b.w for x in a.w]),
    ("@", "vec", TT.NUM): lambda a, b, env: Leaf(TT.NUM, a.w[b.w]),
    ("fold", "vec"): fold,
    ("scan", "vec"): scan,
    ("+", "vec", "0"): left,
    ("-", "vec", "0"): left,
    ("*", "vec", "1"): left,
    ("/", "vec", "1"): left,
}


def Repl(prompt="> "):
    builtins = {k: Leaf(TT.BUILTIN, x) for k, x in BUILTINS.items()}
    special = {k: Leaf(TT.SPECIAL, x) for k, x in SPECIAL.items()}
    dispatches = {DISPATCH_SEP.join(map(str, k)): Leaf(TT.BUILTIN, v) for k, v in dispatch.items()}

    env = Env(None, from_dict={
        **special,
        **builtins,
        **dispatches,
    })
    env = Env(env)  # dummy env

    while True:
        try:
            x = input(prompt)
            x = Lex(x)
            # print("LEX", y)
            x = Parse(x)
            # print("PARSE", y)
            x = Eval(x, env)
            if x is not None:
                print(x)
        except ParseError as err:
            print(f"Parse error: {err}", file=sys.stderr)
        except (NoDispatch, CantReduce, TypeError) as err:
            print(err, file=sys.stderr)
        except (EOFError, KeyboardInterrupt):
            break


if __name__ == "__main__":
    readline.parse_and_bind('tab: complete')
    readline.parse_and_bind('set editing-mode vi')
    Repl()
