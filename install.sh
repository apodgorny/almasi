#!/bin/bash

set -e

pushd "$(dirname "$0")" > /dev/null

if [ -n "$VIRTUAL_ENV" ]; then
	"$VIRTUAL_ENV/bin/python" -m pip install -e .
elif command -v python > /dev/null 2>&1; then
	python -m pip install -e .
elif command -v python3 > /dev/null 2>&1; then
	python3 -m pip install -e .
else
	echo "Python not found"
	exit 1
fi

popd > /dev/null

echo
echo "Almasi installed"
echo
