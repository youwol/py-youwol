#!/bin/bash

# Extract name and version from package.json using grep and sed
name=$(grep -E '"name":' package.json | sed -E 's/.*: "(.+)".*/\1/')
version=$(grep -E '"version":' package.json | sed -E 's/.*: "(.+)".*/\1/')

# Check if name and version were extracted successfully
if [ -z "$name" ] || [ -z "$version" ]; then
    echo "Failed to extract name or version from package.json."
    exit 1
fi

show_usage() {
    echo "Usage: $0 -p <port> -h <host> [other_arguments]"
    echo "Example: $0 -p 2010 -s 2000"
    echo "  -p, --serving-port       Specify serving port"
    echo "  -s, --server-port        Specify the server (youwol) port"
    echo "  -h, --help               Display this help message"
}



# Parse command-line options
while getopts ":p:s:h" opt; do
  case $opt in
    p)
      PORT="$OPTARG"
      ;;
    s)
      HOST="$OPTARG"
      ;;
    h)
      show_usage
      exit 0
      ;;
    \?)
      echo "Unused extra option: -$OPTARG"
      ;;
    :)
      echo "Option -$OPTARG requires an argument."
      exit 1
      ;;
  esac
done

# Shift to skip processed options
shift $((OPTIND-1))

echo "Package name: $name"
echo "Package version: $version"
echo "Serving port: $PORT"
echo "Server port: $HOST"

. .venv/bin/activate

python -m "$name".main  --port="$PORT" --yw_port="$HOST"