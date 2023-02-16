import subprocess
import sys

import tomli
import tomli_w
from packaging import version

PYPROJECT_TOML = "pyproject.toml"


def debug(msg: str):
    sys.stderr.write(msg + "\n")


def write_version(v: str):
    pyproject_dict = None
    with open(PYPROJECT_TOML, "rb") as f_r:
        pyproject_dict = tomli.load(f_r)

    with open(PYPROJECT_TOML, "wb") as f_w:
        pyproject_dict.get("project")["version"] = v
        tomli_w.dump(pyproject_dict, f_w)
        debug(f"written : {v}")

    debug(f"canonical version : {get_current_version()}")


def git_commit(msg: str):
    subprocess.run("git add pyproject.toml", shell=True)
    subprocess.run(f"git commit -m '{msg}'", shell=True)


def get_current_version():
    with open("pyproject.toml", "rb") as f:
        pyproject_dict = tomli.load(f)
        v = version.parse(pyproject_dict.get("project").get("version"))
        # if isinstance(v, version.LegacyVersion):
        #     raise ValueError(f"{v} is a legacy version string")
        if v.is_postrelease:
            raise ValueError(f"{v} is a post version")
        return v


def get_target_version():
    if len(sys.argv) != 3:
        raise RuntimeError("Missing param target version")
    arg = sys.argv[2]
    parsed_version = version.parse(arg)
    # if isinstance(parsed_version, version.LegacyVersion):
    #     raise ValueError(f"{parsed_version} is a legacy version string")
    if parsed_version.is_prerelease or parsed_version.is_devrelease or parsed_version.is_postrelease:
        raise ValueError(f"Version is not final : {arg}")
    return parsed_version


def cmd_prepare_release_candidate():
    check()
    target_version = get_target_version()
    if target_version <= current_version:
        raise ValueError(f"target version {target_version} is not after current version {current_version}")

    major = target_version.major
    minor = target_version.minor
    micro = target_version.micro
    rc = 'rc'
    if current_version.pre is not None:
        rc_nb = int(current_version.pre[1])
        if rc_nb > 0:
            rc = 'rc' + str(rc_nb)

    target = f"{major}.{minor}.{micro}{rc}"
    write_version(target)
    git_commit(f"🔖 release candidate {target}")


def cmd_restore_dev():
    if current_version.is_devrelease:
        raise ValueError(f"{current_version} is already a dev version")
    major = current_version.major
    minor = current_version.minor
    micro = current_version.micro
    rc = ''

    if current_version.is_prerelease:
        rc_nb = int(current_version.pre[1]) + 1
        rc = 'rc' + str(rc_nb)
    else:
        micro = str(int(micro) + 1)

    next_version = f"{major}.{minor}.{micro}{rc}"
    dev_version = f"{next_version}.dev"
    write_version(dev_version)
    git_commit(f"🔖 prepare for next version {next_version}")


def cmd_prepare_final():
    check()
    if current_version.pre is None:
        raise ValueError(f"{current_version} is not a release candidate")
    final_version = current_version.base_version
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


def check():
    if not current_version.is_devrelease:
        raise ValueError(f"{current_version} is not a dev version")


cmds = {'prepare_rc': cmd_prepare_release_candidate, 'restore_dev': cmd_restore_dev, 'prepare_final': cmd_prepare_final,
        'get_final': cmd_get_final_version, 'get_current': cmd_get_current, 'check': cmd_check}

if __name__ == '__main__':
    current_version = get_current_version()
    debug(f"current version : {current_version}")

    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        fn = cmds.get(cmd)
        if fn is None:
            raise ValueError(f"Unknown command {sys.argv[1]}")
        debug(f"command : {cmd}")
        fn()
    else:
        check()
