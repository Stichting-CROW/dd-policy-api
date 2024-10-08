import zones.zone as zone
import mds.policy
from pydantic.json import pydantic_encoder

def generate_policy(data: zone.Zone):
    if data.geography_type != "no_parking":
      return

    rule = mds.policy.Rule(
        name = "Disallow parking",
        description = "This rule forbids parking.",
        rule_type = "count",
        rule_units = "devices",
        geographies = [data.geography_id],
        states = {"available": ["trip_end"]},
        maximum = 0
    )
    
    policy = mds.policy.Policy(
        policy_id=data.geography_id,
        name = "No parking policy: " + data.name,
        description= "Disallow parking in geography with name: " + data.name,
        start_date=data.effective_date,
        end_date=data.retire_date,
        published_date=data.published_date,
        rules = [rule]
    )
    return policy


policies = """{
  "updated": 0,
  "version": "1.2.0",
  "data": {
    "policies": [
      {
        "policy_id": "99f7a469-6e3a-4981-9313-c2f6c0bbd5ce",
        "name": "Test City Mobility Hubs",
        "description": "Enforced parking in specific mobility hubs for downtown area",
        "start_date": 1558389669540,
        "end_date": null,
        "published_date": 1558389669540,
        "prev_policies": null,
        "rules": [
          {
            "name": "Allow parking in specific locations",
            "rule_id": "8a61de66-d9fa-4cba-a38d-5d948e2373fe",
            "minimum": 0,
            "rule_type": "count",
            "rule_units": "devices",
            "geographies": [
              "e3ed0a0e-61d3-4887-8b6a-4af4f3769c14",
              "1512a3f4-313c-45fc-9fae-0dca6d7ab355"
            ],
            "states": {
              "available": [
                "trip_end"
              ]
            },
            "vehicle_types": [
              "bicycle",
              "scooter"
            ]
          },
          {
            "name": "Disallow parking elsewhere in downtown area",
            "rule_id": "0240899e-a8ad-4263-953a-6e278ff859ab",
            "rule_type": "count",
            "maximum": 0,
            "rule_units": "devices",
            "geographies": [
              "075a5303-2571-4ca5-b429-841bcc4025d1"
            ],
            "states": {
              "available": [
                "trip_end"
              ]
            },
            "vehicle_types": [
              "bicycle",
              "scooter"
            ]
          }
        ]
      }
    ]
  }
}"""