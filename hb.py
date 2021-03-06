#!/usr/bin/env python3

import sys
import time

from c import Lex, Parse, TT, Tree, Leaf, Unit, \
    WitnessedError, ParseError, DebugInfo

from stack import Cactus, CT, Frame
import matrix


ROOT_TAG = "__root__"
SELF_F = "F"
DISPATCH_SEP = ":"


class UnexpectedType(Exception): pass
class CantReduce(WitnessedError): pass
class NoDispatch(WitnessedError): pass


class Shift:
    """ Instance of some continuation travelling the stack.  Eg. raised error.
    Used when a native function wants to throw an error or raise some other
    kind of continuation.
    """

    def __init__(self, tag, value):
        self.tag = tag
        self.value = value


class Env:

    def __init__(self, parent, from_dict=None):
        # self.parent = parent
        self.e = {**(from_dict or {})}
        self.parent = parent
        # self.e[":"] = parent

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
            # parent = self.e.get(":")
            parent = self.parent
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


class Function:

    def __init__(self, left_name, right_name, body, env):
        self.left_name = left_name
        self.right_name = right_name
        self.body = body
        self.env = env

    def clone(self, body):
        return Function(self.left_name, self.right_name, body, self.env)

    def __str__(self):
        return "{" + f"{self.left_name, self.right_name} -> {self.body}" + "}"

    @property
    def tt(self):
        # TODO ins accepts only Leafs and Trees, not Functions. Remove this?
        return TT.FUNCTION

def bakevar(a, b):
    if b.tt not in (TT.STRING, TT.SYMBOL):
        raise TypecheckError(f"bakevar: Expected string | symbol. Got '{b.tt}'")
    return bakevars(a, [b.w])


def bakevars(x, vars):
    if isinstance(x, Tree):
        L, H, R = bakevars(x.L, vars), bakevars(x.H, vars), bakevars(x.R, vars)
        x = Tree(L, H, R)
    elif x.tt in (TT.THUNK, TT.FUNTHUNK):
        x = Leaf(x.tt, bakevars(unwrap(x), vars))
    elif x.tt == TT.FUNCTION:
        body = bakevars(x.w.body, vars)
        x = Leaf(x.tt, x.w.clone(body))
    elif x.tt == TT.SYMBOL and x.w in vars:
        # NOTE: only bake on symbol, not on string. Otherwise you couldn't do assignments
        x = Tree(Leaf(TT.SYMBOL, ".", debug=x.debug), Leaf(TT.PUNCTUATION, "$"), x)
    return x


def makefunc(a, b, env, cstack):
    return makefunc_(a, env), None, env, cstack


def iscons(x):
    return x.tt == TT.PUNCTUATION and x.w in (".", ":")


def makefunc_(a, env):
    if a.tt not in (TT.THUNK, TT.FUNTHUNK):
        raise Exception(f"Can't create function out of '{a.tt}'")

    body = a.w

    left_name, right_name = "x", "y"
    if body.tt == TT.TREE and body.H.tt == TT.SEPARATOR:
        header, body = body.L, body.R
        if header.tt == TT.SYMBOL:
            left_name, right_name = header.w, "_"
        elif header.tt == TT.TREE and iscons(header.H):
            left_name, right_name = header.L, header.R
            if not (left_name.tt == right_name.tt == TT.SYMBOL):
                raise TypecheckError(f"Function parameter names need to by symbols."
                                     f" Given '{left_name.tt}' : '{right_name.tt}'")
            left_name, right_name = left_name.w, right_name.w
        else:
            header, body = None, a.w
            #raise TypecheckError(f"Fn header expected cons TREE | SYMBOL. Got {header.tt}")

    body = bakevars(body, [left_name, right_name])
    return Leaf(TT.FUNCTION, Function(left_name, right_name, body, env), debug=body.debug)


def load(a, b, env, cstack):
    with open(b.w) as f:
        code = f.read()
    # print(f"CODE: '{code}'", file=sys.stderr)

    _, _, module, _ = Execute(code, Env(env), cstack)
    if module is None:
        raise TypecheckError("Module can't be NULL")
    return Leaf(TT.OBJECT, module), None, env, cstack


def import_(a, b, env, cstack):
    with open(b.w) as f:
        code = f.read()
    # print(f"CODE: '{code}'", file=sys.stderr)

    _, _, module, _ = Execute(code, env, cstack)
    if module is None:
        raise TypecheckError("Module can't be NULL")
    return Unit, None, env, cstack


def execute(a, b, env, cstack):
    assert a.tt in (TT.SYMBOL, TT.STRING)
    code = a.w
    return Execute_(code, env, cstack)


def reset(a, b, env, cstack):
    assert a.tt in (TT.SYMBOL, TT.STRING) # TODO keep only symbol as continuation tags?
    tag = a.w
    cstack.spush(tag)
    if isinstance(b, Leaf) and b.tt in (TT.THUNK, TT.FUNTHUNK):
        b = b.w
    return b, None, env, cstack


