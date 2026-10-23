# WaterGuru Home Assistant Integration

This is a Home Assistant integration for the WaterGuru Automated Smart Pool Water Monitor product.

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=dwradcliffe&repository=home-assistant-waterguru)

NOTE: This is not any kind of official integration or support. Use at your own risk.

This integration requires Home Assistant 2024.4 or later.

## Features

### Cassette Replacement
The integration provides a native button entity to reset the cassette life to 100% after a physical replacement. 
* **Repair Flow:** When the API reports a cassette is empty, Home Assistant will automatically generate a repair issue. Opening the repair gives you the choice to confirm the physical replacement (which automatically triggers the reset) or ignore the issue for now; ignored issues stay hidden until the cassette is refilled and reported empty again.
* **Safety Override:** To prevent accidental resets, the reset button will fail to execute if the cassette is not completely empty. To replace a cassette early, you must first toggle on the "Temporarily Allow Early Cassette Replacement" switch before pressing the reset button.

### Manual Measurement
The integration provides a button entity to request a manual water measurement. Because the WaterGuru pod operates on battery power, it sleeps to conserve energy and only connects to the network every 30 minutes. When this button is pressed, the API instructs the device to perform a measurement during its next scheduled check-in. As a result, it can take up to 45 minutes for the new measurement data to reflect in Home Assistant.

## Usage
1. Install HACS if you haven't already (see [installation guide](https://hacs.xyz/docs/setup/prerequisites)).
2. Add custom repository `https://github.com/dwradcliffe/home-assistant-waterguru` as "Integration" in the settings tab of HACS.
3. Find and install `WaterGuru` integration in HACS's "Integrations" tab.
4. Restart Home Assistant.
5. Go to your integrations page and click `Add Integration` and look for `WaterGuru`.

## References
The code to connect to WaterGuru is taken directly from https://github.com/bdwilson/waterguru-api and wrapped in a HA integration. Thanks also to https://community.home-assistant.io/t/water-guru-integration/291917
