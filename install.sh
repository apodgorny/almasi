pushd "$(dirname "$0")" > /dev/null

py -m pip uninstall -y a
py -m pip install -e .

popd > /dev/null