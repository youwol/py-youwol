# standard library
import asyncio
import itertools

# typing
from typing import Callable, Dict, List, Tuple, Union

# third parties
from fastapi import HTTPException
from pydantic import BaseModel
from semantic_version import NpmSpec, Version

# Youwol backends
from youwol.backends.cdn.utils import (
    Configuration,
    Constants,
    get_version_number_str,
    list_versions,
    to_package_id,
)
from youwol.backends.cdn.utils_indexing import get_version_number

# Youwol utilities
from youwol.utils import CircularDependencies, DependenciesError
from youwol.utils.context import Context
from youwol.utils.http_clients.cdn_backend import (
    LibraryQuery,
    LibraryResolved,
    ListVersionsResponse,
    Release,
    exportedSymbols,
    get_api_key,
)

ExportedKey = str
QueryKey = str
LibName = str


class ResolvedQuery(BaseModel):
    name: str
    query: str
    version: str
    exportedSymbol: str
    parent: LibraryResolved


class LibraryQueryWithParent(LibraryQuery):
    parent: LibraryResolved


class LibraryException(HTTPException):
    library: LibraryQueryWithParent

    def __init__(self, library: LibraryQueryWithParent, **kwargs):
        HTTPException.__init__(
            self,
            status_code=500,
            detail=f"Error while processing library {library.name} not found",
            **kwargs,
        )
        self.library = library


class LibraryNotFound(HTTPException):
    library: LibraryQueryWithParent

    def __init__(self, library: LibraryQueryWithParent, **kwargs):
        HTTPException.__init__(
            self, status_code=404, detail=f"Library {library.name} not found", **kwargs
        )
        self.library = library


def get_query_key(lib: LibraryQuery) -> str:
    return f"{lib.name}#{lib.version}"


def get_full_exported_symbol(name: str, version: Union[str, Version]):
    api_key = get_api_key(version)
    exported_name = exportedSymbols[name] if name in exportedSymbols else name
    return f"{exported_name}_APIv{api_key}"


async def loading_graph(
    remaining: List[LibraryResolved],
    items_dict: Dict[ExportedKey, Tuple[str, str]],
    resolutions_dict: Dict[QueryKey, ResolvedQuery],
    context: Context,
):
    def cached_api_key(lib: LibraryQuery) -> str:
        return resolutions_dict[get_query_key(lib)].exportedSymbol

    async with context.start(action="loading_graph") as ctx:  # type: Context
        remaining_keys = [d.full_exported_symbol() for d in remaining]
        download_keys = [k for k in items_dict.keys() if k not in remaining_keys]

        dependencies = {
            d.full_exported_symbol(): [
                cached_api_key(dependency) in download_keys
                for dependency in d.dependencies
            ]
            for d in remaining
        }

        await ctx.info(text="Requested libraries", data=dependencies)
        fulfilled_libs = [
            key
            for key, dependencies_available in dependencies.items()
            if all(dependencies_available)
        ]
        await ctx.info(
            text="Library to download", data={"fulfilledLibs": fulfilled_libs}
        )
        new_remaining = [
            p for p in remaining if p.full_exported_symbol() not in fulfilled_libs
        ]

        await ctx.info(
            text="New remaining dependencies",
            data={
                "new_remaining": [lib.full_exported_symbol() for lib in new_remaining]
            },
        )

        if not new_remaining:
            response = [[items_dict[a] for a in fulfilled_libs]]
            await ctx.info("Loading-graph final step", data={"response": response})
            return response

        if len(new_remaining) == len(remaining):
            names_dict = {
                d.full_exported_symbol(): f"{d.name}#{d.version}" for d in remaining
            }
            dependencies_dict = {
                d.full_exported_symbol(): d.dependencies for d in remaining
            }
            not_founds = {
                names_dict[pack]: [
                    dependencies_dict[pack][i].dict()
                    for i, found in enumerate(founds)
                    if not found
                ]
                for pack, founds in dependencies.items()
            }
            await ctx.error(
                text="Can not resolve dependency(ies)",
                data={"newRemaining": new_remaining, "oldRemaining": remaining},
            )
            raise CircularDependencies(
                context="Loading graph resolution stuck", packages=not_founds
            )
        next_round = await loading_graph(
            remaining=new_remaining,
            items_dict=items_dict,
            resolutions_dict=resolutions_dict,
            context=ctx,
        )
        response = [[items_dict[a] for a in fulfilled_libs]] + next_round
        await ctx.info("Loading-graph retrieved", data={"response": response})
        return response


