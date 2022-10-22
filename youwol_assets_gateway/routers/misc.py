from fastapi import APIRouter

from youwol_assets_gateway.all_icons_emojipedia import (
    icons_smileys_people, icons_animals, icons_foods, icons_flags, icons_objects,
    icons_travel, icons_activities, icons_symbols,
)

router = APIRouter(tags=["assets-gateway.misc"])


@router.get("/emojis/{category}",
            summary="return available emojis",
            )
async def list_emojis(category):
    """
    We need to move this end-point somewhere else
    """
    icons = {
        "smileys_people": icons_smileys_people,
        "animals": icons_animals,
        "foods": icons_foods,
        "activities": icons_activities,
        "travel": icons_travel,
        "objects": icons_objects,
        "symbols": icons_symbols,
        "flags": icons_flags
    }
    return {
        'emojis': [icon[0] for icon in icons[category]]
    }
