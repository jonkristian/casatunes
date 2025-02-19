"""Support to interface with the Roon API."""
import logging

from homeassistant.components.media_player import BrowseMedia
from homeassistant.components.media_player.const import MediaClass
from homeassistant.components.media_player.errors import BrowseError


class UnknownMediaType(BrowseError):
    """Unknown media type."""

CT_COLLECTION = 8
CT_ALLOWSELECT = 8192

BROWSE_LIMIT = 1000

_LOGGER = logging.getLogger(__name__)


async def build_item_response(
    zone_id, casa_server, media_content_type=None, media_content_id=None
):
    """Implement the websocket media browsing helper."""
    try:
        _LOGGER.debug("browse_media: %s: %s", media_content_type, media_content_id)
        if media_content_type in [None, "library"]:
            return await library_payload(casa_server, zone_id, media_content_id)

    except UnknownMediaType as err:
        raise BrowseError(
            f"Media not found: {media_content_type} / {media_content_id}"
        ) from err


async def item_payload(casa_server, item):
    """Create response payload for a single media item."""

    title = item["Title"]

    thumbnail = None
    image_id = item.get("ArtworkURI")
    if image_id:
        thumbnail = (
            image_id
            if image_id.startswith(("http://", "https://"))
            else await casa_server.data.get_image(image_id)
        )

    flags = item["Flags"]

    if (flags & CT_COLLECTION) and (flags & CT_ALLOWSELECT):
        media_content_type = "library"
        media_class = MediaClass.PLAYLIST
        can_play = True
        can_expand = True
    elif (flags & CT_COLLECTION):
        media_content_type = "library"
        media_class = MediaClass.DIRECTORY
        can_play = False
        can_expand = True
    else:
        media_content_type = "track"
        media_class = MediaClass.TRACK
        can_expand = False
        can_play = True

    media_content_id = item["ID"]

    payload = {
        "title": title,
        "media_class": media_class,
        "media_content_id": media_content_id,
        "media_content_type": media_content_type,
        "can_play": can_play,
        "can_expand": can_expand,
        "thumbnail": thumbnail,
    }

    return BrowseMedia(**payload)


async def library_payload(casa_server, zone_id, media_content_id):
    """Create response payload for the library."""

    opts = {
        "hierarchy": "browse",
        "zone_id": zone_id,
        "limit": BROWSE_LIMIT,
    }

    if media_content_id is None or media_content_id == "Explore":
        opts["pop_all"] = True
        content_id = "Explore"
    else:
        opts["item_id"] = media_content_id
        content_id = media_content_id

    result_detail = await casa_server.data.get_media(opts)
    _LOGGER.debug("Result detail %s", result_detail)

    list_title = "Browse Media"
    if "Title" in result_detail:
        list_title = result_detail["Title"]

    library_info = BrowseMedia(
        title=list_title,
        media_class=MediaClass.DIRECTORY,
        media_content_type="library",
        media_content_id=content_id,
        can_play=False,
        can_expand=True,
        children=[],
    )

    if "MediaItems" in result_detail:
        for item in result_detail["MediaItems"]:
            entry = await item_payload(casa_server, item)
            library_info.children.append(entry)

    return library_info