async def list_all_versions_with_cache(
    library: LibraryQueryWithParent,
    extra_index: List[LibraryResolved],
    versions_cache: Dict[str, List[str]],
    configuration: Configuration,
    context: Context,
):
    if library.name in versions_cache:
        await context.info(text=f"Retrieved versions from cache {library.name}")
        return versions_cache[library.name]

    extra_elements = [lib for lib in extra_index if lib.name == library.name]

    try:
        versions_resp = await list_versions(
            name=library.name,
            context=context,
            max_results=1000,
            configuration=configuration,
        )
        extra_libs = [
            lib for lib in extra_elements if lib.version not in versions_resp.versions
        ]
        versions = sorted(
            [*versions_resp.versions, *[lib.version for lib in extra_libs]]
        )
        versions.reverse()
        versions_resp = ListVersionsResponse(
            name=versions_resp.name,
            id=versions_resp.id,
            namespace=versions_resp.namespace,
            versions=versions,
            releases=[
                *versions_resp.releases,
                *[
                    Release(
                        fingerprint=lib.fingerprint,
                        version=lib.version,
                        version_number=get_version_number(lib.version),
                    )
                    for lib in extra_libs
                ],
            ],
        )
    except HTTPException as e:
        if e.status_code == 404 and not extra_elements:
            raise LibraryNotFound(library=library)

        versions_resp = ListVersionsResponse(
            name=library.name,
            id=to_package_id(library.name),
            namespace="" if "/" not in library.name else library.name.split("/")[0],
            versions=[lib.version for lib in extra_elements],
            releases=[
                Release(
                    fingerprint=lib.fingerprint,
                    version=lib.version,
                    version_number=get_version_number(lib.version),
                )
                for lib in extra_elements
            ],
        )

    versions_cache[library.name] = versions_resp.versions
    return versions_cache[library.name]


async def resolve_version(
    dependency: LibraryQueryWithParent,
    using: Dict[str, str],
    extra_index: List[LibraryResolved],
    versions_cache: Dict[str, List[str]],
    configuration: Configuration,
    context: Context,
) -> ResolvedQuery:
    async with context.start(
        action="resolve_version", with_attributes={"library": dependency.name}
    ) as ctx:  # type: Context
        name = dependency.name
        version = (
            using[dependency.name] if dependency.name in using else dependency.version
        )
        base = version.split("-")[0].replace("x", "*").replace("latest", "*")
        pre_release = "-".join(version.split("-")[1:])
        version_spec = base if len(version.split("-")) == 1 else f"{base}-{pre_release}"
        selector = NpmSpec(version_spec)
        fixed = not any(c in base for c in [">", "<", "*", "^", "~"])
        try:
            versions = await list_all_versions_with_cache(
                library=dependency,
                extra_index=extra_index,
                versions_cache=versions_cache,
                configuration=configuration,
                context=ctx,
            )
        except HTTPException as e:
            if e.status_code == 404:
                raise LibraryNotFound(library=dependency)
            raise LibraryException(library=dependency)

        if fixed:
            version = next((v for v in versions if v == version), None)
        else:
            await ctx.info(f"Got {len(versions)} versions")
            version = next(
                selector.filter(Version(v.replace("-wip", "")) for v in versions), None
            )

        if not version:
            raise LibraryNotFound(library=dependency)

        if not fixed:
            if str(version) not in versions and f"{version}-wip" in versions:
                await ctx.info(f"{version} not available => use {version}-wip")
                version = Version(f"{version}-wip")
            elif str(version) not in versions and f"{version}-wip" not in versions:
                raise LibraryNotFound(library=dependency)
            await ctx.info(
                text=f"Use latest compatible version of {name}#{dependency.version} : {version}"
            )

        await ctx.info(f"Version resolved to {version}")
        api_key = get_full_exported_symbol(name, version)
        return ResolvedQuery(
            name=dependency.name,
            query=dependency.version,
            version=str(version),
            exportedSymbol=api_key,
            parent=dependency.parent,
        )


