loop is {cnt.body
    | 0 as cnt
    | break is {loop shift x}
    | loop reset [()
        {()body() | .$cnt + 1 as cnt | ()F()}
      ()]
}
