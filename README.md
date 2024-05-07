# WaterGuru Home Assistant Integration

This is a Home Assistant integration for the WaterGuru Automated Smart Pool Water Monitor product.

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=dwradcliffe&repository=home-assistant-waterguru)

NOTE: This is not any kind of official integration or support. Use at your own risk.

This integration requires Home Assistant 2024.4 or later.

## Usage
1. Install HACS if you haven't already (see [installation guide](https://hacs.xyz/docs/setup/prerequisites)).
2. Add custom repository `https://github.com/dwradcliffe/home-assistant-waterguru` as "Integration" in the settings tab of HACS.
3. Find and install `WaterGuru` integration in HACS's "Integrations" tab.
4. Restart Home Assistant.
5. Go to your integrations page and click `Add Integration` and look for `WaterGuru`.

## References
The code to connect to WaterGuru is taken directly from https://github.com/bdwilson/waterguru-api and wrapped in a HA integration. Thanks also to https://community.home-assistant.io/t/water-guru-integration/291917
