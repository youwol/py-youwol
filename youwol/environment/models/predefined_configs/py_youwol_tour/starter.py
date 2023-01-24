from pathlib import Path

from youwol.environment import Configuration, System, LocalEnvironment, Projects, RecursiveProjectsFinder
import youwol.pipelines.pipeline_typescript_weback_npm as pipeline_ts

pipeline_ts.set_environment()


def init_working_folders():
    root = Path('/tmp/py-youwol-story-env')
    root.mkdir(parents=True, exist_ok=True)
    cache = root / 'cache'
    projects = root / 'Projects'
    projects.mkdir(exist_ok=True)
    ecosystem = root / 'data'

    return root, cache, projects, ecosystem


root_folder, cache_folder, projects_folder, ecosystem_folder = init_working_folders()

Configuration(
    projects=Projects(
        finder=RecursiveProjectsFinder(
            fromPaths=[projects_folder],
        )
    ),
    system=System(
        localEnvironment=LocalEnvironment(
            dataDir=ecosystem_folder,
            cacheDir=cache_folder
        )
    )
)
