repeated is {
    $$x as fn | $$y as n | {
        $$n le 0 then
            [$$x]:
            [n dec 1 | $$x fn. self.]
    }
}
