# standard library
import json
import subprocess
import sys

from datetime import datetime

# third parties
import tomlkit

from packaging import version

PYPROJECT_TOML = "pyproject.toml"
CHANGELOG_MD = "CHANGELOG.md"
CHANGELOG_HEADER_LINE = 17
NO_CHANGE_LINE = "_no change_"
PYTHON_VERSION_PREFIX = "3."
CLASSIFIER_PYTHON_VERSION = f"Programming Language :: Python :: {PYTHON_VERSION_PREFIX}"


def get_current_version():
    with open(PYPROJECT_TOML, encoding="utf8") as f:
        pyproject_dict = tomlkit.load(f)
        v = version.parse(pyproject_dict.get("project").get("version"))
        if v.is_postrelease:
            raise ValueError(f"{v} is a post version")
        return v


current_version = get_current_version()

messages = []


def debug(msg: str):
    messages.append(msg)
    sys.stderr.write(msg + "\n")


def write_version(v: str):
    pyproject_dict = None
    with open(PYPROJECT_TOML, encoding="utf8") as f_r:
        pyproject_dict = tomlkit.load(f_r)

    with open(PYPROJECT_TOML, "w", encoding="utf8") as f_w:
        pyproject_dict.get("project")["version"] = v
        tomlkit.dump(pyproject_dict, f_w)
        debug(f"final_version_string='{v}'")

    debug(f"final_version_canonical='{get_current_version()}'")


def set_changelog_section_header(v: str):
    with open(CHANGELOG_MD, encoding="utf8") as c_r:
        lines = c_r.readlines()
    release_date = datetime.today().strftime("%Y-%m-%d")
    lines[CHANGELOG_HEADER_LINE] = f"## [{v}] − {release_date}\n"
    with open(CHANGELOG_MD, "w", encoding="utf8") as c_w:
        c_w.writelines(lines)


def add_changelog_section_header(v: str, squash=False):
    with open(CHANGELOG_MD, encoding="utf8") as c_r:
        input_lines = c_r.readlines()

    output_lines = input_lines[:CHANGELOG_HEADER_LINE] + [
        f"## [{v}] − Unreleased\n" + "\n"
    ]

    pos_after = CHANGELOG_HEADER_LINE
    if input_lines[CHANGELOG_HEADER_LINE + 2].startswith("## "):
        pos_after = CHANGELOG_HEADER_LINE + 2
        if not squash:
            debug(f"no_change_section='{input_lines[CHANGELOG_HEADER_LINE].strip()}'")
            output_lines.extend(
                [
                    f"{input_lines[CHANGELOG_HEADER_LINE]}\n"
                    + f"{NO_CHANGE_LINE}\n"
                    + "\n"
                ]
            )
        else:
            debug(
                f"squashed_empty_section='{input_lines[CHANGELOG_HEADER_LINE].strip()}'"
            )

    output_lines.extend(input_lines[pos_after:])

    with open(CHANGELOG_MD, "w", encoding="utf8") as c_w:
        c_w.writelines(output_lines)


def git_commit(msg: str):
    debug_messages = "\n".join(messages)
    commit_msg = f"{msg}\n\nversion_management.py debug logging:\n{debug_messages}"
    subprocess.run(f"git add {PYPROJECT_TOML}", shell=True, check=True)
    subprocess.run(f"git add {CHANGELOG_MD}", shell=True, check=True)
    subprocess.run(f'git commit -m "{commit_msg}"', shell=True, check=True)


def get_classifiers_python_version() -> list[str]:
    with open(PYPROJECT_TOML, encoding="utf8") as fd:
        metadata = tomlkit.load(fd)
        return [
            f"{PYTHON_VERSION_PREFIX}{classifier[len(CLASSIFIER_PYTHON_VERSION):]}"
            for classifier in metadata["project"]["classifiers"]
            if classifier.startswith(CLASSIFIER_PYTHON_VERSION)
        ]


def get_target_version():
    arg = sys.argv[2] if len(sys.argv) == 3 else current_version.base_version
    parsed_version = version.parse(arg)
    if (
        parsed_version.is_prerelease
        or parsed_version.is_devrelease
        or parsed_version.is_postrelease
    ):
        raise ValueError(f"Version is not final : {arg}")
    return parsed_version


def cmd_prepare_release_candidate():
    check()
    target_version = get_target_version()
    if target_version <= current_version:
        raise ValueError(
            f"target version {target_version} is not after current version {current_version}"
        )

    major = target_version.major
    minor = target_version.minor
    micro = target_version.micro
    rc = "rc"
    if (
        current_version.pre is not None
        and target_version.base_version == current_version.base_version
    ):
        rc_nb = int(current_version.pre[1])
        if rc_nb > 0:
            rc = "rc" + str(rc_nb)

    target = f"{major}.{minor}.{micro}{rc}"
    set_changelog_section_header(target)
    write_version(target)
    git_commit(f"🔖 release candidate {target}")


def cmd_restore_dev():
    if current_version.is_devrelease:
        raise ValueError(f"{current_version} is already a dev version")
    major = current_version.major
    minor = current_version.minor
    micro = current_version.micro
    rc = ""

    if current_version.is_prerelease:
        rc_nb = int(current_version.pre[1]) + 1
        rc = "rc" + str(rc_nb)
    else:
        micro = str(int(micro) + 1)

    next_version = f"{major}.{minor}.{micro}{rc}"
    dev_version = f"{next_version}.dev"
    add_changelog_section_header(dev_version)
    write_version(dev_version)
    git_commit(f"🔖 prepare for next version {next_version}")


def cmd_next_dev():
    if not current_version.is_devrelease:
        raise ValueError(f"{current_version} is not a dev version")
    major = current_version.major
    minor = current_version.minor
    micro = current_version.micro

    micro = str(int(micro) + 1)

    next_version = f"{major}.{minor}.{micro}"
    dev_version = f"{next_version}.dev"
    add_changelog_section_header(dev_version)
    write_version(dev_version)
    git_commit(f"🔖 prepare for next version {next_version}")


def cmd_prepare_final():
    check()
    if current_version.pre is None:
        raise ValueError(f"{current_version} is not a release candidate")
    final_version = current_version.base_version
    set_changelog_section_header(final_version)
    write_version(final_version)
    git_commit(f"🔖 release {final_version}")


def cmd_get_final_version():
    check()
    print(current_version.base_version)


def cmd_get_current():
    print(current_version)


def cmd_check():
    check()
    if len(sys.argv) >= 3:
        parsed_version = version.parse(sys.argv[2])
        if parsed_version > current_version:
            raise ValueError(f"{current_version} is before {parsed_version}")


def cmd_python_versions():
    check()
    result = json.dumps(get_classifiers_python_version())
    print(result)


def check():
    if not current_version.is_devrelease:
        raise ValueError(f"{current_version} is not a dev version")


cmds = {
    "next_dev": cmd_next_dev,
    "prepare_rc": cmd_prepare_release_candidate,
    "restore_dev": cmd_restore_dev,
    "prepare_final": cmd_prepare_final,
    "get_final": cmd_get_final_version,
    "get_current": cmd_get_current,
    "check": cmd_check,
    "python_versions": cmd_python_versions,
}


if __name__ == "__main__":
    debug(f"original_version='{current_version}'")

    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        fn = cmds.get(cmd)
        if fn is None:
            raise ValueError(f"Unknown command {sys.argv[1]}")
        debug(f"command='{cmd}'")
        if len(sys.argv) > 2:
            debug(f"argument='{sys.argv[2]}'")
        fn()
    else:
        check()
