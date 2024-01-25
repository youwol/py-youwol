#!/bin/sh

set -e

dash2underscore() {
  echo "$1" | sed "s/-/_/g"
}

underscore2dash() {
  echo "$1" | sed "s/_/-/g"
}

if [ -z "$YOUWOL_SOURCES_PATH" ]; then
  echo "Missing expected environment variable YOUWOL_SOURCES_PATH"
  exit 1
fi

YOUWOL_SOURCES_PATH=$(realpath "$YOUWOL_SOURCES_PATH")

echo "Using youwol sources path '${YOUWOL_SOURCES_PATH}'"

if [ ! -d "${YOUWOL_SOURCES_PATH}" ]; then
  echo "Directory '${YOUWOL_SOURCES_PATH}' does not exist"
  exit 1
fi

backends_directory_path="${YOUWOL_SOURCES_PATH}/youwol/backends"

if [ ! -d "${backends_directory_path}" ]; then
  echo "Backend directory '${backends_directory_path}' does not exist"
  exit 1
fi

cd "${backends_directory_path}" || exit 1

echo "Available backends:"
for backend in *; do
  if [ -f "${backend}/deployment.py" ]; then
    dashed_backend=$(underscore2dash ${backend})
    echo " * ${dashed_backend}"
  fi
done

dashed_backend="$1"
if [ "x${backend}" = "x" ]; then
  echo "Entry point need one argument, the backend name"
  exit 1
fi

underscored_backend=$(dash2underscore ${dashed_backend})

if [ ! -f "${backends_directory_path}/${underscored_backend}/deployment.py" ]; then
  echo "Argument '${dashed_backend}' is not a backend"
  exit 1
fi

echo "Selected backend: '${dashed_backend}'"

echo "Entering youwol source directory '${YOUWOL_SOURCES_PATH}'"
cd "${YOUWOL_SOURCES_PATH}" || exit 1

echo "Executing uvicorn"
exec uvicorn "youwol.backends.${underscored_backend}.deployment:app" --host=0.0.0.0 --no-server-header --port=8080
