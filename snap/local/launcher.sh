#!/bin/bash
export PYTHONPATH="${SNAP}/lib/python3.10/site-packages:${PYTHONPATH}"
export LD_LIBRARY_PATH="${SNAP}/usr/lib:${LD_LIBRARY_PATH}"
export PATH="${SNAP}/usr/bin:${PATH}"

exec "$SNAP/bin/python3" "$SNAP/main.py" "$@" 