from youwol.environment import Configuration, System, LocalEnvironment, Projects, RecursiveProjectsFinder, \
    get_standard_youwol_env
from youwol.environment.models.predefined_configs.py_youwol_tour.starter import init_working_folders
from youwol.pipelines import CdnTarget
from youwol.pipelines.pipeline_typescript_weback_npm import app_ts_webpack_template

import youwol.pipelines.pipeline_typescript_weback_npm as pipeline_ts

root_folder, cache_folder, projects_folder, ecosystem_folder = init_working_folders()


pipeline_ts.set_environment(environment=pipeline_ts.Environment(
    cdnTargets=[
        CdnTarget(
            name="prod",
            cloudTarget=get_standard_youwol_env(env_id='prod'),
            authId='browser'
        ),
    ]
))


Configuration(
    projects=Projects(
        finder=RecursiveProjectsFinder(
            fromPaths=[projects_folder],
        ),
        templates=[
            app_ts_webpack_template(folder=projects_folder)
        ]
    ),
    system=System(
        localEnvironment=LocalEnvironment(
            dataDir=ecosystem_folder,
            cacheDir=cache_folder
        )
    )
)
