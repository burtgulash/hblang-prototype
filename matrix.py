from c import Tree, Leaf, TT


class Matrix:

    def __init__(self, shape, ar):
        assert isinstance(shape, list)
        assert isinstance(ar, list)
        self._shape = shape
        self._ar = ar

    def apply(self, fn, value):
        return Matrix(self._shape, [fn(x, value) for x in self._ar])

    def rank(self):
        return len(self._shape)

    def shape(self):
        return self._shape[:]

    def reshape(self, new_shape):
        return Matrix(new_shape, self._ar[:])

    @staticmethod
    def print_dim(shape, ar, start, stride):
        if not shape:
            return str(ar[start]) + " "

        cur, rest = shape[0], shape[1:]
        x = "".join(Matrix.print_dim(
            rest,
            ar,
            start + i * stride,
            stride * cur)
            for i in range(cur)
        )

        return x + "\n"

    def __str__(self):
        return Matrix.print_dim(self._shape, self._ar, 0, 1).rstrip("\n")

def tomatrix(vec):
    return Matrix([len(vec.w)], vec.w)


modules = {
    "num_vec": {
        "tomatrix": lambda a, b: Leaf("matrix", tomatrix(a)),
    },
    "matrix": {
        ("reshape", "num_vec"): lambda a, b: Leaf(a.tt, a.w.reshape(b.w)),
        ("+", TT.NUM): lambda a, b: Leaf(a.tt, a.w.apply((lambda a, b: a + b), b.w)),
        ("-", TT.NUM): lambda a, b: Leaf(a.tt, a.w.apply((lambda a, b: a - b), b.w)),
        ("*", TT.NUM): lambda a, b: Leaf(a.tt, a.w.apply((lambda a, b: a * b), b.w)),
        ("/", TT.NUM): lambda a, b: Leaf(a.tt, a.w.apply((lambda a, b: a // b), b.w)),
        "shape": lambda a, b: Leaf("num_vec", a.w.shape()),
        "rank": lambda a, b: Leaf(TT.NUM, a.w.rank()),
    }
}
