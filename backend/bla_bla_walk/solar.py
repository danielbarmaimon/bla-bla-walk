"""Geometric solar bearings using the NOAA/Meeus equations, entirely offline."""

import math
from datetime import UTC, datetime


def solar_position(
    moment: datetime, latitude: float, longitude: float
) -> tuple[float, float]:
    """Return elevation and clockwise true-north azimuth in degrees.

    NOAA's Julian-century equations are used without atmospheric refraction.
    This is a geometric sun-centre bearing, not cloud cover or measured cooling.
    See docs/SOURCES.md for the equations and independent reference case.
    """
    if moment.utcoffset() is None:
        raise ValueError("Solar calculation requires a timezone-aware timestamp")
    if not (math.isfinite(latitude) and -90 <= latitude <= 90):
        raise ValueError("Latitude must be finite and between -90 and 90")
    if not (math.isfinite(longitude) and -180 <= longitude <= 180):
        raise ValueError("Longitude must be finite and between -180 and 180")
    utc = moment.astimezone(UTC)
    if not 1800 <= utc.year <= 2100:
        raise ValueError("Solar approximation is limited to years 1800 through 2100")
    century = (utc.timestamp() / 86400 + 2440587.5 - 2451545) / 36525
    declination, equation_minutes = _solar_terms(century)
    minutes = utc.hour * 60 + utc.minute + (utc.second + utc.microsecond / 1e6) / 60
    hour_angle = math.radians(
        (minutes + equation_minutes + 4 * longitude) % 1440 / 4 - 180
    )
    return _bearing(latitude, declination, hour_angle)


def _solar_terms(century):
    """Solar declination and equation of time from a Julian century."""
    mean_longitude = (280.46646 + century * (36000.76983 + 0.0003032 * century)) % 360
    anomaly = math.radians(357.52911 + century * (35999.05029 - 0.0001537 * century))
    eccentricity = 0.016708634 - century * (0.000042037 + 0.0000001267 * century)
    centre = (
        math.sin(anomaly) * (1.914602 - century * (0.004817 + 0.000014 * century))
        + math.sin(2 * anomaly) * (0.019993 - 0.000101 * century)
        + math.sin(3 * anomaly) * 0.000289
    )
    omega = math.radians(125.04 - 1934.136 * century)
    apparent_longitude = math.radians(
        mean_longitude + centre - 0.00569 - 0.00478 * math.sin(omega)
    )
    obliquity = math.radians(
        23
        + (
            26
            + (21.448 - century * (46.815 + century * (0.00059 - 0.001813 * century)))
            / 60
        )
        / 60
        + 0.00256 * math.cos(omega)
    )
    declination = math.asin(math.sin(obliquity) * math.sin(apparent_longitude))
    y = math.tan(obliquity / 2) ** 2
    longitude_radians = math.radians(mean_longitude)
    equation_minutes = 4 * math.degrees(
        y * math.sin(2 * longitude_radians)
        - 2 * eccentricity * math.sin(anomaly)
        + 4 * eccentricity * y * math.sin(anomaly) * math.cos(2 * longitude_radians)
        - 0.5 * y * y * math.sin(4 * longitude_radians)
        - 1.25 * eccentricity**2 * math.sin(2 * anomaly)
    )
    return declination, equation_minutes


def _bearing(latitude, declination, hour_angle):
    """Convert hour angle and declination into a geometric horizon bearing."""
    latitude_radians = math.radians(latitude)
    elevation = math.degrees(
        math.asin(
            max(
                -1,
                min(
                    1,
                    math.sin(latitude_radians) * math.sin(declination)
                    + math.cos(latitude_radians)
                    * math.cos(declination)
                    * math.cos(hour_angle),
                ),
            )
        )
    )
    azimuth = (
        math.degrees(
            math.atan2(
                math.sin(hour_angle),
                math.cos(hour_angle) * math.sin(latitude_radians)
                - math.tan(declination) * math.cos(latitude_radians),
            )
        )
        + 180
    ) % 360
    return elevation, azimuth
