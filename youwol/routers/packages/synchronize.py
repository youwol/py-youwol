import asyncio
import hashlib
import json
import os
import shutil
import zipfile
from pathlib import Path
from typing import List, Dict, cast, IO

from aiohttp import FormData
from fastapi import HTTPException

from youwol.configuration.models_base import FileListing
from youwol.context import Context, ActionException, Action, ActionStep
from youwol.routers.packages.messages import PACKAGE_JSON_MISSING_CDN
from youwol.routers.packages.models import Package, TargetId
from youwol.routers.packages.utils import (
    src_check_sum, get_dependencies_recursive,
    create_packages_cache_entry, build_status_indirect, append_test_cache_entry, md5_update_from_file, test_status,
    local_cdn_status, ensure_default_publish_location, copy_node_module_folder,
    )
from youwol.utils_paths import copy_tree, matching_files, copy_file, parse_json, write_json
from youwol.utils_misc import merge, execute_cmd_or_block
from youwol.services.backs.cdn.configurations import get_configuration
from youwol.services.backs.cdn.utils import publish_package, to_package_id
from youwol_utils import YouWolException, exception_message


def ensure_dependencies(
        package: Package,
        all_packages: List[Package],
        src_check_sums: Dict[TargetId, str],
        context: Context):

    dependencies = get_dependencies_recursive(package=package, all_packages=all_packages, acc=set())
    config = context.config
    missing_dependencies = [d for d in dependencies if not config.pathsBook.store_node_module(d).exists()]

    if missing_dependencies:
        create_packages_cache_entry(
            package=package,
            src_check_sums=src_check_sums,
            build_error=True,
            context=context)
        raise ActionException(
            context.action,
            f"Following dependencies of {package.info.name} do not exists in the youwol module's store" +
            ": {str(missing_dependencies)}. Did you built them?")

    return dependencies


async def prepare_build(
        package: Package,
        all_packages: List[Package],
        src_check_sums: Dict[TargetId, str],
        context: Context
        ):
    config = context.config
    dependencies = ensure_dependencies(package=package, all_packages=all_packages, src_check_sums=src_check_sums,
                                       context=context)

    store_node_module_path = config.pathsBook.store_node_module(package.info.name)
    if store_node_module_path.exists():
        shutil.rmtree(store_node_module_path)

    if not dependencies:
        return True

    if not config.pathsBook.node_modules(package.target.folder):
        os.mkdir(config.pathsBook.node_modules(package.target.folder))

    for dependency in dependencies:

        node_modules_folder = config.pathsBook.node_module_dependency(package.target.folder, dependency)
        node_modules_folder.exists() and shutil.rmtree(node_modules_folder)

        if package.pipeline.build and package.pipeline.build.sourceNodeModules:
            node_modules_folder = package.pipeline.build.sourceNodeModules.parent
            node_modules_folder = config.pathsBook.node_module_dependency(node_modules_folder, dependency)
            node_modules_folder.exists() and shutil.rmtree(node_modules_folder)

        if '/' in dependency and not node_modules_folder / dependency.split('/')[0]:
            os.mkdir(node_modules_folder / dependency.split('/')[0])

        copy_tree(source=config.pathsBook.store_node_module(dependency),
                  destination=node_modules_folder)

    return True


async def prepare_test(
        package: Package,
        all_packages: List[Package],
        src_check_sums: Dict[TargetId, str],
        context: Context):

    ensure_dependencies(package=package, all_packages=all_packages, src_check_sums=src_check_sums, context=context)


async def build_target(
        package: Package,
        src_check_sums: Dict[TargetId, str],
        context: Context
        ) -> bool:

    folder = package.target.folder
    p = await asyncio.create_subprocess_shell(
        cmd=f"(cd  {str(folder)} && {package.pipeline.build.run})",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        shell=True)

    async for f in merge(p.stdout, p.stderr):
        await context.info(ActionStep.RUNNING, f.decode('utf-8'))

    await p.communicate()

    return_code = p.returncode

    if return_code > 0:
        create_packages_cache_entry(
            package=package,
            src_check_sums=src_check_sums,
            build_error=True,
            context=context)
        raise ActionException(
            Action.BUILD,
            f"Build failed at '{package.pipeline.build.run}'")

    await make_package(
        package=package,
        src_check_sums=src_check_sums,
        context=context)

    return True