async def resolve_dependencies_recursive(
    from_libraries: List[LibraryResolved],
    using: Dict[LibName, str],
    extra_index: List[LibraryResolved],
    resolutions_cache: Dict[QueryKey, ResolvedQuery],
    versions_cache: Dict[LibName, List[str]],
    full_data_cache: Dict[ExportedKey, LibraryResolved],
    configuration: Configuration,
    context: Context,
) -> List[LibraryResolved]:
    async with context.start(
        action="resolve_dependencies_recursive"
    ) as ctx:  # type: Context
        resolved_versions = await resolve_dependencies_version_queries(
            from_libraries=from_libraries,
            using=using,
            extra_index=extra_index,
            resolutions_cache=resolutions_cache,
            versions_cache=versions_cache,
            configuration=configuration,
            context=ctx,
        )
        await ctx.info(
            text="Required dependencies' versions resolved",
            data={"resolved_versions": resolved_versions},
        )

        missing_data_versions = {
            lib.exportedSymbol: lib
            for lib in resolved_versions
            if lib.exportedSymbol not in full_data_cache
        }

        if not missing_data_versions:
            await ctx.info(text="No more dependencies to resolve :)")
            return from_libraries

        resolved_dependencies = await fetch_dependencies_data(
            missing_data_versions=missing_data_versions,
            extra_index=extra_index,
            full_data_cache=full_data_cache,
            configuration=configuration,
            context=ctx,
        )

        return [
            *from_libraries,
            *await resolve_dependencies_recursive(
                from_libraries=resolved_dependencies,
                using=using,
                extra_index=extra_index,
                resolutions_cache=resolutions_cache,
                full_data_cache=full_data_cache,
                versions_cache=versions_cache,
                configuration=configuration,
                context=ctx,
            ),
        ]


async def resolve_dependencies_version_queries(
    from_libraries: List[LibraryResolved],
    using: Dict[LibName, str],
    extra_index: List[LibraryResolved],
    resolutions_cache: Dict[QueryKey, ResolvedQuery],
    versions_cache: Dict[LibName, List[str]],
    configuration: Configuration,
    context: Context,
):
    async with context.start(
        action="resolve_dependencies_version_queries"
    ) as ctx:  # type: Context
        inputs_flat_dependencies = [
            LibraryQueryWithParent(**dependency.dict(), parent=lib)
            for lib in from_libraries
            for dependency in lib.dependencies
        ]

        await ctx.info(
            text="Raw dependencies retrieved",
            data={"dependencies": inputs_flat_dependencies},
        )

        inputs_flat_dependencies = await remove_duplicates(
            libraries=inputs_flat_dependencies, get_key=get_query_key, context=ctx
        )
        inputs_flat_dependencies = [
            lib_query
            for lib_query in inputs_flat_dependencies
            if get_query_key(lib_query) not in resolutions_cache
        ]

        await ctx.info(
            text="Dependencies to resolve retrieved",
            data={"dependencies": inputs_flat_dependencies},
        )

        resolved_versions = await asyncio.gather(
            *[
                resolve_version(
                    dependency,
                    configuration=configuration,
                    using=using,
                    extra_index=extra_index,
                    versions_cache=versions_cache,
                    context=ctx,
                )
                for dependency in inputs_flat_dependencies
            ],
            return_exceptions=True,
        )
        await raise_errors(
            errors=[
                resp
                for resp in resolved_versions
                if isinstance(resp, (LibraryNotFound, LibraryException))
            ],
            context=ctx,
        )
        resolved_versions = [
            lib for lib in resolved_versions if isinstance(lib, ResolvedQuery)
        ]

        resolutions_cache.update(
            {
                f"{api_version.name}#{api_version.query}": api_version
                for api_version in resolved_versions
            }
        )

        await sanity_checks_resolved_versions(resolutions_cache, ctx)
        return resolved_versions


async def fetch_dependencies_data(
    missing_data_versions: Dict[ExportedKey, ResolvedQuery],
    extra_index: List[LibraryResolved],
    full_data_cache: Dict[ExportedKey, LibraryResolved],
    configuration: Configuration,
    context: Context,
):
    async with context.start(action="query dependencies data") as ctx:  # type: Context
        resolved_dependencies = await asyncio.gather(
            *[
                get_data(
                    name=dependency.name,
                    version=dependency.version,
                    extra_index=extra_index,
                    configuration=configuration,
                    context=ctx,
                )
                for dependency in missing_data_versions.values()
            ],
            return_exceptions=True,
        )
        resolved_dependencies = [
            d for d in resolved_dependencies if isinstance(d, LibraryResolved)
        ]
        full_data_cache.update({d.exportedSymbol: d for d in resolved_dependencies})
        await ctx.info(
            text="Resolved dependencies",
            data={"dependencies": list(resolved_dependencies)},
        )
        return resolved_dependencies


