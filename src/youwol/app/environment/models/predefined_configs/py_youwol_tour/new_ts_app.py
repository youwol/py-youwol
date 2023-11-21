# Youwol application
from youwol.app.environment import (
    BrowserAuth,
    Configuration,
    LocalEnvironment,
    Projects,
    RecursiveProjectsFinder,
    System,
    get_standard_youwol_env,
)
from youwol.app.environment.models.predefined_configs.py_youwol_tour.starter import (
    init_working_folders,
)

# Youwol pipelines
import youwol.pipelines.pipeline_typescript_weback_npm as pipeline_ts

from youwol.pipelines import CdnTarget
from youwol.pipelines.pipeline_typescript_weback_npm import app_ts_webpack_template

root_folder, cache_folder, projects_folder, ecosystem_folder = init_working_folders()


pipeline_ts.set_environment(
    environment=pipeline_ts.Environment(
        cdnTargets=[
            CdnTarget(
                name="remote",
                cloudTarget=get_standard_youwol_env(
                    env_id="remote", authentications=[BrowserAuth(authId="browser")]
                ),
                authId="browser",
            ),
        ]
    )
)


Configuration(
    projects=Projects(
        finder=RecursiveProjectsFinder(
            fromPaths=[projects_folder],
        ),
        templates=[app_ts_webpack_template(folder=projects_folder)],
    ),
    system=System(
        localEnvironment=LocalEnvironment(
            dataDir=ecosystem_folder, cacheDir=cache_folder
        )
    ),
)