async def make_package(
        package: Package,
        context: Context,
        src_check_sums: Dict[TargetId, str] = None):

    src_check_sums = src_check_sums or {}
    config = context.config

    folder_path = package.target.folder
    store_node_module_path = config.pathsBook.store_node_module(package.info.name)
    cdn_zip_path = config.pathsBook.cdn_zip_path(package.info.name, package.info.version)

    if store_node_module_path.exists():
        shutil.rmtree(store_node_module_path)

    npm_min_includes = {"package.json", "README.*", "CHANGES.*", "CHANGELOG.*", "HISTORY.*", "LICENCE.*", "LICENSE.*",
                        "NOTICE.*", package.info.main}
    npm_includes = set(package.info.files).union(npm_min_includes) if package.info.files else {"*", "**/*"}
    npm_min_exclude = {'.git', '.gitignore', 'CVS', '.svn', 'hg', 'lock-wscript', '.wafpickle-N', '.DS_Store',
                       'npm-debug.log', '.npmrc', 'node_modules', 'config.gypi', 'package-lock.json'}

    if(package.target.folder / '.npmignore').exists():
        rules = set((package.target.folder / '.npmignore').read_text().split('\n'))
        npm_min_exclude = npm_min_exclude.union(rules)

    npm_files = matching_files(
        folder_path,
        FileListing(
            include=list(npm_includes),
            ignore=list(npm_min_exclude)
            )
        )
    for f in npm_files:
        copy_file(source=f,
                  destination=store_node_module_path / f.relative_to(folder_path),
                  create_folders=True)

    packaged_files = npm_files
    if package.pipeline.cdn.targets:
        packaged_files = matching_files(
            store_node_module_path,
            package.pipeline.cdn.targets
            )
    if not any(str(p.relative_to(store_node_module_path)) == "package.json" for p in packaged_files):
        raise ActionException(context.action, PACKAGE_JSON_MISSING_CDN)

    if package.pipeline.build.package_json:
        original = parse_json(store_node_module_path / "package.json")
        updated = package.pipeline.build.package_json(original, package, context)
        write_json(updated, store_node_module_path / "package.json")

    zipper = zipfile.ZipFile(cdn_zip_path, 'w', zipfile.ZIP_DEFLATED)
    for f in packaged_files:
        zipper.write(filename=f, arcname=f.relative_to(store_node_module_path))
    await context.info(step=ActionStep.STATUS, content="CDN zip prepared",
                       json={"files": [str(f) for f in packaged_files]})
    zipper.close()

    create_packages_cache_entry(package=package, src_check_sums=src_check_sums, build_error=False, context=context)

    sha_hash = hashlib.md5()
    check_sum = md5_update_from_file(cdn_zip_path, sha_hash).hexdigest()

    # if there are destinations node_modules => we copy the built package into them
    if package.pipeline.build and package.pipeline.build.destinationNodeModules:
        for destination in package.pipeline.build.destinationNodeModules:
            node_modules_folder = config.pathsBook.node_module_dependency(Path(destination).parent, package.info.name)
            copy_node_module_folder(node_modules_folder, package, context)

    await context.info(ActionStep.PACKAGING, f"checksum cdn: {check_sum}")


async def test_target(
        package: Package,
        src_check_sums: Dict[TargetId, str],
        context: Context) -> bool:

    if not package.pipeline.test:
        return False

    return_code = await execute_cmd_or_block(
        cmd=package.pipeline.test.run,
        asset=package,
        context=context
        )

    append_test_cache_entry(package=package, src_check_sums=src_check_sums, returned_code=return_code,
                            config=context.config)

    return return_code == 0


