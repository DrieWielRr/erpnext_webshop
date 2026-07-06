import frappe
import json

def parse_json(json_string):
    if not json_string:
        return []
    try:
        return json.loads(json_string)
    except Exception:
        return []



_translations = None
def _load_translations():
    global _translations

    if _translations is None:
        path = frappe.get_app_path(
            "erpnext_webshop",
            "webshop",
            "templates",
            "includes",
            "translations.json"
        )

        with open(path, "r", encoding="utf-8") as f:
            _translations = json.load(f)

    return _translations


def translate(key):
    if not key:
        return key

    lang = frappe.local.lang or "en"
    lookup = str(key).lower().strip()

    data = _load_translations()

    return (
        data.get(lang, {}).get(lookup)
        or data.get("en", {}).get(lookup)
        or key
    )