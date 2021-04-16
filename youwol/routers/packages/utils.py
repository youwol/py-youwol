import asyncio
import hashlib
import itertools
import json
import os
import shutil

from functools import reduce

from pathlib import Path
from typing import List, Dict, Union, Set
from collections import OrderedDict

from youwol.configuration.models_package import TargetPackage, InfoPackage
from youwol.configuration.youwol_configuration import YouwolConfiguration
from youwol.context import Context, Action, ActionStep
from youwol.routers.packages.models import (
    BuildStatus, TestStatus, CdnStatus, Package, TargetStatus,
    ActionScope, TargetId, InstallStatus,
    )

from youwol.utils_paths import matching_files, parse_json, copy_tree
from youwol.services.backs.cdn.utils import to_package_id
from youwol_utils import to_group_id, private_group_id
from youwol_utils.clients.treedb.treedb_utils import ensure_pathname

flatten = itertools.chain.from_iterable


def copy_node_module_folder(path: Path, package: Package, context: Context):

    config = context.config
    path.exists() and shutil.rmtree(path)

    if '/' in package.info.name and not path/package.info.name.split('/')[0]:
        os.mkdir(path/package.info.name.split('/')[0])

    copy_tree(source=config.pathsBook.store_node_module(package.info.name),
              destination=path)


def create_packages_cache_entry(
        package: Package,
        src_check_sums: Dict[TargetId, str],
        build_error: bool,
        context: Context
        ):

    paths_book = context.config.pathsBook
    if package.info.name not in src_check_sums:
        src_check_sums[package.info.name] = src_check_sum(package=package, context=context)
    data = parse_json(paths_book.packages_cache_path)
    fingerprint = None
    if package.info.name in data and 'cdn_fingerprint' in data[package.info.name]:
        fingerprint = data[package.info.name]['cdn_fingerprint']

    data[package.info.name] = {
        "src_md5_stamp": src_check_sums[package.info.name],
        "dependencies_md5_stamp": get_dependency_check_sum(package=package, src_check_sums=src_check_sums,
                                                           context=context),
        "cdn_fingerprint": fingerprint,
        "build_error": build_error
        }
    open(paths_book.packages_cache_path, 'w').write(json.dumps(data, indent=4))


def append_test_cache_entry(
        package: Package,
        src_check_sums: Dict[TargetId, str],
        returned_code: int,
        config: YouwolConfiguration
        ):

    paths_book = config.pathsBook
    data = parse_json(paths_book.packages_cache_path)
    data[package.info.name] = data[package.info.name] if package.info.name in data else {}

    data.get(package.info.name, {}).update({
        "test_md5_stamp": src_check_sums[package.info.name],
        "num_failed_tests": returned_code
        })

    open(paths_book.packages_cache_path, 'w').write(json.dumps(data, indent=4))


