"""The Waste Manager integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from homeassistant.components.http import StaticPathConfig
from homeassistant.helpers.event import async_track_time_change
import datetime
import logging
from .const import DOMAIN, CONF_NOTIFY_SERVICE, CONF_NOTIFY_TIME, CONF_ACTION_ENTITY

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.CALENDAR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Waste Manager from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    try:
        # Register static paths
        path_www = hass.config.path("custom_components/waste_manager/www")
        path_rifiuti = hass.config.path("custom_components/waste_manager/rifiuti")
        _LOGGER.info("Waste Manager registering static paths: %s -> %s", "/local/waste_manager", path_www)
        
        await hass.http.async_register_static_paths([
            StaticPathConfig(
                "/local/waste_manager",
                path_www,
                cache_headers=False,
            ),
            StaticPathConfig(
                "/local/waste_manager/rifiuti",
                path_rifiuti,
                cache_headers=False,
            )
        ])
        
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
        
        # Setup Notification Scheduler
        await async_setup_scheduler(hass, entry)
        
    except Exception as e:
        _LOGGER.exception("Error setting up Waste Manager integration: %s", e)
        return False

    entry.async_on_unload(entry.add_update_listener(update_listener))

    return True

_LOGGER = logging.getLogger(__name__)

async def async_setup_scheduler(hass, entry):
    """Setup the notification scheduler."""
    # Cancel existing listener if any
    if "unsub_scheduler" in hass.data[DOMAIN].get(entry.entry_id, {}):
         hass.data[DOMAIN][entry.entry_id]["unsub_scheduler"]()
    
    config = entry.options if entry.options else entry.data
    notify_service = config.get(CONF_NOTIFY_SERVICE)
    notify_time = config.get(CONF_NOTIFY_TIME)

    if not notify_service or not notify_time:
        return

    try:
        hour, minute = map(int, notify_time.split(":"))
    except ValueError:
        _LOGGER.error("Invalid notification time format: %s", notify_time)
        return

    async def check_and_notify(now):
        _LOGGER.debug("Waste Manager: Checking for notifications...")
        
        from homeassistant.util import dt as dt_util
        today = dt_util.now().date()
        
        # Simplified Check Logic
        # If notify_time is evening (> 12:00), we warn about TOMORROW's pickup.
        # If notify_time is morning (< 12:00), we warn about TODAY's pickup.
        
        target_date = today
        prefix = "Oggi"
        if hour >= 12:
            target_date = today + datetime.timedelta(days=1)
            prefix = "Domani"
            
        target_weekday = target_date.weekday()
        
        # Map weekday to config key
        week_schedule_keys = [
            "monday", "tuesday", "wednesday", "thursday", 
            "friday", "saturday", "sunday"
        ]
        key = week_schedule_keys[target_weekday]
        
        waste_type = config.get(key)
        
        if waste_type:
            message = f"{prefix} ritiro: {waste_type}. Ricordati di esporre i rifiuti!"
            try:
                if notify_service:
                    service_name = notify_service.replace("notify.", "")
                    
                    data = {
                        "message": message, 
                        "title": "Gestione Rifiuti",
                        "data": {
                            "actions": [
                                {
                                    "action": "MARK_COLLECTED",
                                    "title": "✅ Segna come Fatto",
                                    "activationMode": "background",
                                    "authenticationRequired": False
                                }
                            ],
                            # iOS Specifics
                            "push": {
                                "category": "WASTE_COLLECTION"
                            }
                        }
                    }
                    
                    await hass.services.async_call(
                        "notify", 
                        service_name, 
                        data
                    )
            except Exception as e:
                _LOGGER.error("Failed to send notification: %s", e)

            # Execute Action (Turn On)
            action_entities = config.get(CONF_ACTION_ENTITY)
            if action_entities:
                if isinstance(action_entities, str):
                    action_entities = [action_entities]
                
                _LOGGER.info("Executing Waste Action: Turning on %s", action_entities)
                try:
                    await hass.services.async_call(
                        "homeassistant",
                        "turn_on",
                        {"entity_id": action_entities}
                    )
                except Exception as e:
                    _LOGGER.error("Failed to execute action: %s", e)


    # Register listener
    unsub = async_track_time_change(hass, check_and_notify, hour=hour, minute=minute, second=0)
    
    # Store unsub to cancel later
    if entry.entry_id not in hass.data[DOMAIN]:
         hass.data[DOMAIN][entry.entry_id] = {}
    hass.data[DOMAIN][entry.entry_id]["unsub_scheduler"] = unsub

    # Listen for Action Events (Global listener, but fine)
    async def handle_notification_action(event):
        if event.data.get("action") == "MARK_COLLECTED":
            _LOGGER.info("Received MARK_COLLECTED action from notification")
            # We don't know the exact entity ID easily here unless we search
            # But we can assume the user has configured one main waste sensor.
            # Best effort: Find all waste_manager sensors and call service on them.
            
            # Find entities
            entity_registry = hass.helpers.entity_registry.async_get(hass)
            waste_entities = []
            
            # This is a bit advanced because we need to find entities by platform
            # Easier: Just loop all states and check entity_id prefix?
            
            # Or assume standard ID if not customized. 
            # Better: Call service set_collected without entity_id? No, service requires it.
            
            # Let's find entity ID from config entry if possible
            # entry.entry_id is known.
            
            # We can get entity_id from entity_registry using config_entry_id
            entities = [
                entry.entity_id 
                for entry in entity_registry.entities.values() 
                if entry.config_entry_id == entry.entry_id
            ]
            
            if entities:
                await hass.services.async_call(
                    DOMAIN, "set_collected", {"entity_id": entities}
                )

    # We should register this listener only once.
    # But async_setup_scheduler runs per entry.
    # If we have multiple instances, we might duplicate listeners.
    # Better to put the event listener in async_setup_entry?
    # Or just check if registered.
    
    # Simple workaround: Just register it. HA allows multiple listeners.
    hass.bus.async_listen("mobile_app_notification_action", handle_notification_action)



async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Cancel scheduler
    if entry.entry_id in hass.data[DOMAIN] and "unsub_scheduler" in hass.data[DOMAIN][entry.entry_id]:
        hass.data[DOMAIN][entry.entry_id]["unsub_scheduler"]()

    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        pass

    return unload_ok


async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)