def shift(a, b, env, cstack):
    assert a.tt in (TT.SYMBOL, TT.STRING) # TODO keep only symbol as continuation tags?
    tag = a.w
    try:
        cc = cstack.spop(tag)
    except Cactus.Empty:
        raise

    # # Don't let the continuation binding propagate to parent environment
    # env = Env(env)
    # So far continuation is just a pair of st and env
    continuation = Leaf(TT.CONTINUATION, (cc, env))
    #env.bind("cc", continuation)

    # New: let the cc binding take place in function object
    if isinstance(b, Leaf) and b.tt in (TT.THUNK, TT.FUNTHUNK, TT.FUNCTION):
        b = Tree(continuation, b, Unit)
    return b, None, env, cstack


def setenv(H, env):
    self_f = env.lookup(SELF_F, None)
    if self_f is H:
        return env
    return Env(env)


def get_type(a, b):
    if isinstance(a, Tree):
        return Leaf(TT.SYMBOL, TT.TREE)
    return Leaf(TT.SYMBOL, a.tt)


def unwrap(H):
    if H.tt == TT.FUNCTION:
        return H.w.body
    if H.tt in (TT.THUNK, TT.FUNTHUNK):
        return H.w
    return H


def is_function(x):
    return x.tt in (TT.FUNCTION, TT.THUNK, TT.FUNTHUNK)


def if_(a, b):
    assert isinstance(a, Tree)
    conseq = a.R if b.w == 0 else a.L
    return unwrap(conseq)


def app(a, b):
    if a.tt == "vec":
        return Leaf("vec", a.w + [b.w])
    return Leaf("vec", [a.w, b.w])


def print_fn(a, _):
    print(a)
    return a


def wait(a, b):
    assert b.tt == TT.NUM and b.w >= 0
    time.sleep(b.w)
    return a


def set_dispatch(a, b, env):
    fn_name = b.L.w
    if isinstance(b.R, Tree):
        left_tt, right_tt = b.R.L.w, b.R.R.w
        dispatch_str = f"{fn_name}{DISPATCH_SEP}{right_tt}"
    else:
        left_tt = b.R.w
        dispatch_str = f"{fn_name}"

    module = env.lookup(left_tt, None)
    if not module:
        # TODO create new module
        raise Exception("Accompanying module of type '{left_tt}' doesn't exist")
    if module.tt != TT.OBJECT:
        raise Exception("Accompanying object is not a module, but {module.tt}")

    module.w.bind(dispatch_str, a)
    return a


def new_object(a, b):
    return Leaf(TT.OBJECT, Env(None))


def at(a, b, env, cstack):
    if isinstance(a, Tree):
        raise TypecheckError("at: Expected leaf, not tree")

    env_name = a.w
    if env_name == ".":
        e = env
    elif env_name == ":":
        # e = env.lookup(":", None) # TODO check if some focka didn't delete it
        e = env.parent
    else:
        e = env.lookup(env_name, None)
        if e is None or e.tt != TT.OBJECT:
            raise TypecheckError(f"Expected OBJECT, got '{type(e).__name__}'")
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

    return item, None, env, cstack


class TypecheckError(Exception):
    pass


def nominal_typecheck(checked_type, expected_type):
    if str(checked_type) != str(expected_type):
        raise TypecheckError(f"Typecheck failed. '{checked_type}' doesn't match expected '{expected_type}'")

def not_typecheck(a, b):
    if b.tt == TT.SYMBOL:
        if str(a.tt) == str(b.w):
            raise TypecheckError(f"Typecheck failed. '{a.tt}' musn't match forbidden '{b.w}'")
    return a

def typecheck(a, b):
    if b.tt == TT.SYMBOL:
        nominal_typecheck(a.tt, b.w)
    elif b.tt == TT.TREE:
        expected_type = b.L.w
        nominal_typecheck(a.tt, expected_type)
        # check_fn = env.lookup(expected_type, Env(None)).lookup("typecheck", None)
        # TODO implement this in code
    else:
        raise Exception(f"Type check needs to be on a symbol or a tree. Got '{b.tt}'")
    return a


def construct(a, b):
    return Tree(a, b, Unit)


def eq(a, b):
    result = 1 if a.tt == b.tt and a.w == b.w else 0
    return Leaf(TT.NUM, result)


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
        if not env or env.tt != TT.OBJECT:
            raise TypecheckError(f"Path2env expected OBJECT got {type(env) or env.tt}")
        env = env.w
    assert env is not None
    return env



def next_ins(x):
    if isinstance(x, Leaf):
        return CT.Leaf
    elif isinstance(x, Tree):
        return CT.Tree
    raise AssertionError(f"Result needs to be either Leaf or Tree. Got '{type(x)}'")


def hb_shift(tag, value):
    tag = Leaf(TT.SYMBOL, tag, debug=value.debug)
    return Tree(tag, Leaf(TT.SYMBOL, "shift"), value)


def Eval(x, env, cstack):
    # Stack of continuations
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
            # print("H", type(H), H)
            if H.tt == TT.SEPARATOR:
                # Tail recurse on separator '|' before R gets evaluated
                x, ins = R, next_ins(R)
                continue
            if ins < CT.Right and isinstance(R, Tree):
                cstack.push(Frame(CT.Right, L, H, R, env))
                x, ins = R, next_ins(R)
                continue

