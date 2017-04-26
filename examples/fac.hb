{.$x 
    {n.acc | (.$n <= 0) ? [.$acc] : [(.$n - 1) f (.$acc * .$n)]}
    {n.acc | (n <= 0) ? [acc] : [(n - 1) f (acc * n)]}
1} -> fac

| 5 fac. print.
| 7 fac. print.
| 9 fac. print.
| ()

