loop is {label.body
    | 0 as i
    | label reset [()
        {()body() | .$i + 1 as i | ()F()}
      ()]
}

| break is {label.value | label shift value}
