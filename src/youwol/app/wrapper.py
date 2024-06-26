# standard library
import os
import platform
import sys

from pathlib import Path


def ensure_env_for_python():
    python_bin_dir = Path(sys.executable).parent
    if not any(
        path == str(python_bin_dir) for path in os.environ["PATH"].split(os.pathsep)
    ):
        print(
            f"Adding detected Python binaries directory '{python_bin_dir}' to environment variable PATH"
        )
        os.environ["PATH"] = f"{python_bin_dir}{os.pathsep}{os.environ['PATH']}"
    pythonpath = os.environ.get("PYTHONPATH")
    if not pythonpath:
        print("Environment variable PYTHONPATH not set")
        pythonpath = sys.path[0]
        print(f"Setting environment variable PYTHONPATH to {pythonpath}")
    python_paths_separator = ";" if platform.system() == "Windows" else ":"
    python_paths = [
        path for path in pythonpath.split(python_paths_separator) if path.strip()
    ]
    pythonpath = python_paths[0]
    if len(python_paths) > 1:
        print(
            "WARNING: using multiple path in environment variable PYTHONPATH is not yet supported!"
        )
    elif not Path(pythonpath).exists():
        print(
            f"WARNING: environment variable PYTHONPATH '{pythonpath}' is a non-existing path!"
        )
    elif platform.system() != "Windows" and not Path(pythonpath).is_dir():
        print(
            f"WARNING: environment variable PYTHONPATH '{pythonpath}' is not the path of a directory!"
        )
    elif not Path(pythonpath).is_absolute():
        print(f"Environment variable PYTHONPATH '{pythonpath}' is a relative path")
        pythonpath_abs = str(Path(pythonpath).absolute())
        os.environ["PYTHONPATH"] = pythonpath_abs
        print(f"Setting environment variable PYTHONPATH to '{pythonpath_abs}'")


def main():
    ensure_env_for_python()
    os.execvp(file=sys.executable, args=["python", *sys.argv[1:]])


if __name__ == "__main__":
    main()
