import os
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    EntitySelector,
    EntitySelectorConfig,
    TextSelector,
    TextSelectorConfig,
)
from .const import (
    DOMAIN,
    CONF_MONDAY,
    CONF_TUESDAY,
    CONF_WEDNESDAY,
    CONF_THURSDAY,
    CONF_FRIDAY,
    CONF_SATURDAY,
    CONF_SUNDAY,
    CONF_COLLECTION_START,
    CONF_COLLECTION_END,
    CONF_NOTIFY_SERVICE,
    CONF_NOTIFY_TIME,
    CONF_ACTION_ENTITY,
)

class WasteManagerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Waste Manager."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        if user_input is not None:
            return self.async_create_entry(title="Gestione Rifiuti", data=user_input)

        data_schema = vol.Schema(
            {
                vol.Optional(CONF_MONDAY): str,
                vol.Optional(CONF_TUESDAY): str,
                vol.Optional(CONF_WEDNESDAY): str,
                vol.Optional(CONF_THURSDAY): str,
                vol.Optional(CONF_FRIDAY): str,
                vol.Optional(CONF_SATURDAY): str,
                vol.Optional(CONF_SUNDAY): str,
                vol.Optional(CONF_COLLECTION_START): str,
                vol.Optional(CONF_COLLECTION_END): str,
            }
        )

        return self.async_show_form(step_id="user", data_schema=data_schema)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return WasteManagerOptionsFlowHandler(config_entry)


class WasteManagerOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Waste Manager."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        self._config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options in a single step."""
        if user_input is not None:
             # Extract icon and color mappings
             waste_icons = {}
             waste_colors = {}
             clean_input = user_input.copy()
             
             keys_to_remove = []
             for key, value in user_input.items():
                 if key.startswith("icon_"):
                     waste_type = key[5:] # len("icon_") is 5
                     waste_icons[waste_type] = value
                     keys_to_remove.append(key)
                 elif key.startswith("color_"):
                     waste_type = key[6:] # len("color_") is 6
                     waste_colors[waste_type] = value
                     keys_to_remove.append(key)
             
             # Clean input
             for k in keys_to_remove:
                 clean_input.pop(k)
             
             # Save to config
             clean_input["waste_icons"] = waste_icons
             clean_input["waste_colors"] = waste_colors
             
             return self.async_create_entry(title="", data=clean_input)

        try:
            current_options = self._config_entry.options
            current_data = self._config_entry.data
            
            # Helper to get current value
            def get_current(key, default=None):
                return current_options.get(key) or current_data.get(key) or default

            # --- 1. Schedule Section ---
            schema_dict = {
                vol.Optional(CONF_MONDAY, default=get_current(CONF_MONDAY, "")): str,
                vol.Optional(CONF_TUESDAY, default=get_current(CONF_TUESDAY, "")): str,
                vol.Optional(CONF_WEDNESDAY, default=get_current(CONF_WEDNESDAY, "")): str,
                vol.Optional(CONF_THURSDAY, default=get_current(CONF_THURSDAY, "")): str,
                vol.Optional(CONF_FRIDAY, default=get_current(CONF_FRIDAY, "")): str,
                vol.Optional(CONF_SATURDAY, default=get_current(CONF_SATURDAY, "")): str,
                vol.Optional(CONF_SUNDAY, default=get_current(CONF_SUNDAY, "")): str,
                vol.Optional(CONF_COLLECTION_START, default=get_current(CONF_COLLECTION_START, "")): str,
                vol.Optional(CONF_COLLECTION_END, default=get_current(CONF_COLLECTION_END, "")): str,
            }

            # --- 2. Notifications Section ---
            services = self.hass.services.async_services()
            notify_services = []
            if "notify" in services:
                 notify_services = [f"notify.{s}" for s in services["notify"]]
            notify_services = sorted(notify_services)
            
            default_service = get_current(CONF_NOTIFY_SERVICE, "")
            default_time = get_current(CONF_NOTIFY_TIME, "20:00")
            default_action = get_current(CONF_ACTION_ENTITY, [])
            if isinstance(default_action, str) and default_action:
                 default_action = [default_action]

            schema_dict[vol.Optional(CONF_NOTIFY_SERVICE, default=default_service)] = SelectSelector(
                SelectSelectorConfig(
                    options=notify_services,
                    mode=SelectSelectorMode.DROPDOWN,
                    custom_value=True
                )
            )
            schema_dict[vol.Optional(CONF_NOTIFY_TIME, default=default_time)] = str
            schema_dict[vol.Optional(CONF_ACTION_ENTITY, default=default_action)] = EntitySelector(
                EntitySelectorConfig(
                    multiple=True,
                    domain=["switch", "light", "script", "automation", "input_boolean", "input_button", "scene"]
                )
            )

            # --- 3. Icon Mapping Section ---
            # Identify unique types from CURRENT config
            config_source = {**current_data, **current_options}
            
            schedule_keys = [
                CONF_MONDAY, CONF_TUESDAY, CONF_WEDNESDAY, CONF_THURSDAY,
                CONF_FRIDAY, CONF_SATURDAY, CONF_SUNDAY
            ]
            unique_types = set()
            for key in schedule_keys:
                raw_value = config_source.get(key, "")
                if raw_value:
                    types = [t.strip() for t in raw_value.split(",") if t.strip()]
                    unique_types.update(types)
            
            if unique_types:
                images_dir = self.hass.config.path("custom_components/waste_manager/rifiuti")
                available_images = ["default.png"]
                if os.path.exists(images_dir):
                    for file in os.listdir(images_dir):
                        if file.endswith(".png"):
                            available_images.append(file)
                available_images = sorted(list(set(available_images)))
                
                # Get current icons and colors mapping
                current_icons = config_source.get("waste_icons", {})
                current_colors = config_source.get("waste_colors", {})
                
                if not isinstance(current_icons, dict): current_icons = {}
                if not isinstance(current_colors, dict): current_colors = {}

                # Colors available
                # Logic: Map readable names to CSS values or just Hex?
                # Let's use standard recycling colors names.
                color_options = [
                    {"label": "Nessuno", "value": "default"},
                    {"label": "Giallo (Plastica)", "value": "#FFEB3B"},
                    {"label": "Blu (Carta)", "value": "#2196F3"},
                    {"label": "Marrone (Umido)", "value": "#795548"},
                    {"label": "Verde (Vetro)", "value": "#4CAF50"},
                    {"label": "Grigio (Secco)", "value": "#9E9E9E"},
                    {"label": "Nero (Indifferenziata)", "value": "#212121"},
                    {"label": "Bianco", "value": "#FFFFFF"},
                    {"label": "Viola", "value": "#9C27B0"},
                    {"label": "Arancione", "value": "#FF9800"},
                    {"label": "Rosso", "value": "#F44336"}
                ]
                
                # Make simple list for selector if object dict not supported in old HA versions?
                # SelectSelector handles lists of dicts {value, label} well.

                for waste_type in sorted(unique_types):
                     # --- Icon ---
                     default_icon = "default.png"
                     if waste_type in current_icons:
                         default_icon = current_icons[waste_type]
                     else:
                         type_lower = waste_type.lower()
                         if "plastica" in type_lower: default_icon = "plastica.png"
                         elif "carta" in type_lower: default_icon = "carta.png"
                         elif "umido" in type_lower: default_icon = "umido.png"
                         elif "vetro" in type_lower: default_icon = "vetro.png"
                         elif "secco" in type_lower or "indifferenziata" in type_lower: default_icon = "indifferenziata.png"
                         elif "metallo" in type_lower: default_icon = "metallo.png"
                         elif "verde" in type_lower or "sfalci" in type_lower: default_icon = "verde.png"
                         
                         if default_icon not in available_images:
                             default_icon = "default.png"

                     schema_dict[vol.Optional(f"icon_{waste_type}", default=default_icon)] = SelectSelector(
                         SelectSelectorConfig(
                             options=available_images,
                             mode=SelectSelectorMode.DROPDOWN,
                         )
                     )
                     
                     # --- Color ---
                     default_color = "default"
                     if waste_type in current_colors:
                         default_color = current_colors[waste_type]
                     else:
                         # Auto-guess color
                         type_lower = waste_type.lower()
                         if "plastica" in type_lower: default_color = "#FFEB3B" # Yellow
                         elif "carta" in type_lower: default_color = "#2196F3" # Blue
                         elif "umido" in type_lower or "organico" in type_lower: default_color = "#795548" # Brown
                         elif "vetro" in type_lower: default_color = "#4CAF50" # Green
                         elif "secco" in type_lower or "indifferenziata" in type_lower: default_color = "#9E9E9E" # Grey
                         elif "metallo" in type_lower: default_color = "#FF9800" # Orange? Metal
                         elif "verde" in type_lower or "sfalci" in type_lower: default_color = "#4CAF50" # Green
                     
                     # Check if guessed is in options, else custom?
                     # We only allow options for now to keep it simple.
                     if not any(opt["value"] == default_color for opt in color_options):
                         default_color = "default"
                         
                     schema_dict[vol.Optional(f"color_{waste_type}", default=default_color)] = SelectSelector(
                         SelectSelectorConfig(
                             options=color_options,
                             mode=SelectSelectorMode.DROPDOWN,
                         )
                     )

            # --- 4. Exceptions Section ---
            default_exceptions = get_current("exceptions", "")
            
            schema_dict[vol.Optional("exceptions", default=default_exceptions)] = TextSelector(
                TextSelectorConfig(
                    multiline=True
                )
            )

            data_schema = vol.Schema(schema_dict)

        except Exception as e:
            import logging
            _LOGGER = logging.getLogger(__name__)
            _LOGGER.error("Waste Manager Options Flow Error: %s", e)
            raise e

        return self.async_show_form(step_id="init", data_schema=data_schema)
