"""Support for the CasaTunes media player."""
from __future__ import annotations

import datetime as dt
import logging

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from pycasatunes.objects.zone import CasaTunesZone
from pycasatunes.objects.source import CasaTunesSource
from pycasatunes.objects.media import CasaTunesMedia
from pycasatunes.exceptions import CasaException

import voluptuous as vol

from homeassistant.components.media_player import (
    BrowseMedia,
    DEVICE_CLASS_SPEAKER,
    MediaPlayerEntity,
)

from homeassistant.components.media_player.const import (
    MEDIA_TYPE_MUSIC,
    MEDIA_TYPE_PLAYLIST,
    SUPPORT_BROWSE_MEDIA,
    SUPPORT_PLAY_MEDIA,
    SUPPORT_PLAY,
    SUPPORT_PAUSE,
    SUPPORT_STOP,
    SUPPORT_SELECT_SOURCE,
    SUPPORT_TURN_OFF,
    SUPPORT_TURN_ON,
    SUPPORT_VOLUME_MUTE,
    SUPPORT_VOLUME_SET,
    SUPPORT_NEXT_TRACK,
    SUPPORT_PREVIOUS_TRACK,
    SUPPORT_SEEK,
    SUPPORT_SHUFFLE_SET,
    SUPPORT_GROUPING,
)

from homeassistant.components.media_player.errors import BrowseError
from homeassistant.const import (
    ATTR_ENTITY_ID,
    STATE_IDLE,
    STATE_ON,
    STATE_OFF,
    STATE_PAUSED,
    STATE_PLAYING,
)
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers import entity_platform
from homeassistant.helpers.network import is_internal_request
from homeassistant.helpers.entity import Entity
import homeassistant.util.dt as dt_util

from .const import DOMAIN
from . import CasaTunesDataUpdateCoordinator, CasaTunesDeviceEntity

SUPPORT_CASATUNES = (
    SUPPORT_SELECT_SOURCE
    | SUPPORT_TURN_OFF
    | SUPPORT_TURN_ON
    | SUPPORT_VOLUME_SET
    | SUPPORT_VOLUME_MUTE
    | SUPPORT_NEXT_TRACK
    | SUPPORT_PREVIOUS_TRACK
    | SUPPORT_SEEK
    | SUPPORT_PLAY
    | SUPPORT_PAUSE
    | SUPPORT_STOP
    | SUPPORT_SHUFFLE_SET
    | SUPPORT_GROUPING
)

STATUS_TO_STATES = {0: STATE_IDLE, 1: STATE_PAUSED, 2: STATE_PLAYING, 3: STATE_ON}

_LOGGER = logging.getLogger(__name__)