#            print("EVAL", x, file=sys.stderr)
#            print("L", L, file=sys.stderr)
#            print("R", R, R.debug, file=sys.stderr)


            new_debug = DebugInfo(L.debug.start, R.debug.end, L.debug.lineno) \
                        if L.debug and R.debug else None
            #new_debug = DebugInfo(L.debug.start, R.debug.end, L.debug.lineno)

            # TODO reorder by frequency of invocation. BUILTIN to top?
            if H.tt == TT.UNIT:
                x = H
                x.debug = new_debug
            elif H.tt == TT.CONTINUATION:
                cc, env = H.w     # unwrap continuation and captured environment
                cstack.scopy(cc)  # Copy over its stack onto newly created stack
                x, ins = L, next_ins(L)
                x.debug = new_debug
            elif iscons(H):
                x = Tree(L, H, R)
                x.debug = new_debug
            elif H.tt == TT.BUILTIN:
                try:
                    x = H.w(L, R)
                except Exception as exc:
                    # NOTE temporary solution. Wrap exception's string into
                    # error and shift it in. Better solution would be to return
                    # (x, err) pair from builtins instead of catching arbitrary
                    # error. In this case, at least create error inheritance
                    # hierarchy
                    if isinstance(exc, AssertionError):
                        raise
                    #print("RROR", type(exc), str(exc), file=sys.stderr)
                    x = hb_shift("error", Leaf(TT.ERROR, str(exc), debug=new_debug))

                ins = next_ins(x)
                x.debug = new_debug
                continue
            elif H.tt == TT.SPECIAL:
                x, shift, env, cstack = H.w(L, R, env, cstack)

                # Capture shift tag and value from shift channel, wrap it with
                # TT.ERROR and continue with this error continuation to next
                # eval iteration
                if shift is not None:
                    assert isinstance(shift, Shift)
                    x = hb_shift(shift.tag, shift.value)

                ins = next_ins(x)
                x.debug = new_debug
                continue
            elif H.tt == TT.FUNTHUNK:
                x = Tree(L, Tree(H, Leaf(TT.SYMBOL, "func"), Unit), R)
                ins = next_ins(x)
                x.debug = H.debug
                continue
            elif H.tt == TT.THUNK:
                x = unwrap(H)
                ins = next_ins(x)
                x.debug = new_debug # TODO really this way? Or just grab debug from H itself?
                continue
            elif H.tt == TT.FUNCTION:
                func = H.w

                # Tail optimize cstack and env if the last frame would
                # be effectively the same as the new one
                self_h = env.lookup(SELF_F, None)
                last_frame = cstack.peek()
                if (last_frame and last_frame.ct != CT.Function) \
                    or self_h is not H:
                    # TODO compare self_h == H or self_h.func == func?
                    cstack.push(Frame(CT.Function, L, H, R, env))

                    # Set up func's original env -> lexical scoping
                    env = func.env
                    env = Env(env)
                # print(TT.OBJECT, id(env))

                env.bind(func.left_name, L)
                env.bind(SELF_F, H)
                env.bind(func.right_name, R)
                x = func.body
                ins = next_ins(x)

                x.debug = new_debug
                continue
            elif H.tt == TT.TREE and iscons(H.H):
                path, fn = tree2env(H, env)
                fn_env = path2env(path, env)
                op = fn_env.lookup(fn, None)
                if op is None:
                    raise NoDispatch(f"Can't find module function {H} on L: {L.tt}", H)
                assert op.tt in (TT.CONTINUATION, TT.SPECIAL,
                                 TT.FUNCTION, TT.BUILTIN, TT.THUNK, TT.FUNTHUNK)
                H = op
                ins = CT.Right
                x.debug = new_debug
                continue
            elif H.tt == TT.OBJECT:
                # If module given for dispatch,
                # lookup a constructor "." function on it.
                # "." reserved for constructors
                # because it can't be overriden in the module
                constructor = H.w.lookup(".", None)
                if not constructor:
                    raise AssertionError("Constructor not found")
                H = constructor
                assert H.tt in (TT.CONTINUATION, TT.SPECIAL,
                                TT.FUNCTION, # TT.CLOSURE,
                                TT.BUILTIN, TT.THUNK, TT.FUNTHUNK, TT.SYMBOL)
                ins = CT.Right
                x.debug = new_debug
                continue
            elif H.tt in (TT.PUNCTUATION, TT.SYMBOL,
                          TT.STRING, TT.SEPARATOR):
                H = dispatch(H, L.tt, R.tt, env)
                ins = CT.Right
                x.debug = new_debug
                continue
            #elif H.tt == TT.CLOSURE:
            #    cstack.push(Frame(CT.Function, L, H, R, env))
            #    env, H = H.w
            #    ins = CT.Right
            #    continue
            else:
                raise CantReduce(f"Can't reduce node: {H} of {H.tt}", H)
#
#         # Capture current environment and close over it
#         if isinstance(x, Leaf) and x.tt == TT.FUNCTION:
#             x = Leaf(TT.CLOSURE, (env, x))

        # Restore stack frame and apply continuation
        c = cstack.pop()
        ins = c.ct
        if ins == CT.Return:
            return x, None, env, cstack # TODO None as error?

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


