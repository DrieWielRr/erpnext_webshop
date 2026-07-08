import frappe

from webshop.utils import log


# --------------------------------------------------------------------
# HELPERS
# --------------------------------------------------------------------

def build_group_tree(parent, groups, level=0):
    children = [
        g
        for g in groups
        if g.parent_item_group == parent
    ]

    for child in children:
        log(
            f"{'  ' * level}"
            f"- {child.name} "
            f"(route: {child.route})"
        )

        build_group_tree(
            child.name,
            groups,
            level + 1
        )


def get_group_nodes(parent, groups, parent_nav=None, level=1):
    nodes = []

    children = [
        g
        for g in groups
        if g.parent_item_group == parent
    ]

    for child in children:
        nodes.append({
            "name": child.name,
            "route": child.route,
            "parent_group": parent,
            "parent_nav": parent_nav,
            "level": level,
        })

        nodes.extend(
            get_group_nodes(
                child.name,
                groups,
                child.name,
                level + 1,
            )
        )

    return nodes




# --------------------------------------------------------------------
# SYNC
# --------------------------------------------------------------------

def sync_dynamic_navbar(*args, **kwargs):
    frappe.enqueue(
        "webshop.dynamic_menu.dynamic_menu.sync_dynamic_navbar",
        queue="short"
    )


def sync_dynamic_navbar(*args, **kwargs):
    if frappe.flags.get("in_dynamic_navbar_sync"):
        log("Skipping recursive dynamic navbar sync (loop guard)")
        return

    frappe.flags.in_dynamic_navbar_sync = True

    try:
        _sync_dynamic_navbar()

    finally:
        frappe.flags.in_dynamic_navbar_sync = False


def _sync_dynamic_navbar():
    log("")
    log("=== DYNAMIC NAVBAR SYNC STARTED ===")
    log("=" * 60)

    website_settings = frappe.get_single("Website Settings")

    dynamic_roots = [
        item for item in website_settings.top_bar_items
        if item.custom_linked_item_group
        and not item.custom_is_dynamic
    ]

    log(f"Found {len(dynamic_roots)} dynamic root menu(s)")

    groups = frappe.get_all(
        "Item Group",
        fields=[
            "name",
            "parent_item_group",
            "route",
            "show_in_website",
            "lft",
        ],
        filters={
            "show_in_website": 1,
        },
        order_by="lft asc",
    )

    log(f"Loaded {len(groups)} website Item Group(s)")

    for root in dynamic_roots:
        log("")
        log("=" * 60)
        log(f"SYNC ROOT: {root.label}")
        log(f"Linked Item Group : {root.custom_linked_item_group}")
        log(f"Navbar URL        : {root.url}")

        sync_root(
            website_settings,
            root,
            groups,
        )
        
    log("=" * 60)
    log("=== DYNAMIC NAVBAR SYNC FINISHED ===")
    log("")


