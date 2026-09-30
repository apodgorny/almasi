pushd "$(dirname "$0")" > /dev/null

python -m pip uninstall -y a
python -m pip install -e .

popd > /dev/null