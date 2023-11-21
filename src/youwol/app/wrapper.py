# standard library
import os
import sys

from pathlib import Path


def ensure_venv_python_in_path():
    python_bin_dir = Path(sys.executable).parent
    if not any(
        path == str(python_bin_dir) for path in os.environ["PATH"].split(os.pathsep)
    ):
        print(
            f"Adding detected Python binaries directory '{python_bin_dir}' to environment variable PATH"
        )
        os.environ["PATH"] = f"{python_bin_dir}{os.pathsep}{os.environ['PATH']}"


def main():
    ensure_venv_python_in_path()
    os.execvp(file=sys.executable, args=["python", *sys.argv[1:]])


if __name__ == "__main__":
    main()
