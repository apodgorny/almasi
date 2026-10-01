#!/bin/bash

set -e

pushd "$(dirname "$0")" > /dev/null

if [ -n "$VIRTUAL_ENV" ]; then
	"$VIRTUAL_ENV/bin/python" -m pip install -e .
	PYTHON="$VIRTUAL_ENV/bin/python"
elif command -v python > /dev/null 2>&1; then
	python -m pip install -e .
	PYTHON="$(command -v python)"
elif command -v python3 > /dev/null 2>&1; then
	python3 -m pip install -e .
	PYTHON="$(command -v python3)"
else
	echo "Python not found"
	exit 1
fi

cat > "$HOME/.local/bin/almasi" <<EOF
#!/bin/sh
exec "$PYTHON" "$PWD/bootstrap/almasi.py" "\$@"
EOF

chmod +x "$HOME/.local/bin/almasi"

popd > /dev/null

echo
echo "Almasi installed"
echo "Almasi CLI tools installed"
echo