#!/bin/bash
# Wrapper script for iCluster-web installer web UI
# Sets LIBPATH to help PASE dynamic linker find postgresql libraries

export LIBPATH=/QOpenSys/pkgs/lib/postgresql12/lib:$LIBPATH
SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
cd "$SCRIPT_DIR" || exit 1
exec /QOpenSys/pkgs/bin/python3.6 web_app.py "$@"
