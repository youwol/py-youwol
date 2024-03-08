# standard library
from pathlib import Path

# Youwol application
from youwol.app.environment import (
    BrowserAuth,
    Configuration,
    DirectAuth,
    Projects,
    get_standard_youwol_env,
)

# Youwol pipelines
import youwol.pipelines.pipeline_typescript_weback_npm as pipeline_ts

from youwol.pipelines import CdnTarget
from youwol.pipelines.pipeline_typescript_weback_npm import PublicNpmRepo

projects_folder = Path.home() / "Projects"

company_youwol = get_standard_youwol_env(
    env_id="foo",
    host="platform.foo.com",
    authentications=[
        BrowserAuth(authId="browser"),
        DirectAuth(authId="bar", userName="bar", password="bar-pwd"),
    ],
)


pipeline_ts.set_environment(
    environment=pipeline_ts.Environment(
        cdnTargets=[
            CdnTarget(
                name="public-yw",
                cloudTarget=get_standard_youwol_env(env_id="public-youwol"),
                authId="browser",
            ),
            CdnTarget(name="foo", cloudTarget=company_youwol, authId="bar"),
        ],
        npmTargets=[PublicNpmRepo(name="public")],
    )
)


Configuration(
    projects=Projects(
        finder=projects_folder,
        templates=[
            pipeline_ts.lib_ts_webpack_template(
                folder=projects_folder / "auto-generated"
            ),
            pipeline_ts.app_ts_webpack_template(
                folder=projects_folder / "auto-generated"
            ),
        ],
    )
)