def sync_root(website_settings, root, groups):

    # ------------------------------------------------------------
    # Validate root Item Group
    # ------------------------------------------------------------

    log(f"Building tree from '{root.custom_linked_item_group}'")

    root_group = root.custom_linked_item_group

    group_map = {
        g.name: g
        for g in groups
    }

    if root_group not in group_map:
        log(f"WARNING: Item Group '{root_group}' not found")
        return


    # ------------------------------------------------------------
    # Load existing dynamic navbar items
    # ------------------------------------------------------------

    navbar_items = [
        item
        for item in website_settings.top_bar_items
        if item.custom_is_dynamic
        or item == root
    ]

    log(f"Existing dynamic navbar items: {len(navbar_items)}")

    existing = {}

    for item in navbar_items:
        existing[item.label] = item

    log(f"Existing navbar lookup entries: {len(existing)}")

    for label, item in existing.items():
        log(
            f"EXISTING: "
            f"{label} "
            f"url={item.url}"
        )


    # ------------------------------------------------------------
    # Build Item Group tree
    # ------------------------------------------------------------

    build_group_tree(
        root_group,
        groups,
        level=0
    )


    # ------------------------------------------------------------
    # Flatten Item Group tree
    # ------------------------------------------------------------

    nodes = get_group_nodes(
        root_group,
        groups
    )

    log(f"Expected dynamic items: {len(nodes)}")

    for node in nodes:
        log(
            f"EXPECTED: "
            f"{node['name']} "
            f"level={node['level']} "
            f"parent={node['parent_group']} "
            f"url=/{node['route']}"
        )


    # ------------------------------------------------------------
    # Build expected Item Group list
    # ------------------------------------------------------------

    expected_groups = {
        node["name"]
        for node in nodes
    }

    expected_groups.add(root_group)


    # ------------------------------------------------------------
    # Remove orphaned dynamic navbar items
    # ------------------------------------------------------------

    for item in list(navbar_items):

        linked_group = item.custom_linked_item_group

        if not linked_group:
            continue

        if linked_group not in expected_groups:

            log(
                f"DELETE ORPHAN: "
                f"{item.label} "
                f"linked_group={linked_group}"
            )

            website_settings.top_bar_items.remove(item)
            navbar_items.remove(item)


    # ------------------------------------------------------------
    # Build Item Group -> Navbar mapping
    # ------------------------------------------------------------

    group_to_nav = {
        root.custom_linked_item_group: root.label
    }

    for item in navbar_items:
        if (
            item.custom_is_dynamic
            and item.custom_linked_item_group
        ):
            group_to_nav[item.custom_linked_item_group] = item.label


    for group, label in group_to_nav.items():
        log(
            f"NAV MAP: "
            f"{group} -> {label}"
        )


    # ------------------------------------------------------------
    # Reconcile root item
    # ------------------------------------------------------------

    root_has_children = len(nodes) > 0

    expected_root_url = ""

    if not root_has_children:

        root_group = group_map.get(
            root.custom_linked_item_group
        )

        if root_group and root_group.route:
            expected_root_url = f"/{root_group.route}"


    if root.url != expected_root_url:

        log(
            f"ROOT UPDATE URL: "
            f"{root.label} "
            f"{root.url} -> {expected_root_url}"
        )

        root.url = expected_root_url


    # ------------------------------------------------------------
    # Reconciliation
    # ------------------------------------------------------------

    for node in sorted(nodes, key=lambda x: x["level"]):

        has_children = any(
            child["parent_group"] == node["name"]
            for child in nodes
        )

        expected_url = ""

        # Frappe rule:
        # Parent items cannot have URLs
        if not has_children:
            expected_url = f"/{node['route']}"


        # --------------------------------------------------------
        # Existing dynamic item
        # --------------------------------------------------------

        if node["name"] in existing:

            item = existing[node["name"]]

            log(
                f"MATCH: {node['name']}"
            )


            # ----------------------------------------------------
            # Check URL consistency
            # ----------------------------------------------------

            if item.url != expected_url:

                log(
                    f"UPDATE URL: "
                    f"{node['name']} "
                    f"{item.url} -> {expected_url}"
                )

                item.url = expected_url


            # ----------------------------------------------------
            # Check parent consistency
            # ----------------------------------------------------

            expected_parent = group_to_nav.get(
                node["parent_group"]
            )

            if item.parent_label != expected_parent:

                log(
                    f"UPDATE PARENT: "
                    f"{node['name']} "
                    f"{item.parent_label} -> {expected_parent}"
                )

                item.parent_label = expected_parent


            # Make available for children
            group_to_nav[node["name"]] = node["name"]

            continue


        # --------------------------------------------------------
        # Create missing dynamic item
        # --------------------------------------------------------

        parent_nav = group_to_nav.get(
            node["parent_group"]
        )

        if not parent_nav:
            log(
                f"WARNING: Cannot create {node['name']} "
                f"because parent {node['parent_group']} "
                f"is missing"
            )
            continue


        log(
            f"CREATE: "
            f"{node['name']} "
            f"parent={parent_nav} "
            f"url={expected_url}"
        )


        new_item = website_settings.append(
            "top_bar_items",
            {
                "label": node["name"],
                "url": expected_url,
                "parent_label": parent_nav,
                "custom_is_dynamic": 1,
                "custom_linked_item_group": node["name"],
            }
        )


        # Make available for children
        group_to_nav[node["name"]] = node["name"]


        log(
            f"CREATED: {new_item.label}"
        )


    # ------------------------------------------------------------
    # Save once after all changes
    # ------------------------------------------------------------

    log(
        f"Saving Website Settings with "
        f"{len(website_settings.top_bar_items)} navbar items"
    )

    website_settings.save()