def dispatch(H, ltt, rtt, env):
    fn = H.w
    # print(f"Dispatching {fn} on {ltt} : {rtt}", file=sys.stderr)

    # separator as fallback if no TCO? TODO remove it
    # Dispatch on left symbol (like a method)
    dispatch_env = env.lookup(ltt, None)
    # print("DENV", L.tt, dispatch_env, file=sys.stderr)
    if dispatch_env and dispatch_env.tt == TT.OBJECT:
        dispatch_env = dispatch_env.w
    else:
        dispatch_env = env

    # print("DISPATCH ON", ltt, fn, rtt, file=sys.stderr)
    # print("DISPTACH ENV", dispatch_env, file=sys.stderr)
    # print("", file=sys.stderr)
    # Dispatch on L.type and R.type

    op = None
    while True:
        if op is None:
            dispatch_str = f"{fn}:{rtt}"
            op = dispatch_env.lookup(dispatch_str, None)
        else: break
        if op is None:
            dispatch_str = f"{fn}"
            op = dispatch_env.lookup(dispatch_str, None)
        else: break
        if op is None:
            op = env.lookup(fn, None)
        else: break
        if op is None:
            raise NoDispatch(f"Can't dispatch {fn} on {ltt}:{rtt}", H)

    # print("LOOKUPED", fn, L.tt, op, type(op), op.tt, file=sys.stderr)
    if op.tt not in (TT.CONTINUATION, TT.SPECIAL,
                     TT.FUNCTION,
                     TT.BUILTIN, TT.THUNK, TT.FUNTHUNK, TT.SYMBOL, TT.PUNCTUATION,
                     TT.OBJECT # dispatch on module/object -> find constructor
    ):
        raise TypeError(f"Dispatched op '{op.tt}' doesn't satisfy function-like types")

    return op


def left(a, b, env):
    return a


def right(a, b, env):
    return b


def fold(a, b, env, cstack):
    if b.tt == TT.TREE:
        f, R = b.L, b.R

        acc = R
        xs = a.w
    else:
        f, R = b, Unit

        if len(a.w) == 0:
            return R
        acc = a.w[0]
        xs = a.w[1:]

    for x in xs:
        acc, _, _, _ = Eval(Tree(acc, f, x), env, cstack)
    return acc, None, env, cstack


# def num_fold(a, b):
#     if isinstance(b, Tree):
#         zero = b.R.w
#         op = b.L.w
#     else:
#         op = b.w
#         zero = {
#             "+": 0,
#             "-": 0,
#             "*": 1,
#             "/": 1,
#         }[op]
#
#     op = {
#         "+": lambda a, b: a + b,
#         "-": lambda a, b: a - b,
#         "*": lambda a, b: a * b,
#         "/": lambda a, b: a // b,
#     }[op]
#
#     acc = zero
#     for x in a.w:
#         acc = op(acc, x)
#     return Leaf(TT.NUM, acc)


def num_fold(a, b):
    op = b.w

    op = {
        "+": lambda a, b: a + b,
        "-": lambda a, b: a - b,
        "*": lambda a, b: a * b,
        "/": lambda a, b: a // b,
    }[op]

    acc = a.w[0]
    for x in a.w[1:]:
        acc = op(acc, x)
    return Leaf(TT.NUM, acc)


def num_fold_by(a, b):
    if b.tt != TT.TREE:
        raise TypecheckError(f"num fold by Expected tree. Got {b.tt}")

    arr = a.w
    key = b.L.w
    op = b.R.w

    op = {
        "+": lambda a, b: a + b,
        "-": lambda a, b: a - b,
        "*": lambda a, b: a * b,
        "/": lambda a, b: a // b,
    }[op]

    acc = [None] * (max(key) + 1)
    for i, y in enumerate(zip(arr, key)):
        x, slot = y
        slot_value = acc[slot]
        if slot_value is None:
            acc[slot] = x
        else:
            acc[slot] = op(slot_value, x)

    return Leaf("num_vec", acc)


def scan(a, b):
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


def each_prep(b):
    if b.tt == TT.TREE:
        f, R = b.L, b.R
    else:
        f, R = b, Unit

    return f, R


def each(a, b, env, cstack):
    f, R = each_prep(b)
    v = [Eval(Tree(x, f, R), env, cstack)[0] for x in a.w]
    return Leaf("vec", v), None, env, cstack


def num_each(a, b, env, cstack):
    f, R = each_prep(b)
    v = [Eval(Tree(Leaf(TT.NUM, x), f, R), env, cstack)[0] for x in a.w]
    return Leaf("vec", v), None, env, cstack


