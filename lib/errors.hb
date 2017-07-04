  catch is {value.handler | error reset value handle handler}
| handle is {retval.handler
    | retval type. = ERROR
    then [retval handler.] : [retval]
  }
| raise is {error shift x}
