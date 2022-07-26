import asyncio
import itertools
from typing import List, Callable, Union, Dict, Tuple

from fastapi import HTTPException

from youwol_cdn_backend.utils import Configuration, get_version_number_str, Constants, list_versions, \
    to_package_id
from youwol_cdn_backend.utils_indexing import get_version_number
from youwol_utils import CircularDependencies, DependenciesError, DependencyErrorData
from youwol_utils.context import Context
from youwol_utils.http_clients.cdn_backend import LibraryResolved, LibraryQuery

LibKey = str


class LibraryException(HTTPException):

    library: LibraryQuery

    def __init__(self, library: LibraryQuery, **kwargs):
        HTTPException.__init__(
            self,
            status_code=500,
            detail=f"Error while processing library {library.name} not found",
            **kwargs)
        self.library = library


class LibraryNotFound(HTTPException):

    library: LibraryQuery

    def __init__(self, library: LibraryQuery, **kwargs):
        HTTPException.__init__(
            self,
            status_code=404,
            detail=f"Library {library.name} not found",
            **kwargs)
        self.library = library


async def loading_graph(
        downloaded: List[LibKey],
        remaining: List[LibraryResolved],
        items_dict: Dict[LibKey, Tuple[str, str]],
        get_key: Callable[[Union[LibraryResolved, LibraryQuery]], LibKey],
        context: Context
):
    async with context.start(action="loading_graph") as ctx:  # type: Context
        dependencies = {get_key(d): [get_key(dependency) in downloaded for dependency in d.dependencies]
                        for d in remaining}
        await ctx.info(text="Requested libraries", data=dependencies)
        fulfilled_libs = [key for key, dependencies_available in dependencies.items() if all(dependencies_available)]
        await ctx.info(text="Library to download", data={'fulfilledLibs': fulfilled_libs})
        new_remaining = [p for p in remaining if get_key(p) not in fulfilled_libs]

        await ctx.info(text="New remaining dependencies",
                       data={'new_remaining': [get_key(lib) for lib in new_remaining]})

        if not new_remaining:
            response = [[items_dict[a] for a in fulfilled_libs]]
            await ctx.info("Loading-graph final step", data={"response": response})
            return response

        if len(new_remaining) == len(remaining):
            dependencies_dict = {get_key(d): d.dependencies for d in remaining}
            not_founds = {pack: [dependencies_dict[pack][i] for i, found in enumerate(founds) if not found]
                          for pack, founds in dependencies.items()}
            await ctx.error(text="Can not resolve dependency(ies)",
                            data={"newRemaining": new_remaining, "oldRemaining": remaining})
            raise CircularDependencies(context="Loading graph resolution stuck",
                                       packages=not_founds)
        next_round = await loading_graph(
            downloaded=downloaded + [r for r in fulfilled_libs],
            remaining=new_remaining,
            items_dict=items_dict,
            get_key=get_key,
            context=ctx
        )
        response = [[items_dict[a] for a in fulfilled_libs]] + next_round
        await ctx.info("Loading-graph retrieved", data={"response": response})
        return response


async def list_all_versions_with_cache(
        library: LibraryQuery,
        versions_cache: Dict[str, List[str]],
        configuration: Configuration,
        context: Context
):
    if library.name in versions_cache:
        await context.info(text=f'Retrieved versions from cache {library.name}')
        return versions_cache[library.name]
    try:
        versions_resp = await list_versions(name=library.name, context=context, max_results=1000,
                                            configuration=configuration)
    except HTTPException as e:
        if e.status_code == 404:
            raise LibraryNotFound(library=library)
        raise LibraryException(library=library)

    versions_cache[library.name] = versions_resp.versions
    return versions_cache[library.name]


