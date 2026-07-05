import frappe
import json

def parse_json(json_string):
    if not json_string:
        return []
    try:
        return json.loads(json_string)
    except Exception:
        return []
