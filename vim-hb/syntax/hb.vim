" Vim syntax file
" Language: HB
" Maintainer: Burtgulash
" Latest Revision: 30 March 2017

if exists("b:current_syntax")
    finish
endif


syn keyword hbContinuation cpush cpop
syn keyword hbFunctionKeyword contained x y self

syn match hbNumber "[_0-9]*"
syn match hbSymbol "[a-zA-Z][a-zA-Z0-9_]*"
syn match hbPunctuation "[!$%&*+,-./:;<=>?@\\^`~]"

syn match hbParenthesis "[(){}|]"
syn match hbDelay "[\[\]]"
syn match hbFuncDef "[{}]"
syn match hbVoid "( *)"

syn region hbFunction start='{' end='}' contains=ALL fold transparent
syn region hbString start='"' end='"'

syn keyword hbTodo contained TODO FIXME NOTE
syn match hbComment "#.*$" contains=hbTodo


hi def link hbTodo              Todo
hi def link hbComment           Comment
hi def link hbString            String
hi def link hbNumber            Number
hi def link hbNumber            Statement
hi def link hbKeyword           Keyword
hi def link hbParenthesis       Delimiter
hi def link hbDelay             Type
hi def link hbPunctuation       Operator
hi def link hbVoid              Number
hi def link hbFuncDef           Comment
hi def link hbFunction          Statement
hi def link hbFunctionKeyword   Keyword
hi def link hbContinuation      Keyword

let b:current_syntax = "hb"
