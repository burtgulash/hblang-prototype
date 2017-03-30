visit is {
    ($$x sametype ()) then
    () : [
        k cpop [($$x !L) : ($$x !R !self !k)]
    ]
}

| reverse is {
    !cpush [$$x !visit]
}
