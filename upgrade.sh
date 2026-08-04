#!/bin/bash
# UDO upgrade wrapper. All logic lives in upgrade.py (cross-platform,
# stdlib-only); this script just execs it with the interpreter on PATH.
exec python3 "$(dirname "$0")/upgrade.py" "$@"
