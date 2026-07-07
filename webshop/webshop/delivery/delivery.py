# --------------------------------------------------
# DELIVERY UTILITIES (v0.0.1)
#
# Changelog:
# - v0.0.1 Initial implementation
#
# Responsibilities:
# - Geocode an Address using OpenStreetMap Nominatim
# - Store coordinates in the Geolocation field
# - Calculate driving distance using OSRM
# --------------------------------------------------

import json
import requests

import frappe
from frappe.utils import flt
from webshop.utils import log

# --------------------------------------------------------------------
# CONFIG
# --------------------------------------------------------------------

USER_AGENT = "JojaCakes-ERPNext/1.0 (info@jojacakes.nl)"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OSRM_URL = "https://router.project-osrm.org/route/v1/driving"


# --------------------------------------------------------------------
# HELPERS
# --------------------------------------------------------------------

def build_address(address):
    return ", ".join(filter(None, [
        address.address_line1,
        address.address_line2,
        address.pincode,
        address.city,
        address.country,
    ]))


def get_coordinates(address):
    """
    Returns (lat, lon) from the Geolocation field.
    """

    if not address.custom_geolocation:
        return None

    geo = json.loads(address.custom_geolocation)

    coordinates = geo["features"][0]["geometry"]["coordinates"]

    # GeoJSON = [lon, lat]
    return (
        flt(coordinates[1]),
        flt(coordinates[0]),
    )


def set_coordinates(address, latitude, longitude):
    """
    Stores coordinates in the Address Geolocation field.
    """

    address.custom_geolocation = json.dumps({
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "properties": {},
            "geometry": {
                "type": "Point",
                "coordinates": [
                    longitude,
                    latitude,
                ]
            }
        }]
    })

# --------------------------------------------------------------------
# SHOP ADDRESS
# --------------------------------------------------------------------

def get_shop_address():
    """
    Returns the company Address marked as "Is Your Company Address".
    """

    addresses = frappe.get_all(
        "Address",
        filters={
            "is_your_company_address": 1
        },
        pluck="name",
    )

    if not addresses:
        frappe.throw(
            "No company address found. "
            "Please mark an Address as 'Is Your Company Address'."
        )

    if len(addresses) > 1:
        log(
            f"Multiple company addresses found: {addresses}. "
            f"Using first one."
        )

    return frappe.get_doc("Address", addresses[0])

# --------------------------------------------------------------------
# GEOCODING
# --------------------------------------------------------------------

def geocode(address):
    """
    Geocode an Address using Nominatim.
    """

    query = build_address(address)
    log(f"Geocoding address: {query}")

    try:
        response = requests.get(
            NOMINATIM_URL,
            params={
                "q": query,
                "format": "jsonv2",
                "limit": 1,
            },
            headers={
                "User-Agent": USER_AGENT
            },
            timeout=5,
        )

        response.raise_for_status()

    except requests.exceptions.Timeout:
        log("Nominatim timeout")
        frappe.throw("Address lookup timed out. Please try again later.")

    except requests.exceptions.HTTPError as e:
        log(f"Nominatim HTTP error: {e}")
        frappe.throw(f"Address lookup failed: {e}")

    except requests.exceptions.RequestException as e:
        log(f"Nominatim request error: {e}")
        frappe.throw("Unable to contact address lookup service.")

    try:
        data = response.json()

    except Exception as e:
        log(f"Nominatim invalid response: {e}")
        frappe.throw("Invalid response received from address lookup service.")

    if not data:
        log(f"No geolocation result for: {query}")
        frappe.throw(f"Unable to determine coordinates for address:<br><br>{query}")

    latitude = flt(data[0]["lat"])
    longitude = flt(data[0]["lon"])

    log(f"Geocode result: latitude={latitude}, longitude={longitude}")

    set_coordinates(
        address,
        latitude,
        longitude
    )

    return latitude, longitude


# --------------------------------------------------------------------
# ROUTING
# --------------------------------------------------------------------

def calculate_route_distance(origin, destination):
    """
    Calculates road distance in kilometers.
    """

    origin_lat, origin_lon = origin
    destination_lat, destination_lon = destination

    response = requests.get(
        f"{OSRM_URL}/{origin_lon},{origin_lat};{destination_lon},{destination_lat}",
        params={
            "overview": "false"
        },
        headers={
            "User-Agent": USER_AGENT
        },
        timeout=10,
    )

    response.raise_for_status()

    data = response.json()

    if not data.get("routes"):
        frappe.throw("Unable to calculate delivery route.")

    return round(
        data["routes"][0]["distance"] / 1000,
        2
    )


# --------------------------------------------------------------------
# PUBLIC API
# --------------------------------------------------------------------

def update_delivery_distance(doc, method=None):
    """
    Calculates and stores delivery distance.
    """
    address = doc

    log("=== UPDATE DELIVERY DISTANCE START ===")
    log(f"Address: {address.name}")
    log(f"Address text: {build_address(address)}")

    #
    # Customer
    #

    log("Checking customer coordinates")
    customer_coordinates = geocode(address)
    log(f"Customer coordinates obtained: {customer_coordinates}")

    #
    # Shop
    #

    log("Loading shop address")
    shop = get_shop_address()     
    log(f"Shop address found: {shop.name} - {build_address(shop)}")

    shop_coordinates = get_coordinates(shop)
    if shop_coordinates:
        log(f"Using existing shop coordinates: {shop_coordinates}")
    else:
        log("No shop coordinates found, geocoding shop address")
        shop_coordinates = geocode(shop)
        log(f"Shop coordinates obtained: {shop_coordinates}")
        
        frappe.db.set_value(
            "Address",
            shop.name,
            "custom_geolocation",
            shop.custom_geolocation
        )
        log("Shop coordinates saved")

    if doc.name == shop.name:
        log(
            f"Skipping delivery calculation. "
            f"Address {doc.name} is the shop address."
        )
        log("=== UPDATE DELIVERY DISTANCE END ===")
        return

    #
    # Route
    #

    log(f'Calculating route distance from "{shop_coordinates}" to "{customer_coordinates}"')
    distance = calculate_route_distance(
        shop_coordinates,
        customer_coordinates
    )
    log(f"Calculated delivery distance: {distance} km")

    #
    # Store result
    #

    address.custom_delivery_distance_km = distance
    log(f"Updated {address.name}.custom_delivery_distance_km (distance: {distance})")

    log("=== UPDATE DELIVERY DISTANCE END ===")
    return distance