def md5_update_from_file(
        filename: Union[str, Path],
        current_hash):
    with open(str(filename), "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            current_hash.update(chunk)
    return current_hash


def sort_packages(
        packages: List[Package],
        sorted_packages: List[Package] = None
        ):
    if not packages:
        return sorted_packages
    sorted_packages = sorted_packages or []
    sorted_names = [k.info.name for k in sorted_packages]
    flags = [all(dep in sorted_names for dep in p.info.projectDependencies.keys()) for p in packages]
    return sort_packages(
        packages=[p for p, f in zip(packages, flags) if not f],
        sorted_packages=sorted_packages + [p for p, f in zip(packages, flags) if f])


async def get_all_packages(context: Context) -> List[Package]:

    # if 'packages' in context.config.cache:
    #    return context.config.cache['packages']

    config = context.config
    targets = list(flatten([(category, t) for t in targets]
                           for category, targets in config.userConfig.packages.targets.items()))

    def to_info(t: TargetPackage):
        path = t.folder / 'package.json'
        return InfoPackage(**parse_json(path))

    info_targets = [to_info(t) for _, t in targets]

    async def to_package(category: str, target: TargetPackage, info: InfoPackage):
        return Package(
            assetId=to_package_id(to_package_id(info.name)),
            pipeline=await config.userConfig.packages.pipeline(category, target, info, context.with_target(info.name)),
            target=target,
            info=info
            )

    packages = [await to_package(category, target, info) for (category, target), info in zip(targets, info_targets)]
    all_names = [p.info.name for p in packages]
    for p in packages:
        all_dependencies = {**p.info.peerDependencies, **p.info.dependencies, **p.info.devDependencies}
        p.info.projectDependencies = {k: v for k, v in all_dependencies.items() if k in all_names}

    context.config.cache['packages'] = sort_packages(packages)
    return context.config.cache['packages']


def src_check_sum(package: Package, context: Context):

    if not package.pipeline.build or not package.pipeline.build.checkSum:
        return None
    sha_hash = hashlib.md5()
    folder = package.target.folder
    paths = list(matching_files(folder, package.pipeline.build.checkSum))
    for path in sorted(paths, key=lambda p: str(p).lower()):
        sha_hash.update(str(path).encode())
        sha_hash = md5_update_from_file(path, sha_hash)
    sha_hash = sha_hash.hexdigest()
    return sha_hash


def get_dependencies_recursive(
        package: Package,
        all_packages: List[Package],
        acc: Set[TargetId]
        ) -> Set[TargetId]:

    def get_by_name(name: str):
        return next(p for p in all_packages if p.info.name == name)
    return acc\
        .union(set(package.info.projectDependencies))\
        .union(set(flatten([get_dependencies_recursive(get_by_name(t), all_packages, set())
                            for t in package.info.projectDependencies.keys()])))


def get_dependency_check_sum(
        package: Package,
        src_check_sums: Dict[TargetId, str],
        context: Context) -> str:

    sorted_dependencies = sorted(package.info.projectDependencies.keys())
    check_sum = reduce(lambda acc, e:
                       acc + (src_check_sums[e]
                              if e in src_check_sums
                              else src_check_sum(package=package, context=context)),
                       sorted_dependencies, "")
    return check_sum


async def install_status(
        package: Package,
        context: Context) \
        -> Union[InstallStatus, None]:

    if not package.pipeline.install or not package.pipeline.install.isInstalled:
        return None
    if package.pipeline.install.isInstalled(package, context):
        return InstallStatus.INSTALLED

    return InstallStatus.NOT_INSTALLED


def build_status_direct(
        package: Package,
        src_check_sums: Dict[TargetId, str],
        context: Context) \
        -> Union[BuildStatus, None]:

    config = context.config
    if not package.pipeline.build or not package.pipeline.build.run:
        return None

    cache = json.loads(open(config.pathsBook.packages_cache_path).read())

    if package.info.name not in cache:
        return BuildStatus.NEVER_BUILT

    if "src_md5_stamp" not in cache[package.info.name] \
            or cache[package.info.name]["src_md5_stamp"] != src_check_sums[package.info.name]:
        return BuildStatus.OUT_OF_DATE

    if "build_error" in cache[package.info.name] and cache[package.info.name]["build_error"]:
        return BuildStatus.RED

    return BuildStatus.SYNC


async def build_status_indirect(
        package: Package,
        src_check_sums: Dict[str, str],
        context: Context) -> BuildStatus:

    async def send_build_ws(status: BuildStatus):
        await context.debug(ActionStep.STATUS, status.name)
        return status
    config = context.config
    if not package.pipeline.build or not package.pipeline.build.run:
        return BuildStatus.NA

    direct_status = build_status_direct(package=package, src_check_sums=src_check_sums, context=context)

    if direct_status != BuildStatus.SYNC:
        return await send_build_ws(direct_status)

    check_sum_dependencies = get_dependency_check_sum(package=package, src_check_sums=src_check_sums, context=context)
    saved_check_sum = parse_json(config.pathsBook.packages_cache_path)[package.info.name]["dependencies_md5_stamp"]

    if check_sum_dependencies != saved_check_sum:
        return await send_build_ws(BuildStatus.INDIRECT_OUT_OF_DATE)

    return await send_build_ws(BuildStatus.SYNC)


async def test_status(
        package: Package,
        src_check_sums: Dict[TargetId, str],
        context: Context) -> TestStatus:

    async def send_test_ws(status: TestStatus):
        await context.debug(ActionStep.STATUS, status.name)
        return status
    config = context.config
    cache_file = parse_json(config.pathsBook.packages_cache_path)
    if package.info.name not in cache_file or "test_md5_stamp" not in cache_file[package.info.name]:
        return await send_test_ws(TestStatus.NO_ENTRY)

    build_status = build_status_indirect(package=package, src_check_sums=src_check_sums, context=context)

    if build_status == BuildStatus.OUT_OF_DATE:
        return await send_test_ws(TestStatus.OUT_OF_DATE)

    if build_status == BuildStatus.INDIRECT_OUT_OF_DATE:
        return await send_test_ws(TestStatus.INDIRECT_OUT_OF_DATE)

    if cache_file[package.info.name]["test_md5_stamp"] != src_check_sums[package.info.name]:
        return await send_test_ws(TestStatus.OUT_OF_DATE)

    if cache_file[package.info.name]["num_failed_tests"] > 0:
        return await send_test_ws(TestStatus.RED)

    return await send_test_ws(TestStatus.GREEN)


async def local_cdn_status(
        package: Package,
        src_check_sums: Dict[TargetId, str],
        context: Context) -> CdnStatus:

    if not package.pipeline.cdn:
        return CdnStatus.NA

    async def send_cdn_ws(status: CdnStatus):
        await context.debug(ActionStep.STATUS, status.name)
        return status

    config = context.config
    if build_status_direct(package, src_check_sums, context) != BuildStatus.SYNC:
        return await send_cdn_ws(CdnStatus.OUT_OF_DATE)

    cache = json.loads(open(config.pathsBook.packages_cache_path).read())

    if package.info.name not in cache:
        return await send_cdn_ws(CdnStatus.NOT_PUBLISHED)

    check_sum = ""
    zip_path = config.pathsBook.cdn_zip_path(package.info.name, package.info.version)
    if zip_path.exists():
        check_sum = md5_update_from_file(zip_path,  hashlib.md5()).hexdigest()

    if "cdn_fingerprint" in cache[package.info.name] and cache[package.info.name]["cdn_fingerprint"] == check_sum:
        return await send_cdn_ws(CdnStatus.SYNC)

    return await send_cdn_ws(CdnStatus.OUT_OF_DATE)


async def get_packages_status(context: Context) -> List[TargetStatus]:

    packages = await get_all_packages(context=context)

    if not packages:
        return []

    src_check_sums = {p.info.name: src_check_sum(p, context=context) for p in packages}

    all_install_status = await asyncio.gather(*[
        install_status(package=p,
                       context=context.with_target(p.info.name).with_action(Action.BUILD))
        for p in packages])

    all_build_status = await asyncio.gather(*[
        build_status_indirect(package=p,
                              src_check_sums=src_check_sums,
                              context=context.with_target(p.info.name).with_action(Action.BUILD))
        for p in packages])

    all_test_status = await asyncio.gather(*[
        test_status(package=p,
                    src_check_sums=src_check_sums,
                    context=context.with_target(p.info.name).with_action(Action.TEST))
        for p in packages])

    all_cdn_status = await asyncio.gather(*[
        local_cdn_status(package=p, src_check_sums=src_check_sums,
                         context=context.with_target(p.info.name).with_action(Action.CDN))
        for p in packages])

    return [TargetStatus(target=p,
                         src_check_sum=src_check_sums[p.info.name],
                         install_status=install,
                         build_status=build,
                         test_status=test,
                         cdn_status=cdn)
            for p, install, build, test, cdn in
            zip(packages, all_install_status, all_build_status, all_test_status, all_cdn_status)]


def extract_below_dependencies_recursive(
        packages: List[Package],
        target_name: TargetId,
        known: List[TargetId] = None
        ) -> List[TargetId]:
    known = known or []
    package = next((p for p in packages if p.info.name == target_name), None)
    if not package:
        raise Exception("module {} not found in project".format(target_name))

    dependencies = list(package.info.projectDependencies.keys())
    if all(d in known for d in dependencies):
        return list(OrderedDict.fromkeys(known + [package.info.name]))

    for dep in dependencies:
        known = list(OrderedDict.fromkeys(known + extract_below_dependencies_recursive(packages, dep, known)))

    return known + [package.info.name]


def extract_above_dependencies_recursive(
        packages: List[Package],
        target_name: str
        ) -> Set[TargetId]:

    return {p.info.name for p in packages if target_name in p.info.projectDependencies.keys()}


def preparation(context: Context):

    config = context.config
    paths_book = config.pathsBook

    if not paths_book.js_modules_store_path.exists():
        os.mkdir(paths_book.js_modules_store_path)

    if not paths_book.packages_cache_path:
        open(paths_book.packages_cache_path, "w").write(json.dumps({}))

    if not paths_book.store_node_modules.exists():
        os.mkdir(paths_book.store_node_modules)


async def select_packages(
        package_name: str,
        action: Action,
        scope: ActionScope,
        context: Context
        ) -> (List[Package], List[Package], List[Package], List[Package]):

    packages = await get_all_packages(context=context)
    targets = packages
    targets_dict = {t.info.name: t for t in targets}

    if scope == ActionScope.ALL_BELOW:
        scope_dependencies = extract_above_dependencies_recursive(packages=packages, target_name=package_name)
        targets = [t for t in packages if t.info.name in scope_dependencies or t.info.name == package_name]

    if scope == ActionScope.ALL_ABOVE:
        scope_dependencies = extract_below_dependencies_recursive(packages=packages, target_name=package_name)
        targets = [targets_dict[name] for name in scope_dependencies]

    if scope == ActionScope.TARGET_ONLY:
        targets = [p for p in packages if p.info.name == package_name]

    preparation(context)
    all_status = await get_packages_status(context=context)
    status_dict = {status.target.info.name: status for status in all_status}
    targets_status = [status_dict[t.info.name] for t in targets]

    to_publish = [status.target for status in targets_status
                  if status.cdn_status in [CdnStatus.OUT_OF_DATE, CdnStatus.NOT_PUBLISHED]]

    to_rebuild = [status.target for status in targets_status
                  if status.build_status != BuildStatus.SYNC
                  and status.build_status != BuildStatus.NA
                  and status.target.pipeline.build.run]

    to_test = [status.target for status in targets_status if status.test_status != TestStatus.GREEN]

    if action == Action.BUILD:
        to_test = []
        to_publish = []

    if action == Action.TEST:
        to_rebuild = []
        to_publish = []

    if action == Action.CDN:
        to_rebuild = []
        to_test = []

    return to_rebuild, to_test, to_publish, packages


async def ensure_default_publish_location(context: Context):

    default_path = context.config.userConfig.general.defaultPublishLocation
    user = await context.config.userConfig.general.get_user_info(context)
    parts = default_path.split('/')
    group_id = private_group_id({"sub": user.id}) if parts[0] == 'private' else to_group_id(parts[0])
    drive_name, folders = parts[1], parts[2:]
    treedb_client = context.config.localClients.treedb_client
    folder_id = await ensure_pathname(group_id=group_id, drive_name=drive_name, folders_name=folders,
                                      treedb_client=treedb_client, headers={})
    return folder_id
