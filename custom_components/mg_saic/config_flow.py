import logging
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from .const import (
    DOMAIN,
    LOGGER,
    COUNTRY_CODES,
    UPDATE_INTERVAL,
    UPDATE_INTERVAL_CHARGING,
    REGION_CHOICES,
    REGION_BASE_URIS,
)
from saic_ismart_client_ng import SaicApi
from saic_ismart_client_ng.model import SaicApiConfiguration

_LOGGER = logging.getLogger(__name__)


@callback
def configured_instances(hass):
    """Return a set of configured MG SAIC instances."""
    return set(
        entry.data.get("username")
        for entry in hass.config_entries.async_entries(DOMAIN)
    )


class SAICMGConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for MG SAIC integration."""

    VERSION = 1

    def __init__(self):
        self.login_type = None
        self.username = None
        self.password = None
        self.country_code = None
        self.region = None
        self.vin = None
        self.vehicles = []
        self.vehicle_type = None  # Store vehicle type (BEV, PHEV, HEV, ICE)

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            self.login_type = user_input["login_type"]
            return await self.async_step_login_data()

        data_schema = vol.Schema(
            {
                vol.Required("login_type"): vol.In(["email", "phone"]),
            }
        )

        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )

    async def async_step_login_data(self, user_input=None):
        errors = {}
        if user_input is not None:
            self.username = user_input["username"]
            self.password = user_input["password"]
            username_is_email = self.login_type == "email"

            self.region = user_input["region"]

            if not username_is_email:
                self.country_code = user_input["country_code"].replace("+", "")
                self.username = self.username.replace(" ", "").replace("+", "")

            try:
                await self.fetch_vehicle_data(username_is_email)
                return await self.async_step_select_vehicle()
            except Exception as e:
                errors["base"] = "auth"
                LOGGER.error(f"Failed to authenticate or fetch vehicle data: {e}")

        if self.login_type == "email":
            data_schema = vol.Schema(
                {
                    vol.Required("username"): str,
                    vol.Required("password"): str,
                    vol.Required("region"): vol.In(REGION_CHOICES),
                }
            )
        else:  # phone login
            country_options = {code["code"]: code["code"] for code in COUNTRY_CODES}
            data_schema = vol.Schema(
                {
                    vol.Required("country_code"): vol.In(country_options),
                    vol.Required("username"): str,
                    vol.Required("password"): str,
                    vol.Required("region"): vol.In(REGION_CHOICES),
                }
            )

        return self.async_show_form(
            step_id="login_data", data_schema=data_schema, errors=errors
        )

    async def async_step_select_vehicle(self, user_input=None):
        errors = {}
        if user_input is not None:
            self.vin = user_input["vin"]
            self.vehicle_type = user_input["vehicle_type"]  # Store vehicle type
            return self.async_create_entry(
                title=f"MG SAIC - {self.vin}",
                data={
                    "username": self.username,
                    "password": self.password,
                    "country_code": self.country_code,
                    "region": self.region,
                    "vin": self.vin,
                    "login_type": self.login_type,
                    "vehicle_type": self.vehicle_type,  # Include vehicle type in the entry
                },
            )

        # Add vehicle_type selection with fallback for user confirmation
        data_schema = vol.Schema(
            {
                vol.Required("vin"): vol.In(self.vehicles),
                vol.Required("vehicle_type"): vol.In(["BEV", "PHEV", "HEV", "ICE"]),
            }
        )

        return self.async_show_form(
            step_id="select_vehicle", data_schema=data_schema, errors=errors
        )

    async def fetch_vehicle_data(self, username_is_email):
        """Authenticate and fetch vehicle data."""

        # Get the base_url for the selected region
        base_uri = REGION_BASE_URIS.get(self.region)
        if not base_uri:
            raise ValueError(f"Base URL not defined for region: {self.region}")

        config = SaicApiConfiguration(
            username=self.username,
            password=self.password,
            base_uri=base_uri,
            phone_country_code=self.country_code if not username_is_email else None,
            username_is_email=username_is_email,
        )

        LOGGER.debug(
            "Logging in with Username: %s, Country Code: %s, Email: %s, Region: %s, Base URL: %s",
            self.username,
            self.country_code,
            username_is_email,
            self.region,
            base_uri,
        )

        # Initialize SaicApi in the executor to avoid blocking the event loop
        saic_api = await self.hass.async_add_executor_job(SaicApi, config)

        try:
            await saic_api.login()
            vehicle_list_resp = await saic_api.vehicle_list()
            LOGGER.debug("Vehicle list response: %s", vehicle_list_resp)

            # Use hasattr instead of `in` for checking object attributes
            if (
                not hasattr(vehicle_list_resp, "vinList")
                or not vehicle_list_resp.vinList
            ):
                raise Exception("Vehicle list API returned no vehicles")

            # Now safely iterate over vinList
            self.vehicles = [car.vin for car in vehicle_list_resp.vinList]
            LOGGER.info("Fetched vehicle data successfully.")
        except Exception as e:
            LOGGER.error("Error fetching vehicle data: %s", e)
            raise

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return SAICMGOptionsFlowHandler(config_entry)


class SAICMGOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for MG SAIC integration."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, data=None):
        """Manage the options."""
        if data is not None:
            return self.async_create_entry(title="", data=data)

        data = vol.Schema(
            {
                vol.Optional(
                    "scan_interval",
                    default=self.config_entry.options.get(
                        "scan_interval", int(UPDATE_INTERVAL.total_seconds())
                    ),
                ): vol.All(vol.Coerce(int), vol.Range(min=60)),
                vol.Optional(
                    "charging_scan_interval",
                    default=self.config_entry.options.get(
                        "charging_scan_interval",
                        int(UPDATE_INTERVAL_CHARGING.total_seconds()),
                    ),
                ): vol.All(vol.Coerce(int), vol.Range(min=60)),
            }
        )

        return self.async_show_form(step_id="init", data_schema=data)
