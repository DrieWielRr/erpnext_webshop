import inspect
import frappe
import json
import os

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
        timeout=300,
        enqueue_after_commit=True
    )
    log(f"queuing rebuild for {lang}, logs in queue-short container")


def translation_export(lang):
    frappe.log_error(
        title="Translation Worker Debug",
        message=(
            f"file={__file__}\n"
            f"debug={frappe.conf.get('enable_debug')}"
        )
    )

    dirty_key = f"translation_dirty:{lang}"
    job_key = f"translation_job_scheduled:{lang}"

    log(f"[translation_export] START lang={lang}")

    # clear scheduled flag
    job_flag = frappe.cache().get_value(job_key)
    log(f"[translation_export] job_key={job_key} before_delete={job_flag}")

    frappe.cache().delete_value(job_key)

    dirty_flag = frappe.cache().get_value(dirty_key)
    log(f"[translation_export] dirty_key={dirty_key} value={dirty_flag}")

    # if nothing changed → exit
    if not dirty_flag:
        log(f"[translation_export] SKIPPED no dirty flag for {lang}")
        return

    frappe.cache().delete_value(dirty_key)
    log(f"[translation_export] Dirty flag cleared for {lang}")

    log(f"[translation_export] Fetching translations for {lang}")
    rows = frappe.db.get_all(
        "Translation",
        filters={"language": lang},
        fields=["source_text", "translated_text"]
    )

    log(f"[translation_export] Found {len(rows)} translation rows for {lang}")
    data = {
        r.source_text.lower().strip(): r.translated_text
        for r in rows
        if r.translated_text
    }

    log(f"[translation_export] Prepared {len(data)} JSON entries for {lang}")
    translation_dir = frappe.get_site_path(
        "public",
        "translations"
    )
    os.makedirs(translation_dir, exist_ok=True)
    file_path = os.path.join(
        translation_dir,
        f"{lang}.json"
    )

    log(f"[translation_export] Writing file: {file_path}")
    try:
        temp_path = file_path + ".tmp"
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(temp_path, file_path)

    except Exception:
        log(f"[translation_export] FAILED writing {file_path}")
        frappe.log_error(
            title="Translation Export Failed",
            message=frappe.get_traceback()
        )
        raise

    log(f"[translation_export] COMPLETED lang={lang} entries={len(data)}")