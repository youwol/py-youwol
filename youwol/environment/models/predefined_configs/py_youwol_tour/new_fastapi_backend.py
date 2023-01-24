from fastapi import APIRouter

from youwol.environment import Configuration, System, LocalEnvironment, CustomEndPoints, Customization
from youwol.environment.models.predefined_configs.py_youwol_tour.starter import init_working_folders

from youwol_utils.servers.fast_api import FastApiRouter

root_folder, cache_folder, projects_folder, ecosystem_folder = init_working_folders()


def backend_service():
    router = APIRouter()

    @router.get("/users/", tags=["users"])
    async def read_users():
        return [{"username": "Rick"}, {"username": "Morty"}]

    @router.get("/users/me", tags=["users"])
    async def read_user_me():
        return {"username": "fakecurrentuser"}

    @router.get("/users/{username}", tags=["users"])
    async def read_user(username: str):
        return {"username": username}

    return router


Configuration(
    system=System(
        localEnvironment=LocalEnvironment(
            dataDir=ecosystem_folder,
            cacheDir=cache_folder
        )
    ),
    customization=Customization(
        endPoints=CustomEndPoints(
            routers=[
                FastApiRouter(
                    base_path="/api/users-service",
                    router=backend_service()
                )
            ]
        )
    )
)
