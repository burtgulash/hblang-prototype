!
| !           is {x.fn | x fn.}
| flip        is {f:z | {y f x}}
| ^           is {fn.op | {x op fn:y}}
| eachright   is {(y R.) each ((y L.flip.):x)}
| list_to_vec is {x type. = TREE then [((x L.) F.) , (x R.)] : [x tovec.]}
| pow         is {base.exp | exp mod 2 = 0 then [exp = 0 then 1 : ([base F (exp / 2) as "z" | z * z] bakevar z)] : [base F (exp - 1) * base]}
| rep         is {y rrep x}
| sort        is {xs.z | xs order. (@ flip.) xs}