def arithmetic_series_sum(a, b, by):
    n = (b - a) // by + 1
    return (by * n * (n - 1) // 2) + (n * a)


def asmod_vec(a, b, env, cstack):
    d = {}
    for item in a.w:
        assert item.tt == TT.TREE
        assert item.L.tt in (TT.SYMBOL, TT.STRING)
        d[item.L.w] = item.R
    return Leaf(TT.OBJECT, Env(env, from_dict=d)), None, env, cstack

def asmod_tree(a, b, env, cstack):
    assert a.L.tt in (TT.SYMBOL, TT.STRING)
    d = {a.L.w: a.R}
    return Leaf(TT.OBJECT, Env(env, from_dict=d)), None, env, cstack


def zip_(a, b):
    return Leaf(a.tt, [Tree(x, Leaf(TT.PUNCTUATION, ":"), y) for x, y in zip(a.w, b.w)])


def order(a, b):
    return Leaf(a.tt, [i for i, _ in sorted(enumerate(a.w), key=lambda x: x[1])])


def choose(a, b):
    new = [0] * len(b.w)
    for i, pos in enumerate(b.w):
        # TODO handle out of bounds
        new[i] = a.w[pos]
    return Leaf(a.tt, new)


def tap(a, b, env, cstack):
    # Just for side effect
    Eval(Tree(a, b, Unit), env, cstack)
    return a, None, env, cstack


class Some:

    def __init__(self, x):
        self.value = x

    def __str__(self):
        return f"Some({self.value})"


def mkrange(lo, d, hi):
    n = (hi - 1 - lo) // d + 1
    return (lo, d, n)


def range_to_range(r):
    lo, d, n = r
    return range(lo, lo + d * n, d)


def bind(a, b):
    if b.tt == TT.TREE:
        fn, R = b.L, b.R
    else:
        fn, R = b, Unit
    return Tree(a, fn, R)


def json_each(filename, fn):
    import json
    with open(filename, "r") as f:
        for item in f:
            item = json.loads(item)
            item = Leaf(TT.NATIVE_OBJECT, Env(None, from_dict=item))
            item = Tree(item, fn, Unit)

            env = prepare_env()
            cstack = Cactus(ROOT_TAG)
            item, _, _, _ = Eval(item, env, cstack)
            print(item)

    return Unit


def add_type(x):
    if isinstance(x, (Leaf, Tree)):
        return x
    elif isinstance(x, str):
        t = TT.STRING
    elif isinstance(x, int):
        t = TT.NUM
    else:
        raise TypecheckError(f"Can't add type to native type {type(x).__name__} ")
    return Leaf(t, x)


def mod_assign(a, b):
    a.w.bind(b.L.w, b.R)
    return a


def mod_update(a, b, env, cstack):
    value = add_type(a.w.lookup(b.L.w, Unit))
    update_fn = b.R
    value, _, _, _ = Eval(Tree(value, update_fn, Unit), env, cstack)
    a.w.bind(b.L.w, value)
    return a, None, env, cstack


def ptr_update(a, b, env, cstack):
    mod_, at_ = a.w
    mod, at = mod_.w, at_.w
    value = add_type(mod.lookup(at, Unit))
    update_fn = b
    value, _, _, _ = Eval(Tree(value, update_fn, Unit), env, cstack)
    mod.bind(at, value)
    return a, None, env, cstack


def ptr_set(a, b):
    mod_, at_ = a.w
    mod, at = mod_.w, at_.w
    mod.bind(at, b)
    return a


def mod_merge(a, b):
    return Leaf(a.tt, Env(a.w.parent, from_dict={
        **a.w.e,
        **b.w.e,
    }))


def safe_variable(a, b, env, cstack):
    value, err = env.lookup(b.w, None), None
    if value is None:
        err = Shift("error", Leaf(TT.STRING, f"Variable {b.w} not defined"))
    return value, err, env, cstack


BUILTINS = {
    "jsoneach": lambda a, b: json_each(a.w, b),
    "=": eq,
    "==": eq,
    "!=": lambda a, b: Leaf(TT.NUM, 1 - eq(a, b).w),
    "T": get_type,
    "type": get_type,
    "retype": lambda a, b: Leaf(b.w, a.w),
    "sametype": lambda a, b: Leaf(TT.NUM, 1 if a.tt == b.tt else 0),
    "dispatch": set_dispatch,
    "til": lambda a, b: Leaf("range", mkrange(a.w, 1, b.w)),
    # "enumerate": lambda a, b: Leaf("range", (0, 1, a.w)),
    "if": lambda a, b: unwrap(a.L),
    "not": lambda a, b: Leaf(TT.NUM, 1 - a.w), # TODO doesn't play with unit ()
    "then": lambda a, b: if_(b, a),
    # "bake": bake,
    "open": lambda a, _: unwrap(a),
    "unwrap": lambda a, _: unwrap(a),
    "emptyvec": lambda a, b: Leaf("vec", []),
    ",": lambda a, b: Leaf("vec", [a, b]),
    "tovec": lambda a, b: Leaf("vec", [a]),
    "print": print_fn,
    "wait": wait,
    "O": new_object(Unit, Unit),
    "object": new_object(Unit, Unit),
    "bakevar": bakevar,
    "%": typecheck,
    ":%": typecheck,
    "!%": not_typecheck,
    "`": construct,
    "id": lambda a, b: a,
    ">>": bind,
    "error": lambda a, b: Leaf(TT.ERROR, a),

    "execute":    [execute],
    "cpush":   [reset],
    "reset":   [reset],
    "cpop":    [shift],
    "shift":   [shift],
    "load":    [load],
    "import":  [import_],
    "tap":     [tap],
    "IP":      lambda a, b: Tree(Unit, Leaf(TT.SYMBOL, "import"), Leaf(TT.STRING, "lib/prelude.hb")), # make it easy to import prelude

    "showenv": [lambda a, b, env, cstack: (Leaf(TT.OBJECT, env), None, env, cstack)],
    "@":       [at],
    #"$":       [lambda a, b, env, cstack: (env.lookup(b.w, a), None, env, cstack)],
    "$":       [safe_variable],
    ":$":      [safe_variable],
    "as":      [lambda a, b, env, cstack: (env.bind(b.w, a), None, env, cstack)],
    "assign":  [lambda a, b, env, cstack: (env.assign(b.w, a), None, env, cstack)],
    "is":      [lambda a, b, env, cstack: (env.assign(a.w, b), None, env, cstack)],
    "func":    [makefunc],
}


modules = {
    "true": {
        ".": lambda a, b: Leaf("true", "True"),
        ("and", "false"): lambda a, b: b,
        ("and", TT.THUNK): lambda a, b: unwrap(b),
        "and": lambda a, b: b,
        "or": lambda a, b: a,
    },
    "false": {
        ".": lambda a, b: Leaf("false", "False"),
        ("or", "true"): lambda a, b: b,
        ("or", TT.THUNK): lambda a, b: unwrap(b),
        "or": lambda a, b: b,
        "and": lambda a, b: a,
    },
    "range": {
        ("+", TT.NUM): lambda a, b: Leaf("range", (a.w[0] + b.w, a.w[1], a.w[2])),
        ("-", TT.NUM): lambda a, b: Leaf("range", (a.w[0] - b.w, a.w[1], a.w[2])),
        ("*", TT.NUM): lambda a, b: Leaf("range", (a.w[0] * b.w, a.w[1] * b.w, a.w[2])),
        # Division needs to convert to vec and then divide, otherwise lossy
        "tovec": lambda a, b: Leaf("num_vec", list(range_to_range(a.w))),
        # "fold": lambda a, b: Tree(Tree(a, Leaf(TT.SYMBOL, "tovec"), Unit), Leaf(TT.SYMBOL, "fold"), b),
        # "scan": lambda a, b: Tree(Tree(a, Leaf(TT.SYMBOL, "tovec"), Unit), Leaf(TT.SYMBOL, "scan"), b),
        #"sum": lambda a, b: Leaf(TT.NUM, arithmetic_series_sum(a.w[0], a.w[2], a.w[1])),
        "sum": lambda a, b: Leaf(TT.NUM, a.w[1] * a.w[2] * (a.w[2] - 1) // 2 + (a.w[2] * a.w[0])),
        "len": lambda a, b: Leaf(TT.NUM, a.w[2]),
        "each": lambda a, b: Tree(Tree(a, Leaf(TT.SYMBOL, "tovec"), Unit), Leaf(TT.SYMBOL, "each"), b),
    },
    "vec": {
        ",": lambda a, b: a.w.append(b) or a,
        "clone": lambda a, b: Leaf("vec", a.w[:]),
        ("~", "vec"): lambda a, b: Leaf("vec", a.w + b.w),
        ("@", TT.NUM): lambda a, b: a.w[b.w],
        "len": lambda a, b: Leaf(TT.NUM, len(a.w)),
        "asmod": [asmod_vec],
        "each": [each],
        "fold": [fold],
        ("zip", "vec"): zip_,
        ("@", "num_vec"): choose,
        "tonums": lambda a, b: Leaf("num_vec", [x.w for x in a.w]),
    },
    "num_vec": {
        ("~", "num_vec"): lambda a, b: Leaf("num_vec", a.w + b.w),
        "clone": lambda a, b: Leaf("vec", a.w[:]),
        "each": [lambda a, b, env, cstack: each(Leaf("num_vec", [Leaf(TT.NUM, x) for x in a.w]), b, env, cstack)],
        "len": lambda a, b: Leaf(TT.NUM, len(a.w)),
        ("+", "num_vec"): lambda a, b: Leaf("num_vec", [x + y for x, y in zip(a.w, b.w)]),
        ("-", "num_vec"): lambda a, b: Leaf("num_vec", [x - y for x, y in zip(a.w, b.w)]),
        ("*", "num_vec"): lambda a, b: Leaf("num_vec", [x * y for x, y in zip(a.w, b.w)]),
        ("/", "num_vec"): lambda a, b: Leaf("num_vec", [x // y for x, y in zip(a.w, b.w)]),
        (",", TT.NUM): lambda a, b: a.w.append(b.w) or a,
        ("=", TT.NUM): lambda a, b: Leaf("num_vec", [int(x == b.w) for x in a.w]),
        ("+", TT.NUM): lambda a, b: Leaf("num_vec", [x + b.w for x in a.w]),
        ("-", TT.NUM): lambda a, b: Leaf("num_vec", [x - b.w for x in a.w]),
        ("*", TT.NUM): lambda a, b: Leaf("num_vec", [x * b.w for x in a.w]),
        ("/", TT.NUM): lambda a, b: Leaf("num_vec", [x // b.w for x in a.w]),
        ("@", TT.NUM): lambda a, b: Leaf(TT.NUM, a.w[b.w]),
        "toset": lambda a, b: Leaf("num_set", set(a.w)),
        "max": lambda a, b: Leaf(TT.NUM, max(a.w)),
        "min": lambda a, b: Leaf(TT.NUM, min(a.w)),
        "sum": lambda a, b: Leaf(TT.NUM, sum(a.w)),
        "foldby": num_fold_by,
        "fold": num_fold,
        "scan": scan,
        "order": order,
        ("@", "num_vec"): choose,
        ">>": lambda a, b: Tree(a, Leaf(TT.SYMBOL, "eachflat"), b),
    },
    "num_set": {
        ("~", "num_set"): lambda a, b: Leaf("num_set", a.w | b.w),
        ("-", "num_set"): lambda a, b: Leaf("num_set", a.w - b.w),
    },
    TT.TREE: {
        # "if": if_,
        "L": lambda a, _: a.L,
        "H": lambda a, _: a.H,
        "R": lambda a, _: a.R,
        "asmod": [asmod_tree],
    },
    TT.OBJECT: {
        "extend": lambda a, b: Leaf(TT.OBJECT, a.w),
        ("@", TT.TREE): mod_assign,
        ("<=", TT.TREE): [mod_update],
        ("&", TT.SYMBOL): lambda a, b: Leaf("pointer", (a, b)),
        ("&", TT.STRING): lambda a, b: Leaf("pointer", (a, b)),
        ("@", TT.SYMBOL): lambda a, b: a.w.lookup(b.w, Unit),
        ("@", TT.STRING): lambda a, b: a.w.lookup(b.w, Unit),
        ("~", TT.OBJECT): mod_merge,
    },
    TT.NATIVE_OBJECT: {
        ("@", TT.TREE): mod_assign,
        ("<=", TT.TREE): [mod_update],
        ("&", TT.SYMBOL): lambda a, b: Leaf("pointer", (a, b)),
        ("&", TT.STRING): lambda a, b: Leaf("pointer", (a, b)),
        ("@", TT.SYMBOL): lambda a, b: add_type(a.w.lookup(b.w, Unit)),
        ("@", TT.STRING): lambda a, b: add_type(a.w.lookup(b.w, Unit)),
        ("~", TT.NATIVE_OBJECT): mod_merge,
    },
    "pointer": {
        ("update", TT.FUNCTION): [ptr_update],
        "set": ptr_set,
        "mod": lambda a, b: a.w[0],
        "at": lambda a, b: a.w[1],
        "get": lambda a, b: add_type(a.w[0].w.lookup(a.w[1].w, Unit)),
    },
    TT.NUM: {
        "tovec": lambda a, b: Leaf("num_vec", [a.w]),
        "rrep": lambda a, b: Leaf("vec", [b] * a.w),
        # ("rep", TT.NUM): lambda a, b: Leaf("num_vec", [b.w] * a.w),
        (",", TT.NUM): lambda a, b: Leaf("num_vec", [a.w, b.w]),
        ("+", TT.NUM): lambda a, b: Leaf(TT.NUM, a.w + b.w),
        ("-", TT.NUM): lambda a, b: Leaf(TT.NUM, a.w - b.w),
        ("*", TT.NUM): lambda a, b: Leaf(TT.NUM, a.w * b.w),
        ("/", TT.NUM): lambda a, b: Leaf(TT.NUM, a.w // b.w),
        ("mod", TT.NUM): lambda a, b: Leaf(TT.NUM, a.w % b.w),
        ("<", TT.NUM): lambda a, b: Leaf(TT.NUM, 1 if a.w < b.w else 0),
        ("<=", TT.NUM): lambda a, b: Leaf(TT.NUM, 1 if a.w <= b.w else 0),
        (">", TT.NUM): lambda a, b: Leaf(TT.NUM, 1 if a.w > b.w else 0),
        (">=", TT.NUM): lambda a, b: Leaf(TT.NUM, 1 if a.w >= b.w else 0),
        ("and", TT.NUM): lambda a, b: Leaf(TT.NUM, 1 if 0 not in (a.w, b.w) else 0),
        ("or", TT.NUM): lambda a, b: Leaf(TT.NUM, 1 if 1 in (a.w, b.w) else 0),
        ("not", TT.NUM): lambda a, b: Leaf(TT.NUM, 1 if a.w == 0 else 0),
    },
    TT.SYMBOL: {
        ("~", TT.SYMBOL): lambda a, b: Leaf(a.tt, a.w + b.w),
        ("~", TT.STRING): lambda a, b: Leaf(a.tt, a.w + b.w),
    },
    TT.STRING: {
        ("*", TT.NUM): lambda a, b: Leaf(a.tt, a.w * b.w),
        ("~", TT.STRING): lambda a, b: Leaf(a.tt, a.w + b.w),
        ("~", TT.SYMBOL): lambda a, b: Leaf(a.tt, a.w + b.w),
        ("/", TT.STRING): lambda a, b: Leaf("vec", [Leaf(TT.STRING, x) for x in a.w.split(b.w)]),
        ("@", TT.NUM): lambda a, b: Leaf(TT.STRING, a.w[b.w]),
        ("@", TT.TREE): lambda a, b: Leaf(TT.STRING, a.w[b.L.w : b.R.w]),
        "len": lambda a, b: Leaf(TT.NUM, len(a.w)),
    },
    TT.FUNCTION: {
        # ("dispatch", TT.TREE): lambda a, b, env: set_dispatch(a, b, env), # TODO special
        # "asmod": lambda a, b: Tree(unwrap(a), Leaf(TT.SYMBOL, "asmod"), Unit),
    },
    TT.THUNK: {
        "asmod": lambda a, b: Tree(unwrap(a), Leaf(TT.SYMBOL, "asmod"), Unit),
    },
    TT.UNIT: {
        ">>": lambda a, b: a,
        "?": lambda a, b: unwrap(b.R),
    },
    "Some": {
        ".": lambda a, b: Leaf("Some", Some(a)),
        ">>": lambda a, b: Tree(a.w.value, b, Unit), # TODO define this generically in some parent functor?
        (">>", TT.TREE): lambda a, b: Tree(a.w.value, b.L, b.R),
        # ("+>", TT.TREE): lambda a, b: Tree(Tree(a, Leaf(TT.PUNCTUATION, ">>"), b), Leaf(TT.SYMBOL, "Some"), Unit),
    },
}

def as_module(mod_dict):
    d = {}
    for k, v in mod_dict.items():
        if not isinstance(k, str):
            k = DISPATCH_SEP.join(map(str, k))

        if isinstance(v, list):
            v = Leaf(TT.SPECIAL, v[0])
        else:
            v = Leaf(TT.BUILTIN, v)

        d[k] = v
    return d


def Execute_(code, env, cstack):
    x = code
    x = Lex(x)
    # print("LEX", y)
    x = Parse(x)

    # Wrap in error reset
    x = Tree(Leaf(TT.SYMBOL, "error", debug=Unit.debug),
             Leaf(TT.SYMBOL, "reset"),
             Leaf(TT.THUNK, x, debug=x.debug))
    # Wrap in global reset
    x = Tree(Leaf(TT.SYMBOL, ROOT_TAG, debug=Unit.debug),
             Leaf(TT.SYMBOL, "reset"),
             Leaf(TT.THUNK, x, debug=x.debug))

    x, err, env, cstack = Eval(x, env, cstack)
    return x, err, env, cstack


def Execute(code, env, cstack):
    try:
        return Execute_(code, env, cstack)
    except (ParseError, NoDispatch, CantReduce) as err:
        #print("ERR", err, type(err), file=sys.stderr)

        if err.witness.debug is not None:
            start = err.witness.debug.start
            end = err.witness.debug.end
            lineno = err.witness.debug.lineno
            line = code.split("\n")[lineno]

            break_ = "  "
            if start + (end - start) + len(break_) + len(err.msg) > 70:
                break_ = "\n"

            msg = f"""ERROR
{line}
{" " * start}{"^" * (end - start)}{break_}{err.msg}"""
            print(msg, file=sys.stderr)
        else:
            print(err, file=sys.stderr)
        #print(f"Parse error: {err}", file=sys.stderr)
    except UnexpectedType as err:
        print("UNEXPECTED TYPE", err, file=sys.stderr)
    except Cactus.Empty as err:
        print(f"No matching reset with tag {err.tag}", file=sys.stderr)
        cstack.spush(ROOT_TAG)

    return Unit, None, None, None


def mod_merge(a, b):
    m = {k: v for k, v in a.items()}
    for k, v in b.items():
        if k in m:
            m[k] = {
                **m[k],
                **v,
            }
        else:
            m[k] = v
    return m


def prepare_env():
    modules_ = mod_merge(modules, matrix.modules)
    mods = {k: Leaf(TT.OBJECT, Env(None, from_dict=as_module(mod)))
            for k, mod in modules_.items()}

    rootenv = Env(None, from_dict={
        **as_module(BUILTINS),
        **mods,
    })

    # rootenv = Env(rootenv)  # dummy env
    return rootenv


def Repl(env, rstack, prompt="> "):
    import readline
    readline.parse_and_bind('tab: complete')
    readline.parse_and_bind('set editing-mode vi')

    while True:
        try:
            x = input(prompt)
            x, _, _, _ = Execute(x, env, cstack)
            print(x)
        except TypecheckError as err:
            print(err, file=sys.stderr)
        except (EOFError, KeyboardInterrupt):
            break
        sys.stdout.flush()


if __name__ == "__main__":
    env = prepare_env()
    cstack = Cactus(ROOT_TAG)

    if len(sys.argv) == 1:
        try:
            Repl(env, cstack)
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

            x, _, env, cstack = Execute(src, env, cstack)
            print(x)
        else:
            print("Missing command (run)", file=sys.stderr)
            sys.exit(1)
