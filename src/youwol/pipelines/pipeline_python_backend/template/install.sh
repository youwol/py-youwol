#!/bin/bash

# Extract name and version from package.json using grep and sed
name=$(grep -E '"name":' package.json | sed -E 's/.*: "(.+)".*/\1/')
version=$(grep -E '"version":' package.json | sed -E 's/.*: "(.+)".*/\1/')

# Check if name and version were extracted successfully
if [ -z "$name" ] || [ -z "$version" ]; then
    echo "Failed to extract name or version from package.json."
    exit 1
fi

echo "Package name: $name"
echo "Package version: $version"

if [ -d ".venv" ]; then
    echo "remove previous .venv folder."
    rm -rf .venv
fi

echo "creating and activating new .venv ..."
python3 -m venv .venv || exit 1
. .venv/bin/activate || exit 1

# Install wheel from ./dist folder
echo "Installing module from wheel..."
pip install --force-reinstall "./dist/$name-$version-py3-none-any.whl" || exit 1
exit 0
