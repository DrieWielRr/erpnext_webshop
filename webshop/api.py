import json
import hashlib
import frappe

from frappe import _
from webshop.webshop.shopping_cart.cart import (
    _get_cart_quotation,
    apply_cart_settings,
    set_cart_count,
    get_cart_quotation
)
from frappe.utils import flt, cint


# --------------------------------------------------
# DEBUG FLAG
# --------------------------------------------------
ENABLE_DEBUG = 1


def log(msg):
    if ENABLE_DEBUG:
        print(f"[CART DEBUG] {msg}", flush=True)


def normalize_config(config):
    """
    Normalizes the values send by the front-end to prevent issues down the line
    """
    for c in config:
        c["attribute"] = c["attribute"].strip()
        c["value"] = c["value"].strip()
        if "price" in c:
            c["price"] = float(c["price"])
    return config


def validate_config(config):
    """
    Validates if the config send by the front-end is valid.
    """
    if config is None:
        return []

    if not isinstance(config, list):
        frappe.throw("Invalid configuration format (must be list)")

    ALLOWED_KEYS = {"attribute", "value", "price", "id"}

    for c in config:

        if not isinstance(c, dict):
            frappe.throw("Invalid config entry (must be object)")

        # reject unknown keys early
        if not set(c.keys()).issubset(ALLOWED_KEYS):
            frappe.throw("Invalid config keys")

        # required fields
        if not c.get("attribute") or not c.get("value"):
            frappe.throw("Missing required config fields")

        if not isinstance(c["attribute"], str) or not isinstance(c["value"], str):
            frappe.throw("Invalid config types")

        # optional price validation
        if "price" in c:
            try:
                c["price"] = float(c["price"])
            except Exception:
                frappe.throw("Invalid price value")

            if c["price"] < 0:
                frappe.throw("Price cannot be negative")

    return config


