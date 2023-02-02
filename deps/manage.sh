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

# Either 'compile', 'upgrade' or 'upgrade'
action="$1"
package="$2"

out_dev="dev-requirements.txt"
extras_dev="--extra=dev --extra=qa --extra=publish"

out_qa="qa-requirements.txt"
extras_qa="--extra=qa"

out_publish="publish-requirements.txt"
extras_publish="--extra=publish"

out_docker="docker-requirements.txt"

out_no_hashes="requirements.txt"

help_message() {
  echo "Usage: ${0} [action]

Python requirements files management.

Available actions :
  * compile             : generate requirements files from deps/*.in
  * upgrade [<package>] : upgrade all packages or only specified package in existing requirements files

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

pip_compile() {
  out=$1
  extras=$2
  no_hashes=$3

  opts="--allow-unsafe"

  if [ -z "${no_hashes}" ]; then
    opts="${opts} --generate-hashes"
  fi

  if [ -n "${extras}" ]; then
    opts="${opts} ${extras}"
  fi

  echo "[compile] '${out}'"
  pip-compile \
    ${opts} \
    --output-file="${out}" \
    pyproject.toml
}

do_compile() {
      export CUSTOM_COMPILE_COMMAND="sh ${0} compile"
      echo "[action] Compiling requirements files from deps/*.in"
      echo
      ch_cwd

      pip_compile "${out_dev}" "${extras_dev}"

      pip_compile "${out_qa}" "${extras_qa}"

      pip_compile "${out_publish}" "${extras_publish}"

      pip_compile "${out_docker}"

      pip_compile "${out_no_hashes}" "${extras_dev}" "no_hashes"

      echo
      echo "Requirements files updated."
      echo "You should run pip-sync now :"
      echo
      echo "  pip-sync dev-requirements.txt"
      echo
}

pip_upgrade_all() {
  out=$1
  extras=$2
  no_hashes=$3

  opts="--upgrade --allow-unsafe"

  if [ -z "${no_hashes}" ]; then
    opts="${opts} --generate-hashes"
  fi

  if [ -n "${extras}" ]; then
    opts="${opts} ${extras}"
  fi

  echo "[upgrade] '${out}'"
  pip-compile \
    ${opts} \
    --output-file="${out}" \
    pyproject.toml
}

do_upgrade_all() {
      export CUSTOM_COMPILE_COMMAND="sh ${0} compile"
      echo "[action] Upgrading all dependencies to their latest version"
      echo
      ch_cwd

      pip_upgrade_all "${out_dev}" "${extras_dev}"

      pip_upgrade_all "${out_qa}" "${extras_qa}"

      pip_upgrade_all "${out_publish}" "${extras_publish}"

      pip_upgrade_all "${out_docker}"

      pip_upgrade_all "${out_no_hashes}" "${extras_no_hashes}" "no_hashes"

      echo
      echo "Dependencies upgraded and requirements files updated."
      echo "You should run pip-sync now :"
      echo
      echo "    pip-sync dev-requirements.txt"
      echo
}

pip_upgrade_package() {
  package=$1
  out=$2
  extras=$3
  no_hashes=$4

  opts="--upgrade-package ${package} --allow-unsafe"

  if [ -z "${no_hashes}" ]; then
    opts="${opts} --generate-hashes"
  fi

  if [ -n "${extras}" ]; then
    opts="${opts} ${extras}"
  fi

  echo "[upgrade package '${package}'] '${out}'"
  pip-compile \
    ${opts} \
    --output-file="${out}" \
    pyproject.toml
}

do_upgrade_package() {
      package="$1"
      export CUSTOM_COMPILE_COMMAND="sh ${0} compile"
      echo "[action] Upgrading '${package}'"
      echo
      ch_cwd

      pip_upgrade_package "${package}" "${out_dev}" "${extras_dev}"

      pip_upgrade_package "${package}" "${out_qa}" "${extras_qa}"

      pip_upgrade_package "${package}" "${out_publish}" "${extras_publish}"

      pip_upgrade_package "${package}" "${out_docker}"

      pip_upgrade_package "${package}" "${out_no_hashes}" "${extras_no_hashes}" "no_hashes"

      echo
      echo "Package '${package}' upgraded and requirements files updated."
      echo "You should run pip-sync now :"
      echo
      echo "    pip-sync dev-requirements.txt"
      echo
}

if [ -z "${VIRTUAL_ENV}" ] ; then
  failure "Virtual environment not activated. If you have not already create it, do it now with :

  python -m venv <path_to_venv>

Once you have a virtual environment for this project, activate it before running this script with :

  source <path_to_venv>/bin/activate
"
else
  echo "[venv]
peth: ${VIRTUAL_ENV}"
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
      if [ -n "${package}" ]; then
        do_upgrade_package "${package}"
      else
        do_upgrade_all
      fi
      exit 0
    ;;

  "compile")
      do_compile
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
