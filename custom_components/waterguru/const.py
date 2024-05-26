"""Const for WaterGuru."""

from enum import StrEnum

DOMAIN = "waterguru"

class WaterGuruEntityAttributes(StrEnum):
  """Possible entity attributes."""

  LAST_MEASUREMENT = "last_measurement"
  DESC = "description"
  STATUS_COLOR = "status_color"
  ADVICE = "advice"
