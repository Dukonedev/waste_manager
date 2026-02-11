"""Platform for sensor integration."""
from __future__ import annotations

from datetime import date, datetime, timedelta
import logging

from homeassistant.components.sensor import SensorEntity

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv, entity_platform
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import (
    CONF_MONDAY,
    CONF_TUESDAY,
    CONF_WEDNESDAY,
    CONF_THURSDAY,
    CONF_FRIDAY,
    CONF_SATURDAY,
    CONF_SUNDAY,
    CONF_COLLECTION_START,
    CONF_COLLECTION_END,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    entities = [WastePickupSensor(config_entry)]
    
    # Identify unique waste types for separate sensors
    config = config_entry.options if config_entry.options else config_entry.data
    week_schedule = [
        config.get(CONF_MONDAY), config.get(CONF_TUESDAY), config.get(CONF_WEDNESDAY),
        config.get(CONF_THURSDAY), config.get(CONF_FRIDAY), config.get(CONF_SATURDAY),
        config.get(CONF_SUNDAY)
    ]
    
    unique_types = set()
    for day_str in week_schedule:
        if day_str:
             types = [t.strip() for t in day_str.split(",") if t.strip()]
             unique_types.update(types)
             
    for waste_type in unique_types:
        entities.append(WasteTypeSensor(config_entry, waste_type))

    async_add_entities(entities)




class WasteTypeSensor(SensorEntity):
    """Sensor for a specific waste type."""
    
    def __init__(self, config_entry: ConfigEntry, waste_type: str) -> None:
        """Initialize the sensor."""
        self._config_entry = config_entry
        self._waste_type = waste_type
        
        # ID safe name
        safe_type = waste_type.lower().replace(" ", "_")
        self._attr_unique_id = f"waste_manager_{safe_type}"
        self._attr_name = f"Gestione Rifiuti {waste_type}"
        self._attr_icon = "mdi:recycle"
        
        self._attr_native_value = None
        self._attr_extra_state_attributes = {}

    def update(self) -> None:
        """Calculate next pickup for this specific type."""
        config = self._config_entry.options if self._config_entry.options else self._config_entry.data
        
        week_schedule = {
            0: config.get(CONF_MONDAY),
            1: config.get(CONF_TUESDAY),
            2: config.get(CONF_WEDNESDAY),
            3: config.get(CONF_THURSDAY),
            4: config.get(CONF_FRIDAY),
            5: config.get(CONF_SATURDAY),
            6: config.get(CONF_SUNDAY),
        }

        today = dt_util.now().date()
        
        days_until = None
        pickup_date = None
        
        # Parse Exceptions
        exceptions_map = {}
        exceptions_text = config.get("exceptions", "")
        if exceptions_text:
            for line in exceptions_text.splitlines():
                if ":" in line:
                    d_str, v = line.split(":", 1)
                    try:
                        d, m = map(int, d_str.strip().split("/"))
                        exceptions_map[(d, m)] = v.strip()
                    except ValueError:
                        pass

        # Find next occurrence
        for i in range(30): # Look ahead 1 month
            check_date = today + timedelta(days=i)
            
            # Check Exception
            waste_type_raw = None
            if (check_date.day, check_date.month) in exceptions_map:
                waste_type_raw = exceptions_map[(check_date.day, check_date.month)]
                if waste_type_raw.lower() == "nessuno":
                    waste_type_raw = None
            else:
                waste_type_raw = week_schedule.get(check_date.weekday())
            
            if waste_type_raw:
                types = [t.strip().lower() for t in waste_type_raw.split(",")]
                if self._waste_type.lower() in types:
                    days_until = i
                    pickup_date = check_date
                    break
        
        if days_until is not None:
             if days_until == 0:
                 self._attr_native_value = "Oggi"
             elif days_until == 1:
                 self._attr_native_value = "Domani"
             else:
                 self._attr_native_value = f"Tra {days_until} giorni"
                 
             self._attr_extra_state_attributes = {
                 "days_until": days_until,
                 "pickup_date": pickup_date.isoformat()
             }
             
             # Color
             colors = config.get("waste_colors", {})
             if self._waste_type in colors and colors[self._waste_type] != "default":
                 self._attr_extra_state_attributes["color"] = colors[self._waste_type]
                 
        else:
             self._attr_native_value = "Non programmato"
             self._attr_extra_state_attributes = {}


class WastePickupSensor(SensorEntity):
    """Representation of a Waste Pickup Sensor."""

    _attr_has_entity_name = True
    _attr_name = "Next Waste Pickup"
    _attr_unique_id = "waste_manager_next_pickup"

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        self._config_entry = config_entry
        self._attr_native_value = None
        self._attr_extra_state_attributes = {}
        self._attr_icon = "mdi:delete-empty"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self._attr_native_value

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return self._attr_extra_state_attributes

    @property
    def icon(self):
        """Return the icon of the sensor."""
        return self._attr_icon

    def update(self) -> None:
        """Fetch new state data for the sensor."""
        # Get configuration from options if available, otherwise data
        config = self._config_entry.options if self._config_entry.options else self._config_entry.data
        
        # Map days to config keys
        week_schedule = {
            0: config.get(CONF_MONDAY),
            1: config.get(CONF_TUESDAY),
            2: config.get(CONF_WEDNESDAY),
            3: config.get(CONF_THURSDAY),
            4: config.get(CONF_FRIDAY),
            5: config.get(CONF_SATURDAY),
            6: config.get(CONF_SUNDAY),
        }

        today = dt_util.now().date()
        today_weekday = today.weekday()

        found_pickup_raw = None
        days_until = None
        pickup_date = None

        # Parse Exceptions
        exceptions_map = {}
        exceptions_text = config.get("exceptions", "")
        if exceptions_text:
            for line in exceptions_text.splitlines():
                if ":" in line:
                    d_str, v = line.split(":", 1)
                    try:
                        d, m = map(int, d_str.strip().split("/"))
                        exceptions_map[(d, m)] = v.strip()
                    except ValueError:
                        pass

        # Calculate upcoming schedule
        # Check next 15 days
        upcoming_schedule = []
        for i in range(15): 
            check_date = today + timedelta(days=i)
            
            # Check Exception
            waste_type_raw = None
            if (check_date.day, check_date.month) in exceptions_map:
                waste_type_raw = exceptions_map[(check_date.day, check_date.month)]
                if waste_type_raw.lower() == "nessuno":
                    waste_type_raw = None
            else:
                waste_type_raw = week_schedule.get(check_date.weekday())
            
            if waste_type_raw and waste_type_raw.strip():
                waste_types = [w.strip() for w in waste_type_raw.split(",") if w.strip()]
                
                day_name_map = {
                    0: "Lunedì", 1: "Martedì", 2: "Mercoledì", 3: "Giovedì", 
                    4: "Venerdì", 5: "Sabato", 6: "Domenica"
                }
                
                # Determine upcoming items (limit to 5)
                if len(upcoming_schedule) < 5:
                    upcoming_schedule.append({
                        "date": check_date.isoformat(),
                        "day": day_name_map.get(check_date.weekday(), ""),
                        "waste_types": waste_types,
                        "days_until": i
                    })
                
                # Check for NEXT pickup (only once)
                if found_pickup_raw is None:
                    found_pickup_raw = waste_type_raw
                    days_until = i
                    pickup_date = check_date
                    
        if found_pickup_raw:
            # Handle multiple types separated by comma
            waste_types = [w.strip() for w in found_pickup_raw.split(",") if w.strip()]
            found_pickup = ", ".join(waste_types)

            if days_until == 0:
                self._attr_native_value = f"{found_pickup} (Oggi)"
            elif days_until == 1:
                self._attr_native_value = f"{found_pickup} (Domani)"
            else:
                self._attr_native_value = f"{found_pickup} (Tra {days_until} giorni)"
            
            self._attr_extra_state_attributes = {
                "waste_type": found_pickup,
                "waste_types": waste_types,
                "days_until": days_until,
                "pickup_date": pickup_date.isoformat(),
                "upcoming_schedule": upcoming_schedule,
                "collection_start": config.get(CONF_COLLECTION_START, ""),
                "collection_end": config.get(CONF_COLLECTION_END, ""),
                "waste_icons": config.get("waste_icons", {}),
                "waste_colors": config.get("waste_colors", {}),
            }

            # Update icon based on keywords in the full string
            waste_lower = found_pickup.lower()
            if "plastica" in waste_lower:
                self._attr_icon = "mdi:recycle"
            elif "umido" in waste_lower:
                self._attr_icon = "mdi:food-apple"
            elif "carta" in waste_lower:
                self._attr_icon = "mdi:newspaper"
            else:
                self._attr_icon = "mdi:delete-empty"
        else:
            self._attr_native_value = "Nessun ritiro programmato"
            self._attr_extra_state_attributes = {
                "waste_type": None,
                "waste_types": [],
                "days_until": None,
                "pickup_date": None,
                "upcoming_schedule": []
            }
            self._attr_icon = "mdi:delete-empty"
