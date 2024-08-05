# config_flow.py

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from .const import DOMAIN, LOGGER, COUNTRY_CODES
from saic_ismart_client_ng import SaicApi
from saic_ismart_client_ng.model import SaicApiConfiguration


@callback
def configured_instances(hass):
    """Return a set of configured MG SAIC instances."""
    return set(
        entry.data.get("username")
        for entry in hass.config_entries.async_entries(DOMAIN)
    )


class SAICMGConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

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
            self.region = user_input["region"]
            username_is_email = self.login_type == "email"

            if self.login_type == "phone":
                self.country_code = user_input["country_code"]
                self.username = f"{self.country_code}{self.username}"

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
        else:
            country_options = {
                f"{code['code']} - {code['country']}": code["code"]
                for code in COUNTRY_CODES
            }
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
            phone_country_code=self.country_code,
            username_is_email=username_is_email,
        )
        saic_api = SaicApi(config)

        await saic_api.login()
        vehicle_list_resp = await saic_api.vehicle_list()
        self.vehicles = [car.vin for car in vehicle_list_resp.vinList]
