foreach is {$$x as n|$$y as fn|i is 0|break is {k shift [$$x]}|.reset [!!{[i is ($$i + 1)|!!fn|!!self]:() if ($$i < $$n)}]}

10000 foreach {$$i P. | [ended!break]:() if ($$i > 5000)}