async def publish_local_cdn(
        package: Package,
        context: Context
        ):
    config = context.config
    if package.pipeline.build.run is None:
        return
    path_cache = config.pathsBook.packages_cache_path
    data = parse_json(path_cache)

    cdn_zip_path = config.pathsBook.cdn_zip_path(package.info.name, package.info.version)

    try:
        zip_file = zipfile.ZipFile(cdn_zip_path)
    except Exception as e:
        await context.error(
            step=ActionStep.RUNNING,
            content=f"Module ${package.info.name}: the cdn zip file ({cdn_zip_path}) is not found. " +
                    "You can try re-building your package",
            json={"zip_path": str(cdn_zip_path)}
            )
        raise e
    try:
        zip_file.extract(package.info.main)
    except Exception as e:
        await context.error(
            step=ActionStep.RUNNING,
            content=f"Module {package.info.name}: the entry point file is not found. " +
                    f"Does the file '{package.info.main}' exists?",
            json={"zip_path": str(cdn_zip_path), "expected file": package.info.main}
            )
        raise e
    assets_gateway_client = context.config.localClients.assets_gateway_client
    folder_id = await ensure_default_publish_location(context)
    try:
        asset = await assets_gateway_client.get_asset_metadata(asset_id=to_package_id(to_package_id(package.info.name)))
    except HTTPException:
        asset = None

    try:
        with open(cdn_zip_path, 'rb') as file:
            if asset is None:
                form = FormData()
                form.add_field('file', file)
                form.add_field('content_encoding', 'identity')
                resp = await assets_gateway_client.put_asset_with_raw(
                    kind='package',
                    folder_id=folder_id,
                    data=form
                    )
            else:
                resp = await publish_package(
                    file=cast(IO, file),
                    filename=cdn_zip_path.name,
                    content_encoding='identity',
                    configuration=await get_configuration(), headers={}
                    )
    except Exception as e:
        await context.error(
            step=ActionStep.RUNNING,
            content=f"Error while publishing the package to the CDN: {exception_message(e)}",
            json={"zip_path": str(cdn_zip_path)}
            )
        raise e
    sha_hash = hashlib.md5()
    check_sum = md5_update_from_file(cdn_zip_path, sha_hash).hexdigest()
    data[package.info.name]['cdn_fingerprint'] = check_sum
    open(path_cache, 'w').write(json.dumps(data, indent=4))
    return resp


async def synchronize(
        build_targets: List[Package],
        test_targets: List[Package],
        cdn_targets: List[Package],
        all_targets: List[Package],
        context: Context):

    src_check_sums = {t.info.name: src_check_sum(package=t, context=context) for t in all_targets}

    async def build_block(p: Package, prepare: bool):
        async with context.with_target(p.info.name).start(Action.BUILD) as _ctx:
            if prepare:
                await prepare_build(package=package, all_packages=all_targets,
                                    src_check_sums=src_check_sums, context=_ctx)
            await build_target(package=p, src_check_sums=src_check_sums, context=_ctx)
            await build_status_indirect(package=p, src_check_sums=src_check_sums, context=_ctx)
            return True

    async def test_block(p: Package, prepare: bool):
        async with context.with_target(p.info.name).start(Action.TEST) as _ctx:
            if prepare:
                await prepare_test(package=package, all_packages=all_targets,
                                   src_check_sums=src_check_sums, context=_ctx)
            return_code = await test_target(package=p, src_check_sums=src_check_sums, context=_ctx)
            await test_status(package=p, src_check_sums=src_check_sums, context=_ctx)
            return return_code == 0

    async def cdn_block(p: Package):
        async with context.with_target(p.info.name).start(Action.CDN) as _ctx:

            await publish_local_cdn(package=p, context=_ctx)
            await local_cdn_status(package=p, src_check_sums=src_check_sums, context=_ctx)

    for package in build_targets:

        if package.pipeline.build.run is None:
            continue

        build_ok = await build_block(package, prepare=True)

        if package in test_targets:
            build_ok and await test_block(package, prepare=False)
            test_targets = [t for t in test_targets if t != package]

        if package in cdn_targets:
            build_ok and await cdn_block(package)
            cdn_targets = [t for t in cdn_targets if t != package]

    for package in test_targets:
        test_ok = await test_block(package, prepare=True)
        if package in cdn_targets:
            test_ok and await cdn_block(package)

    for package in cdn_targets:
        await cdn_block(package)
