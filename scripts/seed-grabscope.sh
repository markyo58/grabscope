#!/bin/zsh
# Seed ~/.config/grabscope from the repo (never overwrites an existing config.json).
d=~/.config/grabscope; mkdir -p $d; here=${0:A:h}/../seed
for f in $here/*; do [[ -e $d/${f:t} ]] || cp $f $d/; done; chmod +x $d/*.sh $d/*.py; echo "seeded $d"
