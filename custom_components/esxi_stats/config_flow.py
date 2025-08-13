"""Config flow for esxi_stats integration."""
import logging
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback

from .const import (
    CONF_DS_STATE,
    CONF_LIC_STATE,
    CONF_NOTIFY,
    DOMAIN,
    DEFAULT_PORT,
    DEFAULT_DS_STATE,
    DEFAULT_LIC_STATE,
    DATASTORE_STATES,
    LICENSE_STATES,
)
from .esxi import esx_connect, esx_disconnect


_LOGGER = logging.getLogger(__name__)


@config_entries.HANDLERS.register(DOMAIN)
class ESXiStatsFlowHandler(config_entries.ConfigFlow):
    """Config flow for ESXi Stats."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return ESXiStatsOptionsFlow(config_entry)

    def __init__(self):
        """Initialize."""
        self._errors = {}

    async def async_step_user(
        self, user_input={}
    ):  # pylint: disable=dangerous-default-value
        """Handle a flow initialized by the user."""
        self._errors = {}
        if self.hass.data.get(DOMAIN):
            return self.async_abort(reason="single_instance_allowed")

        if user_input is not None:
            # Check if entered host is already in HomeAssistant
            existing = await self._check_existing(user_input["host"])
            if existing:
                return self.async_abort(reason="already_configured")

            # If it is not, continue with communication test
            valid = await self.hass.async_add_executor_job(
                self._test_communication,
                user_input["host"],
                user_input["port"],
                user_input["verify_ssl"],
                user_input["username"],
                user_input["password"],
            )
            if valid:
                return self.async_create_entry(
                    title=user_input["host"], data=user_input
                )
            else:
                self._errors["base"] = "communication"

            return await self._show_config_form(user_input)

        return await self._show_config_form(user_input)

    async def _show_config_form(self, user_input):
        """Show the configuration form to edit location data."""
        # Defaults
        host = ""
        port = DEFAULT_PORT
        username = ""
        password = ""
        verify_ssl = False
        vmhost = True
        datastore = True
        license = True
        vm = True

        if user_input is not None:
            if "host" in user_input:
                host = user_input["host"]
            if "port" in user_input:
                port = user_input["port"]
            if "username" in user_input:
                username = user_input["username"]
            if "password" in user_input:
                password = user_input["password"]
            if "verify_ssl" in user_input:
                verify_ssl = user_input["verify_ssl"]
            if "vmhost" in user_input:
                vmhost = user_input["vmhost"]
            if "datastore" in user_input:
                datastore = user_input["datastore"]
            if "license" in user_input:
                license = user_input["license"]
            if "vm" in user_input:
                vm = user_input["vm"]

        data_schema = {
            vol.Required("host", default=host): str,
            vol.Required("port", default=port): int,
            vol.Required("username", default=username): str,
            vol.Required("password", default=password): str,
            vol.Optional("verify_ssl", default=verify_ssl): bool,
            vol.Optional("vmhost", default=vmhost): bool,
            vol.Optional("datastore", default=datastore): bool,
            vol.Optional("license", default=license): bool,
            vol.Optional("vm", default=vm): bool,
        }
        return self.async_show_form(
            step_id="user", data_schema=vol.Schema(data_schema), errors=self._errors
        )

    async def async_step_import(self, user_input):
        """Import a config entry.

        Special type of import, we're not actually going to store any data.
        Instead, we're going to rely on the values that are in config file.
        """
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        return self.async_create_entry(title="configuration.yaml", data={})

    async def _check_existing(self, host):
        for entry in self._async_current_entries():
            if host == entry.data.get("host"):
                return True

    def _test_communication(self, host, port, verify_ssl, username, password):
        """Return true if the communication is ok."""
        try:
            conn = esx_connect(host, username, password, port, verify_ssl)
            _LOGGER.debug(conn)

            esx_disconnect(conn)
            return True
        except Exception as exception:  # pylint: disable=broad-except
            _LOGGER.error(exception)
            return False


class ESXiStatsOptionsFlow(config_entries.OptionsFlow):
    """Handle ESXi Stats options."""

    def __init__(self, config_entry):
        """Initialize ESXi Stats options flow."""
        self.config_entry = config_entry
        self.options = dict(config_entry.options)

    async def async_step_init(self, user_input=None):
        """Manage ESXi Stats options."""
        return await self.async_step_esxi_options()

    async def async_step_esxi_options(self, user_input=None):
        """Manage ESXi Stats Options."""
        if user_input is not None:
            self.options[CONF_DS_STATE] = user_input[CONF_DS_STATE]
            self.options[CONF_LIC_STATE] = user_input[CONF_LIC_STATE]
            self.options[CONF_NOTIFY] = user_input[CONF_NOTIFY]
            return self.async_create_entry(title="", data=self.options)

        return self.async_show_form(
            step_id="esxi_options",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_DS_STATE,
                        default=self.config_entry.options.get(
                            CONF_DS_STATE, DEFAULT_DS_STATE
                        ),
                    ): vol.In(DATASTORE_STATES),
                    vol.Optional(
                        CONF_LIC_STATE,
                        default=self.config_entry.options.get(
                            CONF_LIC_STATE, DEFAULT_LIC_STATE
                        ),
                    ): vol.In(LICENSE_STATES),
                    vol.Optional(
                        CONF_NOTIFY,
                        default=self.config_entry.options.get(CONF_NOTIFY, True),
                    ): bool,
                }
            ),
        )
