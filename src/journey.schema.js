// Generated from canonical Python models. Do not edit by hand.
export const journeySchema = {
  "$defs": {
    "Provenance": {
      "additionalProperties": false,
      "description": "Provider, reuse terms and distinct observation/retrieval timestamps.",
      "properties": {
        "provider": {
          "title": "Provider",
          "type": "string"
        },
        "source_url": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Source Url"
        },
        "attribution": {
          "title": "Attribution",
          "type": "string"
        },
        "licence": {
          "title": "Licence",
          "type": "string"
        },
        "fixture": {
          "title": "Fixture",
          "type": "boolean"
        },
        "observed_at": {
          "anyOf": [
            {
              "format": "date-time",
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Observed At"
        },
        "retrieved_at": {
          "anyOf": [
            {
              "format": "date-time",
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Retrieved At"
        }
      },
      "required": [
        "provider",
        "attribution",
        "licence",
        "fixture"
      ],
      "title": "Provenance",
      "type": "object"
    },
    "ShadeMetadata": {
      "additionalProperties": false,
      "description": "Calculation context, independent of sensor observations.",
      "properties": {
        "requested_time": {
          "format": "date-time",
          "title": "Requested Time",
          "type": "string"
        },
        "effective_time": {
          "format": "date-time",
          "title": "Effective Time",
          "type": "string"
        },
        "geometry_version": {
          "title": "Geometry Version",
          "type": "string"
        },
        "resolution_m": {
          "exclusiveMinimum": 0,
          "title": "Resolution M",
          "type": "number"
        }
      },
      "required": [
        "requested_time",
        "effective_time",
        "geometry_version",
        "resolution_m"
      ],
      "title": "ShadeMetadata",
      "type": "object"
    },
    "ShadeState": {
      "description": "Server raster values; night must never count as daytime shaded metres.",
      "enum": [
        0,
        1,
        2,
        3
      ],
      "title": "ShadeState",
      "type": "integer"
    },
    "TripComparison": {
      "additionalProperties": false,
      "description": "Pure rescoring result for T6; manual choice only among eligible IDs.\n\nMetrics retain full-route denominators. Scores can be incomplete lower\nbounds; status and explanation determine whether a winner is available.\nTransit stays unavailable until T18/T19 admission and approval.",
      "properties": {
        "status": {
          "title": "Status",
          "type": "string"
        },
        "winner": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Winner"
        },
        "route_statuses": {
          "additionalProperties": {
            "type": "string"
          },
          "title": "Route Statuses",
          "type": "object"
        },
        "metrics": {
          "additionalProperties": {
            "additionalProperties": true,
            "type": "object"
          },
          "title": "Metrics",
          "type": "object"
        },
        "scores": {
          "additionalProperties": {
            "type": "number"
          },
          "title": "Scores",
          "type": "object"
        },
        "contributions": {
          "additionalProperties": {
            "additionalProperties": {
              "type": "number"
            },
            "type": "object"
          },
          "title": "Contributions",
          "type": "object"
        },
        "reasons": {
          "additionalProperties": {
            "items": {
              "type": "string"
            },
            "type": "array"
          },
          "title": "Reasons",
          "type": "object"
        },
        "manual_choices": {
          "items": {
            "type": "string"
          },
          "title": "Manual Choices",
          "type": "array"
        },
        "explanation": {
          "default": "",
          "title": "Explanation",
          "type": "string"
        },
        "transit_status": {
          "const": "unavailable",
          "default": "unavailable",
          "title": "Transit Status",
          "type": "string"
        }
      },
      "required": [
        "status",
        "route_statuses"
      ],
      "title": "TripComparison",
      "type": "object"
    },
    "WalkingEvidence": {
      "additionalProperties": false,
      "description": "Cached T5 route distances; invalid metrics remain displayable with reasons.\n\nSampling approximation, requested/effective times and model limits live in\nsamples. Unknown includes night for scoring, with night separately recorded.\nFlags must come from evidence, never from the mere existence of a polyline.",
      "properties": {
        "id": {
          "title": "Id",
          "type": "string"
        },
        "distance_metres": {
          "title": "Distance Metres",
          "type": "number"
        },
        "shaded_metres": {
          "title": "Shaded Metres",
          "type": "number"
        },
        "unshaded_metres": {
          "title": "Unshaded Metres",
          "type": "number"
        },
        "unknown_metres": {
          "title": "Unknown Metres",
          "type": "number"
        },
        "planned_stop_minutes": {
          "default": 0,
          "title": "Planned Stop Minutes",
          "type": "number"
        },
        "access_state": {
          "default": "unknown",
          "enum": [
            "checked_open",
            "confirmed_blocked",
            "unknown"
          ],
          "title": "Access State",
          "type": "string"
        },
        "inside_calculation_coverage": {
          "default": false,
          "title": "Inside Calculation Coverage",
          "type": "boolean"
        },
        "construction_caution": {
          "default": false,
          "title": "Construction Caution",
          "type": "boolean"
        },
        "shade_state": {
          "default": "unknown",
          "enum": [
            "current",
            "stale",
            "failed",
            "unknown"
          ],
          "title": "Shade State",
          "type": "string"
        },
        "shade_time_matches_request": {
          "default": false,
          "title": "Shade Time Matches Request",
          "type": "boolean"
        },
        "shade_geometry_matches_request": {
          "default": false,
          "title": "Shade Geometry Matches Request",
          "type": "boolean"
        },
        "duration_complete": {
          "default": true,
          "title": "Duration Complete",
          "type": "boolean"
        },
        "water": {
          "$ref": "#/$defs/WaterEvidence"
        },
        "provenance": {
          "anyOf": [
            {
              "$ref": "#/$defs/Provenance"
            },
            {
              "type": "null"
            }
          ],
          "default": null
        },
        "samples": {
          "items": {
            "$ref": "#/$defs/WalkingShadeSample"
          },
          "title": "Samples",
          "type": "array"
        },
        "sampled_speed_m_per_s": {
          "anyOf": [
            {
              "type": "number"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Sampled Speed M Per S"
        },
        "sampled_distance_metres": {
          "anyOf": [
            {
              "type": "number"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Sampled Distance Metres"
        },
        "sampled_stop_minutes": {
          "anyOf": [
            {
              "type": "number"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Sampled Stop Minutes"
        }
      },
      "required": [
        "id",
        "distance_metres",
        "shaded_metres",
        "unshaded_metres",
        "unknown_metres"
      ],
      "title": "WalkingEvidence",
      "type": "object"
    },
    "WalkingShadeSample": {
      "additionalProperties": false,
      "description": "Midpoint quadrature interval in route metres, sampled at traversal time.\n\nThis estimates distance, not exact cell intersection or observed shade.\nA stop at an interval boundary affects all subsequent sample times.",
      "properties": {
        "start_metres": {
          "title": "Start Metres",
          "type": "number"
        },
        "end_metres": {
          "title": "End Metres",
          "type": "number"
        },
        "requested_time": {
          "format": "date-time",
          "title": "Requested Time",
          "type": "string"
        },
        "metadata": {
          "anyOf": [
            {
              "$ref": "#/$defs/ShadeMetadata"
            },
            {
              "type": "null"
            }
          ],
          "default": null
        },
        "state": {
          "$ref": "#/$defs/ShadeState",
          "default": 0
        },
        "model": {
          "default": "unavailable",
          "title": "Model",
          "type": "string"
        },
        "explanation": {
          "title": "Explanation",
          "type": "string"
        }
      },
      "required": [
        "start_metres",
        "end_metres",
        "requested_time",
        "explanation"
      ],
      "title": "WalkingShadeSample",
      "type": "object"
    },
    "WaterEvidence": {
      "additionalProperties": false,
      "description": "Verified network diversion and physical evidence, never point proximity.",
      "properties": {
        "state": {
          "default": "unknown",
          "title": "State",
          "type": "string"
        },
        "evidence_complete": {
          "default": false,
          "title": "Evidence Complete",
          "type": "boolean"
        },
        "age_hours": {
          "anyOf": [
            {
              "type": "number"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Age Hours"
        },
        "drinking": {
          "anyOf": [
            {
              "type": "boolean"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Drinking"
        },
        "accessible": {
          "anyOf": [
            {
              "type": "boolean"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Accessible"
        },
        "operational": {
          "anyOf": [
            {
              "type": "boolean"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Operational"
        },
        "extra_distance_metres": {
          "anyOf": [
            {
              "type": "number"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Extra Distance Metres"
        },
        "extra_distance_included": {
          "default": false,
          "title": "Extra Distance Included",
          "type": "boolean"
        },
        "provenance": {
          "anyOf": [
            {
              "$ref": "#/$defs/Provenance"
            },
            {
              "type": "null"
            }
          ],
          "default": null
        }
      },
      "title": "WaterEvidence",
      "type": "object"
    }
  },
  "additionalProperties": false,
  "description": "Poll the same request while pending; evidence is local model output.",
  "properties": {
    "status": {
      "enum": [
        "pending",
        "complete"
      ],
      "title": "Status",
      "type": "string"
    },
    "departure": {
      "format": "date-time",
      "title": "Departure",
      "type": "string"
    },
    "explanation": {
      "title": "Explanation",
      "type": "string"
    },
    "evidence": {
      "items": {
        "$ref": "#/$defs/WalkingEvidence"
      },
      "title": "Evidence",
      "type": "array"
    },
    "comparison": {
      "additionalProperties": {
        "$ref": "#/$defs/TripComparison"
      },
      "title": "Comparison",
      "type": "object"
    }
  },
  "required": [
    "status",
    "departure",
    "explanation"
  ],
  "title": "JourneyResponse",
  "type": "object"
};
