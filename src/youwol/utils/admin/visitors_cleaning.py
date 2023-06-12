# standard library
import asyncio

# typing
from typing import List

# third parties
from pydantic import BaseModel

# Youwol utilities
from youwol.utils.clients.oidc.oidc_config import (
    OidcConfig,
    OidcForClient,
    PrivateClient,
)
from youwol.utils.clients.oidc.users_management import KeycloakUsersManagement, User
from youwol.utils.clients.treedb.treedb import TreeDbClient
from youwol.utils.context import Context


class CleanVisitorsBody(BaseModel):
    base_url: str
    admin_url: str
    admin_client_id: str
    admin_client_secret: str
    impersonator_name: str
    impersonator_pwd: str


class Token(BaseModel):
    access_token: str
    expires_in: int
    refresh_expires_in: int
    scope: str


class ImpersonatedUser(BaseModel):
    user: User
    token: Token

    def id(self):
        return self.user.id

    def headers(self):
        return {"authorization": f"Bearer {self.token.access_token}"}

    def group_id(self):
        return f"private_{self.user.id}"


class Drive(BaseModel):
    drive_id: str
    group_id: str
    impersonated: ImpersonatedUser


async def retrieve_tmp_users(
    openid_client: OidcForClient,
    users_manager: KeycloakUsersManagement,
    impersonator_name: str,
    impersonator_pwd: str,
) -> List[ImpersonatedUser]:
    impersonator_tokens = await openid_client.direct_flow(
        username=impersonator_name, password=impersonator_pwd
    )
    users = await users_manager.get_temporary_users()
    tokens = await asyncio.gather(
        *[
            openid_client.token_exchange(
                requested_subject=user.id,
                subject_token=impersonator_tokens["access_token"],
            )
            for user in users
        ]
    )
    return [
        ImpersonatedUser(user=user, token=Token(**token))
        for user, token in zip(users, tokens)
    ]


async def clean_drive(drive: Drive, treedb: TreeDbClient, context: Context):
    async with context.start(
        action="clean_drive", with_attributes={"driveId": drive.drive_id}
    ) as ctx:  # type: Context
        headers = {**ctx.headers(), **drive.impersonated.headers()}
        children = await treedb.get_children(folder_id=drive.drive_id, headers=headers)
        await ctx.info("Drive's children retrieved", data={"children": children})

        await asyncio.gather(
            *[
                treedb.remove_folder(folder_id=folder["folderId"], headers=headers)
                for folder in children["folders"]
            ],
            *[
                treedb.remove_item(item_id=item["itemId"], headers=headers)
                for item in children["items"]
            ],
        )
        await ctx.info(
            "Drive's content successfully deleted, proceed to drive deletion"
        )
        await treedb.purge_drive(drive_id=drive.drive_id, headers=headers)
        await treedb.delete_drive(drive_id=drive.drive_id, headers=headers)


async def clean_visitors(body: CleanVisitorsBody, context: Context):
    async with context.start(action="clean_visitors") as ctx:  # type: Context
        treedb = TreeDbClient(
            url_base="https://platform.youwol.com/api/assets-gateway/treedb-backend"
        )
        openid_config = OidcConfig(body.base_url)
        private_client = PrivateClient(
            client_id=body.admin_client_id, client_secret=body.admin_client_secret
        )
        openid_client = openid_config.for_client(private_client)
        users_manager = KeycloakUsersManagement(
            realm_url=body.admin_url, oidc_client=openid_client, cache=None
        )

        while True:
            await ctx.info(text="Start batch")
            impersonated_users = await retrieve_tmp_users(
                openid_client=openid_client,
                users_manager=users_manager,
                impersonator_name=body.impersonator_name,
                impersonator_pwd=body.impersonator_pwd,
            )
            await ctx.info(text=f"Retrieved {len(impersonated_users)} users")
            if not impersonated_users:
                await ctx.info(text="No more visitors, exit")
                return

            users_drives = await asyncio.gather(
                *[
                    treedb.get_drives(
                        group_id=user.group_id(),
                        headers={**ctx.headers(), **user.headers()},
                    )
                    for user in impersonated_users
                ]
            )

            no_data_users = [
                user
                for user_drives, user in zip(users_drives, impersonated_users)
                if not user_drives["drives"]
            ]

            await ctx.info(
                text=f"{len(no_data_users)} visitors with no data, proceed to deletion"
            )

            await asyncio.gather(
                *[users_manager.delete_user(user.id()) for user in no_data_users]
            )

            drives = [
                Drive(
                    drive_id=drive["driveId"],
                    group_id=drive["groupId"],
                    impersonated=user,
                )
                for user_drives, user in zip(users_drives, impersonated_users)
                for drive in user_drives["drives"]
            ]
            await ctx.info(
                text=f"Retrieved {len(drives)} drives to delete",
                data={"drives": [drive.dict() for drive in drives]},
            )

            await asyncio.gather(
                *[
                    clean_drive(drive=drive, treedb=treedb, context=ctx)
                    for drive in drives
                ]
            )
