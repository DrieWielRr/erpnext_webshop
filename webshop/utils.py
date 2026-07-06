import inspect
import frappe
import json

def log(msg):
    if frappe.conf.get("enable_debug"):
        frame = inspect.currentframe().f_back
        func_name = frame.f_code.co_name
        module_name = frame.f_globals.get("__name__", "unknown")
        print(f"[{module_name}.{func_name}] {msg}", flush=True)


def parse_json(json_string):
    if not json_string:
        return []
    try:
        return json.loads(json_string)
    except Exception:
        return []


def queue_translation_export(doc, method=None):
    if not doc or not doc.language:
        return

    lang = doc.language

    dirty_key = f"translation_dirty:{lang}"
    job_key = f"translation_job_scheduled:{lang}"

    # mark dirty (always)
    frappe.cache().set_value(dirty_key, 1, expires_in_sec=3600)

    # prevent enqueue spam
    if frappe.cache().get_value(job_key):
        return

    frappe.cache().set_value(job_key, 1, expires_in_sec=60)

    frappe.enqueue(
        "webshop.utils.translation_export",
        lang=lang,
        queue="short",
        timeout=300
    )
    log(f"[queue_translation_export] queuing rebuild for {lang}")

def translation_export(lang):
    dirty_key = f"translation_dirty:{lang}"
    job_key = f"translation_job_scheduled:{lang}"

    # clear scheduled flag
    frappe.cache().delete_value(job_key)

    # if nothing changed → exit
    if not frappe.cache().get_value(dirty_key):
        return

    frappe.cache().delete_value(dirty_key)

    rows = frappe.db.get_all(
        "Translation",
        filters={"language": lang},
        fields=["source_text", "translated_text"]
    )

    data = {
        r.source_text.lower().strip(): r.translated_text
        for r in rows if r.translated_text
    }

    file_path = frappe.get_site_path(
        "public",
        "files",
        f"{lang}_translations.json"
    )

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    log(f"[translation_export] rebuilt {lang}")