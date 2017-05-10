!
| {f:z | {y f x}} as flip
| {fn.op | {x op fn:y}} as ^
| {(y R.) each ((y L.flip.):x)} as eachright
| {x type. = TREE then [((x L.) F.) , (x R.)] : [x tovec.]} as list_to_vec
| {base.exp | exp mod 2 = 0 then [exp = 0 then 1 : [base F (exp / 2) as z | .$z * .$z]] : [base F (exp - 1) * base]} as pow
| {y rrep x} as rep