def generate_configuration_hash(configuration):
    """
    Generates deterministic hash based on configuration.
    """
    return hashlib.md5(
        json.dumps(configuration, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()         


def get_attribute_price_map(attribute_name):

    cache_key = f"attr_price_map:{attribute_name}"
    cache = frappe.cache()

    cached = cache.get_value(cache_key)
    if cached:
        return json.loads(cached)

    rows = frappe.get_all(
        "Item Attribute Value",
        filters={"parent": attribute_name},
        fields=["attribute_value", "custom_price"]
    )

    result = {
        r["attribute_value"]: float(r.get("custom_price") or 0)
        for r in rows
    }

    cache.set_value(cache_key, json.dumps(result), expires_in_sec=3600)

    return result

def calculate_configuration_price(configuration):
    """
    Takes parsed configuration list and returns total extra price.
    Server is source of truth for attribute pricing.
    """

    if not configuration:
        return 0.0

    total_extra = 0.0

    for c in configuration:

        attribute_id = c.get("id")
        attribute_name = c.get("attribute")
        value = c.get("value")

        if not attribute_name or not value:
            frappe.throw("Invalid configuration entry (missing attribute/value)")

        price_map = get_attribute_price_map(attribute_id)
        log(f"attribute_id: {attribute_id}, attribute_name: {attribute_name}, value: {value}")
        log(f"price_map: {price_map}")

        if value not in price_map:
            frappe.throw(
                f"Invalid value '{value}' for attribute '{attribute_name}'"
            )

        server_price = price_map[value]
        client_price = float(c.get("price") or 0)

        if client_price != server_price:
            frappe.throw(
                f"Price mismatch for {attribute_name} ({value}). "
                f"Server={server_price}, Client={client_price}"
            )

        total_extra += server_price

    return total_extra







# --------------------------------------------------
# CUSTOM UPDATE CART (v0.0.4)
#
# Changelog:
# - v0.0.1, Initial clone of original function
# - v0.0.2, Adding "configuration=None" to the function
# - v0.0.3, Apply the item configuration to the item when provided
# - v0.0.4, Enforce initial selling quantity
# --------------------------------------------------

@frappe.whitelist()
def update_cart(item_code, qty, additional_notes=None, with_items=False, configuration=None, is_add_to_cart=False):
	
    log("=== CUSTOM UPDATE_CART START ===")

    # Force qty to float immediately to ensure all numerical comparisons are safe
    qty = flt(qty)

    # CUSTOM CODE (ITEM CONFIGURATION)
    ########################################################################
    # If provided generate the custom configuration
    item_configuration = json.loads(configuration or "[]") 
    item_configuration = validate_config(item_configuration)
    item_configuration = normalize_config(item_configuration)                
    item_configuration_hash = generate_configuration_hash(item_configuration)
    item_configuration_price = calculate_configuration_price(item_configuration)
    log(f"configuration={configuration}")
    log(f"item_configuration={item_configuration}")
    log(f"item_configuration_hash={item_configuration_hash}")
    log(f"item_configuration_price={item_configuration_price}")
    ########################################################################

    quotation = _get_cart_quotation()
    log(f"quotation name={quotation.get("name")}")

    empty_card = False    
    if qty == 0:
        quotation_items = [
            d for d in quotation.items
            if d.item_code == item_code
            and d.custom_config_hash != item_configuration_hash
        ]
        if quotation_items:
            quotation.set("items", quotation_items)
        else:
            empty_card = True

    else:
        warehouse = frappe.get_cached_value(
			"Website Item", {"item_code": item_code}, "website_warehouse"
		)
        
        # CUSTOM CODE
        ########################################################################
        quotation_items_all = [
            d for d in quotation.items
            if d.item_code == item_code
        ]
        quotation_items = [
            d for d in quotation.items
            if d.item_code == item_code
            and d.custom_config_hash == item_configuration_hash
        ]        
        ########################################################################
        #quotation_items = quotation.get("items", {"item_code": item_code})
        
        # CUSTOM CODE: (ENFORCE MINIMUM PURCHASE QUANTITY)
        ########################################################################
        try:
            # Fetch the total items based on item_code            
            total_items = sum(flt(d.qty) for d in quotation_items_all)
            log(f"[MIN_QTY CHECK] total_items: {total_items} (Type: {type(total_items).__name__})")
            
            # Fetch the threshold from the Item Price record
            min_qty_record = frappe.db.get_value(
                "Item Price",
                {"item_code": item_code, "price_list": "Standard Selling"}, 
                "custom_initial_quantity"
            )            
            log(f"[MIN_QTY CHECK] Database returned: {min_qty_record} (Type: {type(min_qty_record).__name__})")
            
            if min_qty_record is not None:
                min_qty = int(float(min_qty_record)) # Safe cast from float/string to int
                
        except Exception as e:
            log(f"[MIN_QTY ERROR] Failed to fetch or parse custom_initial_quantity: {str(e)}")
            min_qty = 1
            
        # Force the input qty up to the minimum threshold if it falls below it
        if total_items <= min_qty and qty < min_qty:
            log(f"[MIN_QTY CHECK] CRITICAL: User ordered {qty}, but minimum is {min_qty}. Overriding qty.")
            qty = flt(min_qty)
        else:
            log(f"[MIN_QTY CHECK] Quantity {qty} is valid (Minimum is {min_qty}).")   
        ########################################################################
        
        if not quotation_items:
            log(f"appending item to quotation:")
            log(f"doctype=doctype")
            log(f"item_code={item_code}")
            log(f"qty={qty}")
            log(f"additional_notes={additional_notes}")
            log(f"warehouse={warehouse}")
            log(f"custom_config_hash={item_configuration_hash}")
            log(f"custom_item_configurations={json.dumps(item_configuration)}")            
            quotation.append(
                "items",
                {
                    "doctype": "Quotation Item",
                    "item_code": item_code,
                    "qty": qty,
                    "additional_notes": additional_notes,
                    "warehouse": warehouse,
                    "custom_config_hash": item_configuration_hash,                   # CUSTOM CODE
                    "custom_item_configurations": json.dumps(item_configuration)    # CUSTOM CODE
                },
            )
        else:
            log(f"Updating quotation items")
            log(f"qty={qty}")
            log(f"warehouse={warehouse}")
            log(f"additional_notes={additional_notes}")
            quotation_items[0].qty = (flt(quotation_items[0].qty) + 1) if is_add_to_cart else flt(qty)
            quotation_items[0].warehouse = warehouse
            quotation_items[0].additional_notes = additional_notes

    log(f"Applying cart settings")
    apply_cart_settings(quotation=quotation)
    
    # CUSTOM CODE
    ########################################################################    
    if not quotation_items:
        for item in quotation.items:
            if item.item_code == item_code and item.custom_config_hash == item_configuration_hash:
                base_rate = item.rate
                log(f"base_rate={base_rate}")
                item.rate = base_rate + item_configuration_price
                log(f"Updated item.rate={item.rate}")
                item.amount = item.rate * item.qty
                log(f"Updated item.amount={item.amount}")
    ########################################################################

    quotation.flags.ignore_permissions = True
    quotation.payment_schedule = []
    if not empty_card:
        log(f"Quotation save")
        quotation.save()
    else:
        log(f"Quotation delete")
        quotation.delete()
        quotation = None

    log(f"Applying cart count")
    set_cart_count(quotation)

    log(f"Return render_template")
    log("=== CUSTOM UPDATE_CART END ===")
    if cint(with_items):                 
        context = get_cart_quotation(quotation)
        
        return {
            "items": frappe.render_template(
                "templates/includes/cart/cart_items.html", context
            ),
            "total": frappe.render_template(
                "templates/includes/cart/cart_items_total.html", context
            ),
            "taxes_and_totals": frappe.render_template(
                "templates/includes/cart/cart_payment_summary.html", context
            )
        }
    else:
        return {"name": quotation.name}    




@frappe.whitelist()
def get_cart_status(item_code):
    """
    Returns the quantity of a specific item currently in the active cart.
    Returns 0 if not found.
    """
    log(f"=== CHECKING CART STATUS FOR: {item_code} ===")
    
    # Use the same helper function you use in update_cart
    quotation = _get_cart_quotation()
    
    # Filter for the specific item_code
    items_in_cart = [d for d in quotation.items if d.item_code == item_code]
    
    # Sum the quantity (handles cases where the same item might be added multiple times)
    total_qty = sum(flt(d.qty) for d in items_in_cart)
    
    log(f"Found {total_qty} units of {item_code} in cart.")
    
    return {
        "in_cart": total_qty > 0,
        "qty": total_qty
    }