async def resolve_version(
        dependency: LibraryQuery,
        using: Dict[str, str],
        get_key: Callable[[Union[LibraryResolved, LibraryQuery]], str],
        versions_cache: Dict[str, List[str]],
        configuration: Configuration,
        context: Context
) -> LibraryQuery:

    async with context.start(action="resolve_version",
                             with_attributes={'library': get_key(dependency)}) as ctx:  # type: Context
        if dependency.name in using:
            await ctx.info(text=f"Use specified fixed version {using[dependency.name]}")
            return LibraryQuery(name=dependency.name, version=using[dependency.name])

        versions = await list_all_versions_with_cache(library=dependency, versions_cache=versions_cache,
                                                      context=ctx, configuration=configuration)

        if dependency.version in ["latest", "x", "*"]:
            await ctx.info(text=f"Use latest version {versions[0]}")
            return LibraryQuery(name=dependency.name, version=versions[0])

        target_major = get_major(dependency.version)
        from_version_number = get_version_number(f"{target_major}.0.0")
        to_version_number = get_version_number(f"{target_major+1}.0.0")
        version = next(v for v in versions
                       if from_version_number <= get_version_number(v) < to_version_number)
        await ctx.info(text=f"Use latest compatible version of {target_major} : {version}")
        return LibraryQuery(name=dependency.name, version=version)


async def resolve_dependencies_recursive(
        known_libraries: List[LibraryResolved],
        get_key: Callable[[Union[LibraryResolved, LibraryQuery]], str],
        using: Dict[str, str],
        versions_cache: Dict[str, List[str]],
        configuration: Configuration,
        context: Context,
):

    async with context.start(action="resolve_dependencies_recursive") as ctx:  # type: Context
        """ It maybe the case where some dependencies are missing in the provided body,
        here we fetch using 'body.using' or the latest version of them"""

        inputs_flat_dependencies = [dependency for lib in known_libraries for dependency in lib.dependencies]
        await ctx.info(text="Start another layer to fetch missing dependencies",
                       data={"raw dependencies": inputs_flat_dependencies})

        inputs_flat_dependencies = await remove_duplicates(libraries=inputs_flat_dependencies, get_key=get_key,
                                                           context=ctx)
        async with ctx.start(action='resolve versions') as ctx_latest:  # type: Context
            flat_dependencies = await asyncio.gather(
                *[resolve_version(dependency, get_key=get_key, configuration=configuration,
                                  using=using, versions_cache=versions_cache, context=ctx_latest)
                  for dependency in inputs_flat_dependencies],
                return_exceptions=True
            )
            flat_dependencies = list(flat_dependencies)

        await raise_errors(
            errors=[resp for resp in flat_dependencies
                    if isinstance(resp, LibraryNotFound) or isinstance(resp, LibraryException)],
            known_libraries=known_libraries,
            get_key=get_key,
            context=ctx
        )
        # it maybe the case that 'latest' resolution yield to duplicates
        flat_dependencies = await remove_duplicates(libraries=flat_dependencies, get_key=get_key, context=ctx)

        resolved_keys = [get_key(lib) for lib in known_libraries]
        missing_dependencies = [d for d in flat_dependencies if get_key(d) not in resolved_keys]

        await ctx.info(text="Prepared dependencies",
                       data={"missing": missing_dependencies, "already retrieved": known_libraries})

        if not missing_dependencies:
            await ctx.info(text="No more dependencies to resolve :)")
            return known_libraries

        async with ctx.start(action="query dependencies data") as ctx_dependencies:  # type: Context
            resolved_dependencies = await asyncio.gather(
                *[get_data(lib_query=dependency, configuration=configuration, context=ctx_dependencies)
                  for dependency in missing_dependencies],
                return_exceptions=True
            )
            await ctx_dependencies.info(text="Resolved dependencies",
                                        data={"dependencies": list(resolved_dependencies)})

        await raise_errors(
            errors=[resp for resp in resolved_dependencies
                    if isinstance(resp, LibraryNotFound) or isinstance(resp, LibraryException)],
            known_libraries=known_libraries,
            get_key=get_key,
            context=ctx
        )

        return await resolve_dependencies_recursive(
            known_libraries=[*known_libraries, *resolved_dependencies],
            get_key=get_key,
            using=using,
            configuration=configuration,
            versions_cache=versions_cache,
            context=ctx
        )