async def get_data(
    name: str,
    version: str,
    extra_index: List[LibraryResolved],
    configuration: Configuration,
    context: Context,
) -> LibraryResolved:
    async with context.start(
        action="get_data", with_attributes={"lib": f"{name}#{version}"}
    ) as ctx:  # type: Context
        await ctx.info(f"Retrieved data of {name} version {version}")
        doc_db = configuration.doc_db
        data = next(
            (d for d in extra_index if d.name == name and d.version == version), None
        )
        if data is not None:
            return data
        data = await doc_db.get_document(
            partition_keys={"library_name": name},
            clustering_keys={"version_number": get_version_number_str(version)},
            owner=Constants.owner,
            headers=ctx.headers(),
        )
        metadata = LibraryResolved(
            name=name,
            version=version,
            exportedSymbol=exportedSymbols[name] if name in exportedSymbols else name,
            aliases=data.get("aliases", []),
            apiKey=get_api_key(version),
            fingerprint=data["fingerprint"],
            namespace=data["namespace"],
            type=data["type"],
            id=to_package_id(name),
            bundle=data["bundle"],
            dependencies=[
                LibraryQuery(name=d.split("#")[0], version=d.split("#")[1])
                for d in data["dependencies"]
            ],
        )
        return metadata


async def raise_errors(
    errors: List[Union[LibraryNotFound, LibraryException]], context: Context
):
    if not errors:
        return

    formatted_errors = [
        {
            "query": get_query_key(error.library),
            "fromPackage": {
                "name": error.library.parent.name,
                "version": error.library.parent.version,
            },
            "detail": str(error),
        }
        for error in errors
    ]

    await context.error(
        text="Errors while retrieving dependencies",
        data={"errors": formatted_errors},
    )
    raise DependenciesError(
        context="Errors while retrieving dependencies", errors=formatted_errors
    )


def retrieve_dependency_paths(
    known_libraries: List[LibraryResolved],
    from_package: str,
    get_key: Callable[[Union[LibraryQuery, LibraryResolved]], str],
    suffix: str = None,
) -> List[str]:
    parents = [
        lib
        for lib in known_libraries
        if any(get_key(dependency) == from_package for dependency in lib.dependencies)
    ]
    if not parents:
        return [f"{from_package} > {suffix}"]
    paths = [
        retrieve_dependency_paths(
            known_libraries=known_libraries,
            from_package=get_key(parent),
            get_key=get_key,
            suffix=f"{from_package} > {suffix}" if suffix else from_package,
        )
        for parent in parents
    ]
    paths = list(itertools.chain.from_iterable(paths))
    return paths


async def remove_duplicates(
    libraries: List[LibraryQueryWithParent],
    get_key: Callable[[LibraryQuery], str],
    context: Context,
) -> List[LibraryQueryWithParent]:
    async with context.start(action="remove_duplicates") as ctx:  # type: Context
        result = []
        keys = []
        for library in libraries:
            key = get_key(library)
            if key not in keys:
                keys.append(key)
                result.append(library)
            else:
                await ctx.info(f"Remove duplicate {key}")
        return result


def get_major(version: str):
    if version == "latest":
        return "?"
    version = version[1:] if version[0] in ["~", "^"] else version
    return int(version.split(".")[0])


async def sanity_checks_resolved_versions(resolutions_cache, ctx: Context):
    for api_version in resolutions_cache.values():
        twins = [
            val
            for val in resolutions_cache.values()
            if val.exportedSymbol == api_version.exportedSymbol
        ]
        if len(twins) == 1:
            continue
        warnings = [
            {"left": twin, "right": api_version}
            for twin in twins
            if twin.version != api_version.version
        ]
        if warnings:
            await ctx.warning(
                text="Mismatch in loading graph resolution: same API key, but different versions",
                data={"warnings": warnings},
            )
