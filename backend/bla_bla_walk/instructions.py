"""Normalize OSRM evidence without deriving maneuvers from a route line."""

import math

from pydantic import ValidationError

from .interfaces import WalkingDirections, WalkingInstruction

MODIFIERS = {
    "left",
    "right",
    "slight left",
    "slight right",
    "sharp left",
    "sharp right",
    "straight",
    "uturn",
}


def instruction_text(maneuver, street):
    """Plain English from maneuver fields, including unnamed roads and exits."""
    kind = maneuver["type"]
    modifier = maneuver.get("modifier")
    road = f" on {street}" if street else ""
    direction = f" {modifier}" if modifier in MODIFIERS else ""
    if modifier == "uturn" and kind != "depart" and kind != "arrive":
        return "Make a U-turn" + road, "turn"
    if kind == "depart":
        return "Start walking" + road, "start"
    if kind == "arrive":
        return "Arrive at the selected destination", "arrive"
    if kind in {"roundabout", "rotary", "roundabout turn"}:
        exit_number = maneuver.get("exit")
        action = (
            f"At the roundabout, take exit {exit_number}"
            if exit_number
            else "Follow the roundabout"
        )
        return action + road, "turn"
    if kind in {"exit roundabout", "exit rotary"}:
        return "Exit the roundabout" + road, "turn"
    if kind in {"turn", "end of road"}:
        action = "Continue straight" if modifier == "straight" else "Turn" + direction
        return action + road, "turn"
    if kind == "fork":
        return "At the fork, keep" + direction + road, "turn"
    if kind == "merge":
        return "Merge" + direction + road, "turn"
    if kind == "new name" or kind in {"continue", "notification", "use lane"}:
        return "Continue" + direction + road, "continue"
    raise ValueError("Unsupported maneuver")


def add_street_context(steps):
    """Locate unlabelled segments between actual provider-named route streets.

    A later street is a route reference, never the claimed name of an unnamed
    segment or an inferred intersection. Keep every provider turn intact.
    """
    previous_street = None
    for index, step in enumerate(steps):
        if step.street_name:
            previous_street = step.street_name
            continue
        if step.kind == "arrive":
            continue
        following = next((s for s in steps[index + 1 :] if s.street_name), None)
        references = []
        if previous_street:
            references.append(f"After {previous_street}")
        if following:
            remaining = round(following.at_metres - step.at_metres)
            subject = "route" if previous_street else "Route"
            references.append(
                f"{subject} continues to {following.street_name} in {remaining} m"
            )
        elif previous_street:
            references.append("towards the selected destination")
        if references:
            step.text += ". " + "; ".join(references)


def provider_directions(route, route_id, speed):
    """Missing, partial or inconsistent evidence makes directions unavailable.

    Distances and estimated walking times use the same configured speed as the
    route. Raw provider driving-profile durations are never used for walking.
    """
    try:
        legs = route["legs"]
        if not legs or any(not leg.get("steps") for leg in legs):
            return None
        raw_steps = [step for leg in legs for step in leg["steps"]]
        if (
            raw_steps[0]["maneuver"]["type"] != "depart"
            or raw_steps[-1]["maneuver"]["type"] != "arrive"
        ):
            return None
        steps = []
        at_metres = 0.0
        coordinates = route["geometry"]["coordinates"]
        if (
            math.dist(raw_steps[0]["maneuver"]["location"], coordinates[0]) >= 0.00001
            or math.dist(raw_steps[-1]["maneuver"]["location"], coordinates[-1])
            >= 0.00001
        ):
            return None
        previous_index = 0
        for raw_index, raw in enumerate(raw_steps):
            maneuver = raw["maneuver"]
            location = maneuver["location"]
            matching_index = next(
                (
                    index
                    for index in range(previous_index, len(coordinates))
                    if math.dist(location, coordinates[index]) < 0.00001
                ),
                None,
            )
            if matching_index is None:
                return None
            previous_index = matching_index
            street = raw.get("name") or raw.get("ref") or None
            if street is not None and not isinstance(street, str):
                return None
            text, kind = instruction_text(maneuver, street)
            distance = float(raw["distance"])
            if kind == "arrive" and raw_index != len(raw_steps) - 1:
                if distance == 0:
                    continue
                text, kind = "Continue through the route waypoint", "continue"
            elif kind == "start" and raw_index != 0:
                text, kind = (
                    "Continue walking" + (f" on {street}" if street else ""),
                    "continue",
                )
            steps.append(
                WalkingInstruction(
                    kind=kind,
                    text=text,
                    location=location,
                    at_metres=at_metres,
                    distance_m=distance,
                    duration_s=distance / speed,
                    maneuver_type=maneuver["type"],
                    modifier=maneuver.get("modifier"),
                    street_name=street,
                    exit=maneuver.get("exit"),
                )
            )
            at_metres += distance
        if not math.isclose(at_metres, route["distance"], abs_tol=2, rel_tol=0.001):
            return None
        add_street_context(steps)
        return WalkingDirections(route_id=route_id, steps=steps)
    except (KeyError, TypeError, ValueError, ValidationError):
        return None
