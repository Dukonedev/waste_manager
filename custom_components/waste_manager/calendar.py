"""Calendar platform for Waste Manager."""
from __future__ import annotations

import datetime
from datetime import timedelta
import re

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    CONF_MONDAY,
    CONF_TUESDAY,
    CONF_WEDNESDAY,
    CONF_THURSDAY,
    CONF_FRIDAY,
    CONF_SATURDAY,
    CONF_SUNDAY,
    CONF_EXCEPTIONS,
)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the calendar platform."""
    async_add_entities([WasteManagerCalendar(config_entry)])


class WasteManagerCalendar(CalendarEntity):
    """Waste Manager Calendar Entity."""

    _attr_has_entity_name = True
    _attr_name = "Calendario Rifiuti"
    _attr_unique_id = "waste_manager_calendar"

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize the calendar."""
        self._config_entry = config_entry
        self._event = None

    @property
    def event(self) -> CalendarEvent | None:
        """Return the next upcoming event."""
        return self._event

    async def async_get_events(
        self, hass: HomeAssistant, start_date: datetime.datetime, end_date: datetime.datetime
    ) -> list[CalendarEvent]:
        """Return calendar events within a datetime range."""
        events = []
        
        config = self._config_entry.options if self._config_entry.options else self._config_entry.data
        
        # Schedule Map
        week_schedule = {
            0: config.get(CONF_MONDAY),
            1: config.get(CONF_TUESDAY),
            2: config.get(CONF_WEDNESDAY),
            3: config.get(CONF_THURSDAY),
            4: config.get(CONF_FRIDAY),
            5: config.get(CONF_SATURDAY),
            6: config.get(CONF_SUNDAY),
        }
        
        # Parse Exceptions
        # Format "DD/MM: Type"
        exceptions_map = {}
        exceptions_text = config.get(CONF_EXCEPTIONS, "")
        if exceptions_text:
            lines = exceptions_text.splitlines()
            for line in lines:
                if ":" in line:
                    date_part, value = line.split(":", 1)
                    date_part = date_part.strip()
                    value = value.strip()
                    
                    # Try DD/MM
                    try:
                        d, m = map(int, date_part.split("/"))
                        exceptions_map[(d, m)] = value
                    except ValueError:
                        pass

        current_date = start_date.date()
        end_date_date = end_date.date()
        
        while current_date <= end_date_date:
            waste_type = None
            
            # Check Exception
            if (current_date.day, current_date.month) in exceptions_map:
                waste_type = exceptions_map[(current_date.day, current_date.month)]
                if waste_type.lower() == "nessuno":
                    waste_type = None
            else:
                # Check Schedule
                weekday = current_date.weekday()
                waste_type = week_schedule.get(weekday)

            if waste_type:
                # Handle multiple types
                types = [t.strip() for t in waste_type.split(",") if t.strip()]
                
                # Create an event for each type or combined?
                # Combined is cleaner for calendar view usually, but separate events allow distinct colors if supported?
                # HA Calendar usually distinct events.
                
                summary = f"Ritiro: {', '.join(types)}"
                
                events.append(
                    CalendarEvent(
                        summary=summary,
                        start=current_date,
                        end=current_date + timedelta(days=1),
                        description=f"Raccolta {waste_type}",
                        location=""
                    )
                )

            current_date += timedelta(days=1)

        return events
