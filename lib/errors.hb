  catch is {value.handler | .reset value handle handler}
| handle is {retval.handler
    | retval type. = ERROR
    then [retval handler.] : [retval]
  }
| raise is {.shift x}
