#!/bin/zsh
# QDuo -> bell. $1 = ask; selection on stdin; echo it back (output=copy, no panel).
t=$(cat)
~/Polaris/Staging/bell/ring "grabscope:$1" "$t"
print -r -- "$t"
