# 1. Foreach loop over $$xs
$$xs foreach x: [
    $$x < 10 then [
        $$x !print
    ]:[
        .break.
    ]
]

# 2. define macro of factorial function
factorial define (a, b: string): [
    $$a !print |
    $$b !print
]

# ... and its expansion. Sort of..
factorial is {$$y !R!L as a | $$y !R!R!L as b | .($$y !R).}

# 3. Example SQL DSL
[
    select [a, b, c, d, e]
    from some:table
    where [everything < nothing]
    order_by [a:desc, b:asc, c]
    limit 100
]

# 4. Random examples
(123.34`u64) + (123.66`u64)
[1,2,3,4] ; [5,6,7,8]
