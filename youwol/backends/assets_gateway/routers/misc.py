from fastapi import APIRouter

from ..all_icons_emojipedia import (
    icons_smileys_people, icons_animals, icons_foods, icons_flags, icons_objects,
    icons_travel, icons_activities, icons_symbols,
)

router = APIRouter()


@router.get("/emojis/{category}",
            summary="return available emojis",
            )
async def list_emojis(category):
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
