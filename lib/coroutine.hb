yield is {value
    | __gen__ shift {cc | (value : cc)}
}

| gen is {body
    | {__gen__ reset body} func.
}
