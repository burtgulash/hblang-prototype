!
| !           is {x.fn | x fn.}
| flip        is {f | {y f x} func.}
| ^           is {fn.op | {x op fn:y} func.}
| eachright   is {(y R.) each ((y L.flip.):x)}
| list_to_vec is {x type. = TREE then [((x L.) F.) , (x R.)] : [x tovec.]}
| pow         is {base.exp | exp mod 2 = 0 then [exp = 0 then 1 : ([base F (exp / 2) as "z" | z * z] bakevar z)] : [base F (exp - 1) * base]}
| factorial   is {x {n.acc | n <= 1 then [acc] : [n - 1 F acc * n]} 1}
| rep         is {y rrep x}
| sort        is {xs | xs order. (@ flip.) xs}
| eachflat    is {xs.f | xs each f fold ~}
| abort       is {abort shift x}
| reduce      is {xs.f
                  | xs len. as l
                  | .$l = 0 then () : [
                    xs @0 {acc.i | i >= (.$l) then [acc] : [(acc f (xs @i)) F (i + 1)]} 1
                  ]}
| times       is {fn : n | {x {a : i | i <= 0 then [a] : [a fn. F (i - 1)]} n} func.}
