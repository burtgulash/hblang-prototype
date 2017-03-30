foreach is {$$x as n|$$y as fn|i is 0|break is {k shift [$$x]}|.reset [!!{[i is ($$i + 1)|!!fn|!!self]:() if ($$i < $$n)}]}

1000 foreach {$$i !print | [ended!break]:() if ($$i > 500)}