async def get_data(
        lib_query: LibraryQuery,
        configuration: Configuration,
        context: Context) \
        -> LibraryResolved:

    async with context.start(action="get_data",
                             with_attributes={'lib': f'{lib_query.name}#{lib_query.version}'}) \
            as ctx:  # type: Context
        await ctx.info(f"Retrieved data of {lib_query.name} version {lib_query.version}")
        doc_db = configuration.doc_db
        try:
            data = await doc_db.get_document(
                partition_keys={"library_name": lib_query.name},
                clustering_keys={"version_number": get_version_number_str(lib_query.version)},
                owner=Constants.owner, headers=ctx.headers()
            )
            metadata = LibraryResolved(
                name=lib_query.name,
                version=lib_query.version,
                fingerprint=data['fingerprint'],
                namespace=data['namespace'],
                type=data['type'],
                id=to_package_id(lib_query.name),
                bundle=data['bundle'],
                dependencies=[LibraryQuery(name=d.split('#')[0], version=d.split('#')[1])
                              for d in data['dependencies']]
            )
        except HTTPException as e:
            if e.status_code != 404:
                raise LibraryException(
                    library=lib_query,
                    detail=f"{lib_query.name}: error while resolving version {lib_query.version}"
                )
            raise LibraryNotFound(library=lib_query,
                                  detail=f"{lib_query.name}: version {lib_query.version} not found")

        return metadata


async def raise_errors(
        errors: List[Union[LibraryNotFound, LibraryException]],
        known_libraries: List[LibraryResolved],
        get_key: Callable[[Union[LibraryQuery, LibraryResolved]], str],
        context: Context
):
    if not errors:
        return
    paths = [retrieve_dependency_paths(
        known_libraries=known_libraries,
        get_key=get_key,
        from_package=get_key(error.library),
    ) for error in errors]
    formatted_errors = [{
        "key": get_key(error.library),
        "paths": path,
        "detail": ""
    } for error, path in zip(errors, paths)]
    await context.error(
        text="Errors while retrieving dependencies",
        data={"paths": paths},
    )
    raise DependenciesError(
        context="Errors while retrieving dependencies",
        errors=formatted_errors
    )


def retrieve_dependency_paths(
        known_libraries: List[LibraryResolved],
        from_package: str,
        get_key: Callable[[Union[LibraryQuery, LibraryResolved]], str],
        suffix: str = None
) -> List[str]:
    parents = [lib for lib in known_libraries
               if any([get_key(dependency) == from_package for dependency in lib.dependencies])]
    if not parents:
        return [f"{from_package} > {suffix}"]
    paths = [retrieve_dependency_paths(known_libraries=known_libraries,
                                       from_package=get_key(parent),
                                       get_key=get_key,
                                       suffix=f"{from_package} > {suffix}" if suffix else from_package)
             for parent in parents]
    paths = list(itertools.chain.from_iterable(paths))
    return paths


async def remove_duplicates(
        libraries: List[LibraryQuery],
        get_key: Callable[[Union[LibraryQuery, LibraryResolved]], str],
        context: Context
) -> List[LibraryQuery]:

    async with context.start(action="remove_duplicates") as ctx:  # type: Context
        result = []
        keys = []
        for library in libraries:
            key = get_key(library)
            if key not in keys:
                keys.append(key)
                result.append(library)
            else:
                await ctx.info(f'Remove duplicate {key}')
        return result


def get_major(version: str):
    if version == 'latest':
        return '?'
    version = version[1:] if version[0] in ['~', '^'] else version
    return int(version.split('.')[0])
