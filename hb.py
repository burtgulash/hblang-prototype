#!/usr/bin/env python3

import sys
import time

from c import Lex, Parse, \
              ParseError, TT, Tree, Leaf, Void

from stack import Cactus, CT, Frame


SELF_F = "f"
DISPATCH_SEP = ":"

class NoDispatch(Exception):
    pass


class CantReduce(Exception):
    pass


class Env:

    def __init__(self, parent, from_dict=None):
        # self.parent = parent
        self.e = {**(from_dict or {})}
        self.e[":"] = parent

    def lookup(self, name, or_else):
        env = self.find_env(name)
        if not env:
            return or_else
        return env.e[name]

    def find_env(self, name):
        # TODO optimize self-recursion in tail calls by reusing env
        if name in self.e:
            return self
        else:
            parent = self.e.get(":")
            if parent:
                return parent.find_env(name)
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




def load(a, b, env):
    with open(b.w) as f:
        code = f.read()

    new_env = Env(env)
    x, new_env = Execute(code, new_env)
    return Leaf(TT.OBJECT, new_env)


def reset(a, b, env, cstack):
    cstack.spush()
    if isinstance(b, Leaf) and b.tt == TT.THUNK:
        b = b.w
    return b, env, cstack


def shift(a, b, env, cstack):
    cc = cstack.spop()
    # Don't let the continuation binding propagate to parent environment
    env = Env(env)
    # So far continuation is just a pair of st and env
    continuation = Leaf(TT.CONTINUATION, (cc, env))
    env.bind("cc", continuation)
    if isinstance(b, Leaf) and b.tt == TT.THUNK:
        b = b.w
    return b, env, cstack


def setenv(H, env):
    self_f = env.lookup(SELF_F, None)
    if self_f is H:
        return env
    return Env(env)


def get_type(a, b, env):
    if isinstance(a, Tree):
        return Leaf(TT.SYMBOL, TT.TREE)
    return Leaf(TT.SYMBOL, a.tt.name)


def unwrap(H):
    if H.tt == TT.CLOSURE:
        return H.w[1]
    if H.tt in (TT.FUNCTION, TT.THUNK):
        return H.w
    return H


def bake_vars(a, _, env):
    assert a.tt in (TT.FUNCTION, TT.THUNK, TT.CLOSURE)
    return Leaf(a.tt, bake_vars_(unwrap(a)))


def is_function(x):
    return x.tt in (TT.FUNCTION, TT.THUNK, TT.CLOSURE)


def bake_vars_(x):
    if isinstance(x, Tree):
        L, R = bake_vars_(x.L), bake_vars_(x.R)
        H = x.H
        if isinstance(H, Tree) or is_function(H):
            H = bake_vars_(H)
        x = Tree(L, H, R)
    elif is_function(x):
        x = Leaf(x.tt, bake_vars_(unwrap(x)))
    elif x.tt == TT.SYMBOL:
        x = Tree(Leaf(TT.CONS, "."), Leaf(TT.PUNCTUATION, "$"), x)
    return x


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
    assert isinstance(a, Tree)
    conseq = a.R if b.w == 0 else a.L
    return unwrap(conseq)


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


def new_object(a, b, env):
    return Leaf(TT.OBJECT, Env(None))


def at(a, b, env):
    env_name = a.w
    if env_name == ".":
        e = env
    elif env_name == ":":
        e = env.lookup(":", None) # TODO check if some focka didn't delete it
    else:
        e = env.lookup(env_name, None)
        assert e.tt == TT.OBJECT
        e = e.w # unwrap object to env

    # print(e.e)
    if isinstance(b, Tree):
        slot_name = b.L.w
        item = b.R
        e.bind(slot_name, item)
    else:
        slot_name = b.w
        item = e.lookup(slot_name, None)
        assert isinstance(item, Leaf) or isinstance(item, Tree)

    return item


