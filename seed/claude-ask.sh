#!/bin/zsh
# QDuo -> Claude. $1 = instruction; selection arrives on stdin. QDuo kills us at 10s.
# ponytail: Haiku for speed under the 10s cap; long selections may still time out.
cd /tmp && exec ~/.local/bin/claude -p --setting-sources "" --strict-mcp-config --tools "" \
  --no-session-persistence --model haiku "$1 The text is on stdin."
