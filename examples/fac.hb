{.$x 
    {n.acc | (.$n <= 0) ? [.$acc] : [(.$n - 1) f (.$acc * .$n)]}
1} -> fac

| _1 fac. print.
| 0 fac. print.
| 3 fac. print.
| 5 fac. print.
| 7 fac. print.
| 9 fac. print.
| 20 fac. print.
| 40 fac. print.
| 60 fac. print.
| ()