ATTR_CASATUNES_GROUP = "casatunes_group"


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the CasaTunes config entry."""
    coordinator: CasaTunesDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    media_players: list[Entity] = []

    for zone in coordinator.data.zones:
        unique_id = coordinator.data.system.attributes["MACAddress"]
        media_players.append(CasaTunesMediaPlayer(coordinator, zone, unique_id))

    async_add_entities(media_players)


class CasaTunesMediaPlayer(CasaTunesDeviceEntity, MediaPlayerEntity):
    """Representation of a CasaTunes media player on the network."""

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        zone: CasaTunesZone,
        unique_id: str,
    ) -> None:
        """Initialize CasaTunes sensor."""
        super().__init__(
            coordinator,
            zone,
            device_id=f"{unique_id}_{zone.ZoneID}",
            zone_id=zone.ZoneID,
        )

        self._attr_unique_id = f"{unique_id}_{zone.ZoneID}"
        self._attr_supported_features = SUPPORT_CASATUNES
        self._zone_id = zone.ZoneID

    async def async_added_to_hass(self):
        """Run when this Entity has been added to HA."""
        await super().async_added_to_hass()
        self.coordinator.entities.append(self)

    async def async_will_remove_from_hass(self):
        """Entity being removed from hass."""
        await super().async_will_remove_from_hass()
        self.coordinator.entities.remove(self)

    def _media_playback_trackable(self) -> bool:
        """Detect if we have enough media data to track playback."""
        if self.coordinator.data.media[self.zone.SourceID].CurrSong.Duration is None:
            return False

        return self.coordinator.data.media[self.zone.SourceID].CurrSong.Duration > 0

    def _casatunes_entities(self) -> list[CasaTunesMediaPlayer]:
        """Return all media player entities of the casatunes system."""
        entities = []
        for coordinator in self.hass.data[DOMAIN].values():
            entities += [
                entity
                for entity in coordinator.entities
                if isinstance(entity, CasaTunesMediaPlayer)
            ]
        return entities

    @property
    def is_master(self) -> bool:
        return self.zone.SharedRoomID and self.zone.MasterMode

    @property
    def is_client(self) -> bool:
        return self.zone.SharedRoomID and not self.zone.MasterMode

    @property
    def device_class(self) -> str | None:
        """Return the class of this device."""
        return DEVICE_CLASS_SPEAKER

    @property
    def name(self) -> str | None:
        """Return the name of the device."""
        # TODO: mini-media-player already appends +1, +2 to grouped sones.
        # if self.zone.GroupName is not None:
        #     return self.zone.GroupName

        return self.zone.Name

    @property
    def state(self) -> str | None:
        """Return the state of the device."""
        if self.zone and self.zone.Power is not False:
            state = self.coordinator.data.media[self.zone.SourceID].Status
            return STATUS_TO_STATES.get(state, None)
        else:
            return STATE_OFF

    @property
    def shuffle(self):
        """Boolean if shuffle is enabled."""
        return self.coordinator.data.media[self.zone.SourceID].ShuffleMode

    @property
    def volume_level(self) -> str | None:
        """Return the volume level of the media player (0..1)."""
        return int(self.zone.Volume) / 100.0

    @property
    def is_volume_muted(self) -> str | None:
        """Return boolean if volume is currently muted."""
        return self.zone.Mute

    @property
    def source(self):
        """Name of the current input source."""
        for source in self.coordinator.data.sources:
            if source.SourceID == self.zone.SourceID:
                return source.Name
        return None

    @property
    def source_list(self):
        """List of available input sources."""
        return [
            source.Name for source in self.coordinator.data.sources if not source.Hidden
        ]

    @property
    def media_track(self):
        """Return the track number of current media (Music track only)."""
        return self.coordinator.data.media[self.zone.SourceID].QueueSongIndex

    @property
    def media_title(self):
        """Title of current playing media."""
        return self.coordinator.data.media[self.zone.SourceID].CurrSong.Title

    @property
    def media_artist(self):
        """Artist of current playing media, music track only."""
        return self.coordinator.data.media[self.zone.SourceID].CurrSong.Artists

    @property
    def media_album_name(self):
        """Album name of current playing media, music track only."""
        return self.coordinator.data.media[self.zone.SourceID].CurrSong.Album

    @property
    def media_duration(self) -> int | None:
        """Duration of current playing media in seconds."""
        if self._media_playback_trackable():
            return self.coordinator.data.media[self.zone.SourceID].CurrSong.Duration

        return None

    @property
    def media_position(self):
        """Position of current playing media in seconds."""
        if self._media_playback_trackable():
            return self.coordinator.data.media[self.zone.SourceID].CurrProgress

        return None

    @property
    def media_position_updated_at(self) -> dt.datetime | None:
        """When was the position of the current playing media valid.
        Returns value from homeassistant.util.dt.utcnow().
        """
        if self._media_playback_trackable():
            return self.coordinator.data.media[self.zone.SourceID].last_updated_at

        return None

    @property
    def media_content_type(self):
        """Content type of current playing media."""
        return MEDIA_TYPE_MUSIC
        # return MEDIA_TYPE_PLAYLIST

    @property
    def media_image_url(self):
        """Image url of current playing media."""
        return self.coordinator.data.media[self.zone.SourceID].CurrSong.ArtworkURI

    @property
    def group_members(self) -> list[str] | None:
        """
        Return a list of entity_ids, which belong to the group of self.
        [self] returned first since first entity is master.
        """

        zone_clients = [
            zone.ZoneID for zone in self.coordinator.data.zones if zone.SharedRoomID
        ]

        if self.is_master:
            entities = self._casatunes_entities()
            clients = [
                entity.entity_id
                for entity in entities
                if entity.is_client and entity.zone_id in zone_clients
            ]
            return [self.entity_id] + clients

    @property
    def zone_master(self) -> None:
        """Get zone master for this zone."""
        for zone in self.coordinator.data.zones:
            if zone.MasterMode and zone.SharedRoomID == self.zone.SharedRoomID:
                return zone.ZoneID

    async def sync_master(self):
        """If there are no clients left in master zone, remove master flag."""
        if not [entity for entity in self._casatunes_entities() if entity.is_client]:
            await self.coordinator.data.zone_master(self.zone_master, False)
            await self.coordinator.async_refresh()
            _LOGGER.debug("%s zone is no longer master.", self.zone_master)

    async def async_turn_on(self):
        """Turn the media player on."""
        await self.coordinator.data.turn_on(self.zone_id)
        await self.coordinator.async_refresh()

    async def async_turn_off(self):
        """Turn the media player off."""
        await self.coordinator.data.turn_off(self.zone_id)
        await self.coordinator.async_refresh()

    async def async_set_volume_level(self, volume):
        """Set the volume level."""
        await self.coordinator.data.set_volume_level(self.zone_id, int(volume * 100))
        await self.coordinator.async_refresh()

    async def async_mute_volume(self, mute):
        """Mute the volume."""
        await self.coordinator.data.mute_volume(self.zone_id, mute)
        await self.coordinator.async_refresh()

    async def async_media_seek(self, position):
        """Send seek command."""
        await self.coordinator.data.player_action(
            self.zone_id, f"position={int(position)}"
        )
        await self.coordinator.async_refresh()

    async def async_media_previous_track(self):
        """Send previous track command."""
        await self.coordinator.data.player_action(self.zone_id, "previous")
        await self.coordinator.async_refresh()

    async def async_media_next_track(self):
        """Send next track command."""
        await self.coordinator.data.player_action(self.zone_id, "next")
        await self.coordinator.async_refresh()

    async def async_media_play(self):
        """Send play command."""
        await self.coordinator.data.player_action(self.zone_id, "play")
        await self.coordinator.async_refresh()

    async def async_media_pause(self):
        """Send pause command."""
        await self.coordinator.data.player_action(self.zone_id, "pause")
        await self.coordinator.async_refresh()

    async def async_media_stop(self):
        """Send pause command."""
        await self.coordinator.data.player_action(self.zone_id, "stop")
        await self.coordinator.async_refresh()

    async def async_set_shuffle(self, shuffle):
        """Enable/disable shuffle mode."""
        str_flag = "true" if shuffle else "false"
        await self.coordinator.data.player_action(
            self.zone_id, "shuffle", f"ShuffleMode={str_flag}"
        )
        await self.coordinator.async_refresh()

    async def async_select_source(self, source):
        """Select input source."""
        for source_item in self.coordinator.data.sources:
            if source_item.Name == source:
                """If zone is a client on a zone, we should leave."""
                await self.coordinator.data.change_source(
                    self.zone_id, source_item.SourceID
                )
                await self.coordinator.async_refresh()
                await self.sync_master()

    async def async_join_players(self, group_members):
        """Join `group_members` as a player group with the current player."""

        _LOGGER.debug(
            "%s wants to add the following entities %s",
            self.entity_id,
            str(group_members),
        )

        """Make sure self.zone is or becomes master."""
        await self.coordinator.data.zone_master(self.zone_id, True)

        entities = [
            entity
            for entity in self._casatunes_entities()
            if entity.entity_id in group_members
        ]

        for client in entities:
            if client != self:
                await self.coordinator.data.zone_join(self.zone_id, client.zone_id)

        await self.coordinator.async_refresh()
        await self.sync_master()

    async def async_unjoin_player(self):
        """Remove this player from any group."""
        await self.coordinator.data.zone_unjoin(self.zone_master, self.zone_id)
        await self.coordinator.async_refresh()
        await self.sync_master()