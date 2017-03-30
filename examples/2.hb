foreach is {
    $$x as n
    | $$y as fn
    | i is 0
    | break is {k cpop [$$x]}       # Break shifts continuation
    | !cpush [!!{                   # Spawn continuation
        ($$i < $$n) then [
              i is ($$i + 1)
              | !!fn
              | !!self
        ]:()
    }]
}

| 1000 foreach {
    $$i !print
    | [ended !break]:() if ($$i > 500)
}
