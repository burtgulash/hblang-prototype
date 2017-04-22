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
        "|": lambda a, b, env: a,
        ">>=": lambda a, b, env: a,
        #"=>": make_binding,
    },
    "Some": {
        ".": lambda a, b, env: Leaf("Some", Some(a)),
        "|": lambda a, b, env: Tree(a.w.value, b.L, b.R),
        ">>=": lambda a, b, env: Tree(Tree(a.w.value, Leaf(TT.PUNCTUATION, "->"), b.L), Leaf(TT.SEPARATOR, ";"), Tree(Unit, b.R, Unit)),
        #">>=": lambda a, b, env: Parse(Lex(f"{a.w.value} -> {b.L}; () {b.R} ()"))
        # "=>": make_binding,
    },
#    "binding": {
#        ("|", TT.TREE): lambda binding, b, env: binding.w.functor.w.bind_eval(binding.w.name, b.L, b.R, env),
#        "|": lambda binding, b, env: binding.w.functor.w.bind_eval(binding.w.name, b, Unit, env),
#        "|": lambda binding, b, env: Tree(Tree(binding.w.functor, Leaf(TT.PUNCTUATION, "|"), b)),
#    }
}
