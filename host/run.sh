#!/bin/bash
# Starts the DEFUSE AI host. Usage:  ./run.sh   (reads your key from the environment)
cd "$(dirname "$0")"
exec ./venv/bin/python defuse_host.py --mic "$@"
