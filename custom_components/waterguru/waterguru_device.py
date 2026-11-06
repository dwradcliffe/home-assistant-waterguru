import re

# timeLeftText is free text from the API, e.g. "12 days left", "7 weeks left", "5 months left".
_TIME_LEFT_RE = re.compile(r"^\s*(\d+)\s*(day|week|month)s?\b", re.IGNORECASE)
_DAYS_PER_UNIT = {"day": 1, "week": 7, "month": 30}


def _parse_days_remaining(text):
    """Convert timeLeftText to a number of days, or None if the format is not recognized."""
    match = _TIME_LEFT_RE.match(text) if isinstance(text, str) else None
    if match is None:
        return None
    return int(match.group(1)) * _DAYS_PER_UNIT[match.group(2).lower()]


class WaterGuruDevice:
    """Representation of a WaterGuru device."""

    def __init__(self, waterBodyData):
        """Initialize the device."""
        self._data = waterBodyData
        self._sensors = dict[str, str]
        self._standard_sensors = {
            'temp': self._data.get('waterTemp', None),
            'rssi': self._data['pods'][0].get('rssiInfo', {}).get('rssi', None),
        }
        for r in self._data['pods'][0].get('refillables', []):
            if r['type'] == 'BATT':
                self._standard_sensors['battery'] = r['pctLeft']
            if r['type'] == 'LAB':
                self._standard_sensors['cassette'] = r['pctLeft']
                if 'timeLeftText' in r:
                    self._standard_sensors['cassette_days_remaining'] = _parse_days_remaining(r['timeLeftText'])
        self._measurements = {measurement['type']: measurement for measurement in self._data.get('measurements', [])}

    @property
    def device_id(self):
        """Return the device ID."""
        return self._data['waterBodyId']

    @property
    def name(self):
        """Return the name of the device."""
        return f"WaterGuru {self._data['name']}"

    @property
    def product_name(self):
        """Return the product name of the device."""
        return self._data['pods'][0]['pod']['product']

    @property
    def serial_number(self):
        """Return the serial number of the device."""
        return str(self._data['pods'][0]['pod']['podId'])

    @property
    def firmware_version(self):
        """Return the firmware version of the device."""
        return self._data['pods'][0]['pod'].get('fwUpdateVersion', None)

    @property
    def sensors(self):
        """Return the sensors of the device."""
        return self._standard_sensors

    @property
    def measurements(self):
        """Return the measurements of the device."""
        return self._measurements

    @property
    def status(self):
        """Return the status of the device."""
        return self._data['status']

    @property
    def last_measurement_time(self):
        """Return the last measurement time."""
        return self._data.get('latestMeasureTime', None)

    @property
    def diagnostics(self):
        """Return the diagnostics of the device."""
        return {
            "name": self.name,
            "product_name": self.product_name,
            "firmware_version": self.firmware_version,
            "status": self.status,
            "last_measurement_time": self.last_measurement_time,
            "standard_sensors": self.sensors,
            "measurements": self.measurements,
            "raw_data": self._data
        }