BUILTINS = {
    "+": lambda a, b, env: Leaf(TT.NUM, a.w + b.w),
    "-": lambda a, b, env: Leaf(TT.NUM, a.w - b.w),
    "*": lambda a, b, env: Leaf(TT.NUM, a.w * b.w),
    "/": lambda a, b, env: Leaf(TT.NUM, a.w // b.w),
    "mod": lambda a, b, env: Leaf(TT.NUM, a.w % b.w),
    "=": lambda a, b, env: Leaf(TT.NUM, 1 if a.w == b.w else 0),
    "dec": lambda a, b, env: env.assign(a.w, Leaf(TT.NUM, env.lookup(a.w, Leaf(TT.NUM, 1)).w - b.w)),
    "inc": lambda a, b, env: env.assign(a.w, Leaf(TT.NUM, env.lookup(a.w, Leaf(TT.NUM, 0)).w + b.w)),
    "T": get_type,
    "type": get_type,
    "sametype": lambda a, b, env: Leaf(TT.NUM, 1 if a.tt == b.tt else 0),
    "dispatch": set_dispatch,
    "<": lambda a, b, env: Leaf(TT.NUM, 1 if a.w < b.w else 0),
    "<=": lambda a, b, env: Leaf(TT.NUM, 1 if a.w <= b.w else 0),
    ">": lambda a, b, env: Leaf(TT.NUM, 1 if a.w > b.w else 0),
    ">=": lambda a, b, env: Leaf(TT.NUM, 1 if a.w >= b.w else 0),
    "@": at,
    "$": lambda a, b, env: env.lookup(b.w, a),
    "to": lambda a, b, env: Leaf("vec", list(range(a.w, b.w))),
    "as": lambda a, b, env: env.bind(b.w, a),
    "->": lambda a, b, env: env.bind(b.w, a),
    "assign": lambda a, b, env: env.assign(b.w, a),
    "is": lambda a, b, env: env.assign(a.w, b),
    "<-": lambda a, b, env: env.assign(a.w, b),
    "if": lambda a, b, env: unwrap(a.L),
    # "then": lambda a, b, env: if_(b, a, env),
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
    "print": print_fn,
    "wait": wait,
    "!": invoke,
    "load": load,
    "O": new_object(Void, Void, None),
    "object": new_object(Void, Void, None),
    "bakevars": bake_vars,
}


SPECIAL = {
    "cpush": reset,
    "cpop": shift,
}


def tt2env(tt, env):
    ttstr = str(tt)
    path = ttstr.split(DISPATCH_SEP)[:-1] # exclude actual object tt
    return path2env(path, env)


def tree2env(x, env):
    path = []
    while isinstance(x.R, Tree):
        path.append(x.L.w)
        x = x.R
    path.append(x.L.w,)
    return path, x.R.w


def path2env(path, env):
    for p in path:
        env = env.lookup(p, None)
        assert env.tt == TT.OBJECT
        env = env.w
    assert env is not None
    return env



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
            elif H.tt == TT.CONS and H.w in ".:":
                x = Tree(L, H, R)
            elif H.tt == TT.BUILTIN:
                x = H.w(L, R, env)
                ins = next_ins(x)
                continue
            elif H.tt == TT.SPECIAL:
                x, env, cstack = H.w(L, R, env, cstack)
                ins = next_ins(x)
                continue
            elif H.tt == TT.THUNK:
                x = unwrap(H)
                ins = next_ins(x)
                continue
            elif H.tt == TT.FUNCTION:
                # Tail optimize cstack and env if the last frame would
                # be effectively the same as the new one
                self_h = env.lookup(SELF_F, None)
                last_frame = cstack.peek()
                if (last_frame and last_frame.ct != CT.Function) \
                    or self_h is not H:
                    cstack.push(Frame(CT.Function, L, H, R, env))
                    env = Env(env)
                # print(TT.OBJECT, id(env))

                env.bind("x", L)
                env.bind(SELF_F, H)
                env.bind("y", R)
                x = unwrap(H)
                ins = next_ins(x)
                continue
            elif H.tt == TT.TREE:
                path, fn = tree2env(H, env)
                fn_env = path2env(path, env)
                op = fn_env.lookup(fn, None)
                if op is None:
                    raise NoDispatch(f"Can't find module function {H} on L: {L.tt}")
                assert op.tt in (TT.CONTINUATION, TT.SPECIAL,
                                 TT.FUNCTION, TT.CLOSURE,
                                 TT.BUILTIN, TT.THUNK)
                H = op
                ins = CT.Right
                continue
            elif H.tt in (TT.PUNCTUATION, TT.CONS, TT.SYMBOL,
                          TT.STRING, TT.SEPARATOR):
                fn = H.w
                op = None

                # separator as fallback if no TCO? TODO remove it
                # Dispatch on left symbol (like a method)
                dispatch_env = env.lookup(L.tt, None)
                if dispatch_env and dispatch_env.tt == TT.OBJECT:
                    dispatch_env = dispatch_env.w
                else:
                    dispatch_env = env

                # TODO don't dispatch on value
                # if R.tt in (TT.PUNCTUATION, TT.CONS, TT.SYMBOL,
                #             TT.STRING, TT.NUM):
                #     # dispatch on l.type and r.value
                #     dispatch_str = f"{fn}:{R.w}"
                #     op = dispatch_env.lookup(dispatch_str, None)
                if op is None:
                    # Dispatch on L.type and R.type
                    dispatch_str = f"{fn}:{R.tt}"
                    op = dispatch_env.lookup(dispatch_str, None)
                if op is None:
                    # Dispatch on L.type and Fn name
                    dispatch_str = f"{fn}"
                    op = dispatch_env.lookup(dispatch_str, None)
                if op is None:
                    op = env.lookup(fn, None)
                if op is None:
                    raise NoDispatch(f"Can't dispatch {fn} on L: {L.tt}")
                assert op.tt in (TT.CONTINUATION, TT.SPECIAL,
                                 TT.FUNCTION, TT.CLOSURE,
                                 TT.BUILTIN, TT.THUNK, TT.SYMBOL)
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
            return x, env

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


modules = {
    "vec": {
        "+": lambda a, b, env: Leaf("vec", [x + y for x, y in zip(a.w, b.w)]),
        "-": lambda a, b, env: Leaf("vec", [x - y for x, y in zip(a.w, b.w)]),
        "*": lambda a, b, env: Leaf("vec", [x * y for x, y in zip(a.w, b.w)]),
        "/": lambda a, b, env: Leaf("vec", [x // y for x, y in zip(a.w, b.w)]),
        ("+", TT.NUM): lambda a, b, env: Leaf("vec", [x + b.w for x in a.w]),
        ("-", TT.NUM): lambda a, b, env: Leaf("vec", [x - b.w for x in a.w]),
        ("*", TT.NUM): lambda a, b, env: Leaf("vec", [x * b.w for x in a.w]),
        ("/", TT.NUM): lambda a, b, env: Leaf("vec", [x // b.w for x in a.w]),
        ("@", TT.NUM): lambda a, b, env: Leaf(TT.NUM, a.w[b.w]),
        "fold": fold,
        "scan": scan,
        ("+", "0"): left,
        ("-", "0"): left,
        ("*", "1"): left,
        ("/", "1"): left,
    },
    TT.TREE: {
        "if": if_,
    },
    TT.OBJECT: {
        "clone": lambda a, b, env: Leaf(TT.OBJECT, a.w),
        ("@", TT.TREE): lambda a, b, env: env.bind(b.L.w, b.R) # TODO implement assignment
    }
}

def as_module(mod_dict):
    d = {}
    for k, v in mod_dict.items():
        if not isinstance(k, str):
            k = DISPATCH_SEP.join(map(str, k))
        d[k] = Leaf(TT.BUILTIN, v)
    return d


def Execute(code, env):
    try:
        x = code
        x = Lex(x)
        # print("LEX", y)
        x = Parse(x)
        # print("PARSE", y)
        x, env = Eval(x, env)
        return x, env
    except ParseError as err:
        print(f"Parse error: {err}", file=sys.stderr)
    except (NoDispatch, CantReduce, TypeError) as err:
        print(err, file=sys.stderr)

    return None, None


def prepare_env():
    builtins = {k: Leaf(TT.BUILTIN, x) for k, x in BUILTINS.items()}
    special = {k: Leaf(TT.SPECIAL, x) for k, x in SPECIAL.items()}
    # dispatches = {DISPATCH_SEP.join(map(str, k)): Leaf(TT.BUILTIN, v) for k, v in dispatch.items()}
    mods = {k: Leaf(TT.OBJECT, Env(None, from_dict=as_module(mod))) for k, mod in modules.items()}

    env = Env(None, from_dict={
        **mods,
        **builtins,
        **special,
    })
    # env = Env(env)  # dummy env
    return env


def Repl(env, prompt="> "):
    import readline
    readline.parse_and_bind('tab: complete')
    readline.parse_and_bind('set editing-mode vi')

    while True:
        try:
            x = input(prompt)
            x, _ = Execute(x, env)
            print(x)
        except (EOFError, KeyboardInterrupt):
            break


def run(argv):
    env = prepare_env()
    if cmd == "repl":
        Repl(env)
    elif cmd == "run":
        if len(argv) < 3:
            src = sys.stdin.read()
        else:
            f = argv[2]
            if f == "-":
                src = sys.stdin.read()
            else:
                with open(f) as inp:
                    src = ff.read()
        x, env = Execute(src, env)
        print(x)


if __name__ == "__main__":
    env = prepare_env()

    if len(sys.argv) == 1:
        try:
            Repl(env)
        except KeyboardInterrupt:
            pass
    elif len(sys.argv) >= 2:
        cmd = sys.argv[1]
        if cmd == "run":
            if len(sys.argv) >= 3:
                with open(sys.argv[2]) as f:
                    src = f.read()
            else:
                src = sys.stdin.read()

            x, env = Execute(src, env)
            print(x)
        else:
            print("Missing command (run)", file=sys.stderr)
            sys.exit(1)
