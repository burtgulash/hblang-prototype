from c import Tree, Leaf, Unit, TT
from hb import Lex, Parse, Eval, unwrap

class Some:

    def __init__(self, x):
        self.value = x

    def __str__(self):
        return f"Some({self.value})"


class Binding:

    def __init__(self, functor, name):
        self.functor = functor
        self.name = name

    def __str__(self):
        return f"{str(self.functor)} => {self.name}"


def make_binding(a, b, env):
    return Leaf("binding", Binding(a, b.w))


builtins = {
}

# NOTE final possible syntax
# .do [.$x => a; .$y => b; .$a + .$b]
# .$x >>= a: [.$y >>= b: [.$a / .$b]]

modules = {
    TT.UNIT: {
        ">>": lambda a, b, env: a,
        "?": lambda a, b, env: unwrap(b.R),
    },
    "Some": {
        ".": lambda a, b, env: Leaf("Some", Some(a)),
        ">>": lambda a, b, env: Tree(a.w.value, b, Unit), # TODO define this generically in some parent functor?
        (">>", TT.TREE): lambda a, b, env: Tree(a.w.value, b.L, b.R),
        # ("+>", TT.TREE): lambda a, b, env: Tree(Tree(a, Leaf(TT.PUNCTUATION, ">>"), b), Leaf(TT.SYMBOL, "Some"), Unit),
    },
}
