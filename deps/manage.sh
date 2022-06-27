#!/bin/sh

##### Python dependencies management
#
# Python requirements management with pip-tools in an existing virtual environnement.
# Requirements are pinned with package version and hashes in the following files :
#    - dev-requirements.txt is for installing dev environment with :
#        pip-sync dev-requirements.txt
#    - docker-requirements.txt for install in docker image (base image should pick it by default).
#    - requirements.txt specify dependencies without hashes (IDEs should pick it by default).
#
# Usage:
#
#  * Specify the python packages (as for pip install) in the *.in files in this directory :
#    - deps/base.in for project runtime dependencies
#    - deps/dev.in for project development dependencies
#
#  * Whenever these files are updated, run this script to compile the requirements files :
#      sh deps/manage.sh compile
#   and commit the modifications in both deps/*.ir and requirements files
#
#  * Upgrade the pinned versions of dependencies with :
#      sh deps/manage.sh upgrade
#


# Exit if any command fail
set -e

# Uncomment next line to trace commands execution
# set -x

# Either 'compile' or 'upgrade'
action="$1"

out_dev="dev-requirements.txt"
out_docker="docker-requirements.txt"
out_no_hashes="requirements.txt"

help_message() {
  echo "Usage: ${0} [action]

Python requirements files management.

Available actions :
  * compile : generate requirements files from deps/*.in
  * upgrade : update packages in existing requirements files

See sources in ${0} for details."
}

failure() {
  msg="$1"
  echo "${msg}"
  exit 1
}

failure_with_help() {
  msg="$1"
  echo "${msg}"
  help_message
  exit 1
}

# change current working dir to parent directory of this script
ch_cwd() {
  script_dir=$(dirname "$0")
  script_dir_realpath=$(realpath "${script_dir}")
  script_dir_parent="${script_dir_realpath}/.."
  cd "${script_dir_parent}" > /dev/null || failure "Cannot change current working dir to '${script_dir_parent}'"
  echo "[project_dir] '$(pwd)'"
}


if [ -z "${VIRTUAL_ENV}" ] ; then
  failure "Virtual environment not activated. If you have not already create it, do it now with :

  python -m venv <path_to_venv>

Once you have a virtual environment for this project, activate it before running this script with :

  source <path_to_venv>/bin/activate
"
else
  echo "[venv] ${VIRTUAL_ENV}"
  echo
fi

echo "[pip-tools]"
pip-compile --version || failure "pip-tools does not seem to be installed in this virtual environment.
Install pip-tools before running this script with:

    pip install pip-tools
"
echo
case "${action}" in

  "upgrade")
      export CUSTOM_COMPILE_COMMAND="${0} upgrade"
      echo "[action] Upgrading dependencies to their latest version"
      echo
      ch_cwd

      echo "[upgrade] '${out_dev}'"
      pip-compile \
          --upgrade \
          deps/base.in deps/dev.in \
          --output-file="${out_dev}"
      echo "[upgrade] '${out_docker}'"
      pip-compile \
          --upgrade \
          deps/base.in \
          --output-file="${out_docker}"
      echo "[upgrade] '${out_no_hashes}'"
      pip-compile \
          --upgrade \
          deps/base.in deps/dev.in \
          --output-file="${out_no_hashes}"

      echo
      echo "Dependencies upgraded and requirements files updated."
      echo "You should run pip-sync now :"
      echo
      echo "    pip-sync dev-requirements.txt"
      echo
      exit 0
    ;;

  "compile")
      export CUSTOM_COMPILE_COMMAND="${0} compile"
      echo "[action] Compiling requirements files from deps/*.in"
      echo
      ch_cwd

      echo "[compile] '${out_dev}'"
      pip-compile \
          --allow-unsafe \
          --generate-hashes \
          deps/base.in deps/dev.in \
          --output-file="${out_dev}"
      echo "[compile] '${out_docker}'"
      pip-compile \
          --allow-unsafe \
          --generate-hashes \
          deps/base.in \
          --output-file="${out_docker}"
      echo "[compile] '${out_no_hashes}'"
      pip-compile \
          --allow-unsafe \
          deps/base.in deps/dev.in \
          --output-file="${out_no_hashes}"

      echo "
Requirements files updated. You should run pip-sync now :
  pip-sync dev-requirements.txt
"
      exit 0
    ;;

  "help")
      help_message
      exit 0
    ;;

  "")
      failure_with_help "Error : no action specified"
    ;;

  *)
      failure_with_help "Error : unknown action '${action}'"
    ;;
esac
