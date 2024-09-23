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

# build args parsing
show_usage() {
    echo "  -f, --fingerprint        build fingerprint"
    echo "  -h, --help               Display this help message"
}

FINGERPRINT=''
MODULES=''
PYTHON='python3'

# Parse arguments
while [ "$#" -gt 0 ]; do
    case "$1" in
        --fingerprint)
            FINGERPRINT="$2"
            shift 2
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            echo "Invalid option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Shift to skip processed options
shift $((OPTIND-1))

echo "Build fingerprint: $FINGERPRINT"
echo "Modules: $MODULES"

VENV_DIR=".venv_$FINGERPRINT"

echo "Target venv dir: $VENV_DIR"

if [ -d "$VENV_DIR" ]; then
    echo "remove previous .venv folder for build fingerprint $FINGERPRINT."
    rm -rf "$VENV_DIR"
fi

echo "creating and activating new $VENV_DIR ..."
"$PYTHON" -m venv "$VENV_DIR" || exit 1
. "$VENV_DIR/bin/activate" || exit 1

# Install wheel from ./dist folder
echo "Installing module from wheel..."
pip install --force-reinstall "./dist/$name-$version-py3-none-any.whl" --find-links "./deps" || exit 1

exit 0
