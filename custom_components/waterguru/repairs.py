"""Repairs flows for the WaterGuru integration."""

from __future__ import annotations

import voluptuous as vol

from homeassistant import data_entry_flow
from homeassistant.components.repairs import RepairsFlow
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN, CASSETTE_ISSUE_PREFIX

class CassetteEmptyRepairFlow(RepairsFlow):
    """Handler for an issue fixing flow."""

    async def async_step_init(
        self, user_input: dict[str, str] | None = None
    ) -> data_entry_flow.FlowResult:
        """Handle the first step of a fix flow."""
        return await self.async_step_confirm()

    async def async_step_confirm(
        self, user_input: dict[str, str] | None = None
    ) -> data_entry_flow.FlowResult:
        """Handle the confirm step of a fix flow."""
        assert self.data is not None
        device_id = self.data["device_id"]
        name = self.data["name"]

        if user_input is not None:
            # Lookup the button's entity_id
            registry = er.async_get(self.hass)
            button_unique_id = f"{device_id}_replace_cassette"
            button_entity_id = registry.async_get_entity_id("button", DOMAIN, button_unique_id)

            if button_entity_id is None:
                return self.async_abort(reason="entity_not_found")

            await self.hass.services.async_call(
                "button", "press", {"entity_id": button_entity_id}
            )

            return self.async_create_entry(title="", data={})

        return self.async_show_form(
            step_id="confirm",
            data_schema=vol.Schema({}),
            description_placeholders={"name": name},
        )

async def async_create_fix_flow(
    hass: HomeAssistant,
    issue_id: str,
    data: dict[str, str | int | float | None] | None,
) -> RepairsFlow:
    """Create flow."""
    if issue_id.startswith(CASSETTE_ISSUE_PREFIX):
        return CassetteEmptyRepairFlow()
