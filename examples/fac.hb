{.$x 
    {n.acc | [.$acc] : [(.$n - 1) f (.$acc * .$n)] if (.$n <= 0)}
1} as fac

| 5 fac. print.
| 7 fac. print.
| 9 fac. print.
| ()
