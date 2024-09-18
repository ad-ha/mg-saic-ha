import logging
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from .const import DOMAIN, LOGGER, COUNTRY_CODES
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
                    vol.Required("region"): vol.In(["EU", "China", "Asia"]),
                }
            )
        else:  # phone login
            country_options = {code["code"]: code["code"] for code in COUNTRY_CODES}
            data_schema = vol.Schema(
                {
                    vol.Required("country_code"): vol.In(country_options),
                    vol.Required("username"): str,
                    vol.Required("password"): str,
                    vol.Required("region"): vol.In(["EU", "China", "Asia"]),
                }
            )

        return self.async_show_form(
            step_id="login_data", data_schema=data_schema, errors=errors
        )

    async def async_step_select_vehicle(self, user_input=None):
        errors = {}
        if user_input is not None:
            self.vin = user_input["vin"]
            return self.async_create_entry(
                title=f"MG SAIC - {self.vin}",
                data={
                    "username": self.username,
                    "password": self.password,
                    "country_code": self.country_code,
                    "region": self.region,
                    "vin": self.vin,
                    "login_type": self.login_type,
                },
            )

        data_schema = vol.Schema(
            {
                vol.Required("vin"): vol.In(self.vehicles),
            }
        )

        return self.async_show_form(
            step_id="select_vehicle", data_schema=data_schema, errors=errors
        )

    async def fetch_vehicle_data(self, username_is_email):
        """Authenticate and fetch vehicle data."""

        config = SaicApiConfiguration(
            username=self.username,
            password=self.password,
            region=self.region,
            phone_country_code=self.country_code if not username_is_email else None,
            username_is_email=username_is_email,
        )

        LOGGER.debug(
            "Logging in with username: %s, country_code: %s, is_email: %s, region: %s",
            self.username,
            self.country_code,
            username_is_email,
            self.region,
        )

        saic_api = SaicApi(config)

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

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options_schema = vol.Schema(
            {
                vol.Optional(
                    "scan_interval",
                    default=self.config_entry.options.get("scan_interval", 300),
                ): vol.All(vol.Coerce(int), vol.Range(min=60)),
            }
        )

        return self.async_show_form(step_id="init", data_schema=options_schema)
