from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any


OUT = Path("grafana/dashboards/giro-ditalia-2026-race-control-v12.json")
GRAFANA_VERSION = "13.0.1"
DS_NAME = "infinity"
DASHBOARD_NAME = "giro-race-control-v12"
DASHBOARD_TITLE = "Giro d'Italia 2026 - Race Control v12"


def datasource() -> dict[str, str]:
    return {"name": DS_NAME}


def endpoint(path: str) -> str:
    return "${giro_api_base}" + path


def panel_query(url: str, uql: str, ref_id: str = "A", source: str = "url") -> dict[str, Any]:
    return {
        "kind": "PanelQuery",
        "spec": {
            "hidden": False,
            "query": {
                "datasource": datasource(),
                "group": "yesoreyeram-infinity-datasource",
                "kind": "DataQuery",
                "spec": {
                    "columns": [],
                    "computed_columns": [],
                    "data": "",
                    "filters": [],
                    "format": "table",
                    "global_query_id": "",
                    "parser": "uql",
                    "query_mode": "standard",
                    "root_selector": "",
                    "source": source,
                    "type": "json",
                    "uql": uql,
                    "url": url,
                    "url_options": {
                        "body_content_type": "",
                        "body_graphql_query": "",
                        "body_graphql_variables": "",
                        "body_type": "",
                        "data": "",
                        "headers": [{"key": "User-Agent", "value": "Grafana Giro Race Control"}],
                        "method": "GET",
                        "params": [],
                    },
                },
                "version": "v0",
            },
            "refId": ref_id,
        },
    }


def query_group(queries: list[dict[str, Any]] | None = None, transformations: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {
        "kind": "QueryGroup",
        "spec": {
            "queries": queries or [],
            "queryOptions": {},
            "transformations": transformations or [],
        },
    }


def viz(group: str, options: dict[str, Any], field_defaults: dict[str, Any] | None = None, overrides: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {
        "group": group,
        "kind": "VizConfig",
        "spec": {
            "fieldConfig": {
                "defaults": field_defaults or {},
                "overrides": overrides or [],
            },
            "options": options,
        },
        "version": GRAFANA_VERSION,
    }


def panel(panel_id: int, title: str, description: str, group: str, options: dict[str, Any], queries: list[dict[str, Any]] | None = None, field_defaults: dict[str, Any] | None = None, transformations: list[dict[str, Any]] | None = None, overrides: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {
        "kind": "Panel",
        "spec": {
            "data": query_group(queries, transformations),
            "description": description,
            "id": panel_id,
            "links": [],
            "title": title,
            "vizConfig": viz(group, options, field_defaults, overrides),
        },
    }


def text_panel(panel_id: int, title: str, description: str, content: str) -> dict[str, Any]:
    return panel(
        panel_id,
        title,
        description,
        "text",
        {
            "code": {"language": "plaintext", "showLineNumbers": False, "showMiniMap": False},
            "content": content,
            "mode": "markdown",
        },
    )


def table_panel(panel_id: int, title: str, description: str, url: str, uql: str, sort_col: str | None = None, cell_height: str = "sm") -> dict[str, Any]:
    options: dict[str, Any] = {
        "cellHeight": cell_height,
        "footer": {"show": False, "reducer": ["sum"], "fields": ""},
        "showHeader": True,
        "sortBy": [{"desc": False, "displayName": sort_col}] if sort_col else [],
    }
    field_defaults = {
        "custom": {
            "align": "auto",
            "cellOptions": {"type": "auto"},
            "filterable": True,
            "footer": {"reducers": []},
            "inspect": False,
        },
        "thresholds": {"mode": "absolute", "steps": [{"color": "green", "value": 0}]},
    }
    return panel(panel_id, title, description, "table", options, [panel_query(url, uql)], field_defaults)


def stat_panel(panel_id: int, title: str, description: str, url: str, uql: str, unit: str = "short", color: str = "blue", field_name: str = "") -> dict[str, Any]:
    field_defaults = {
        "color": {"mode": "thresholds"},
        "mappings": [{"type": "special", "options": {"match": "null", "result": {"color": "gray", "text": "No data", "index": 0}}}],
        "thresholds": {"mode": "absolute", "steps": [{"color": color, "value": 0}]},
        "unit": unit,
    }
    options = {
        "colorMode": "background",
        "graphMode": "none",
        "justifyMode": "auto",
        "orientation": "auto",
        "reduceOptions": {"calcs": ["lastNotNull"], "fields": field_name, "values": False},
        "showPercentChange": False,
        "textMode": "auto",
        "wideLayout": True,
    }
    return panel(panel_id, title, description, "stat", options, [panel_query(url, uql)], field_defaults)


def gauge_panel(panel_id: int, title: str, description: str, url: str, uql: str) -> dict[str, Any]:
    field_defaults = {
        "color": {"mode": "thresholds"},
        "max": 100,
        "min": 0,
        "thresholds": {
            "mode": "absolute",
            "steps": [
                {"color": "red", "value": 0},
                {"color": "yellow", "value": 25},
                {"color": "green", "value": 70},
            ],
        },
        "unit": "percent",
    }
    options = {
        "orientation": "auto",
        "reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False},
        "showThresholdLabels": False,
        "showThresholdMarkers": True,
        "sizing": "auto",
    }
    return panel(panel_id, title, description, "gauge", options, [panel_query(url, uql)], field_defaults)


def item(name: str, x: int, y: int, w: int, h: int) -> dict[str, Any]:
    return {
        "kind": "GridLayoutItem",
        "spec": {
            "element": {"kind": "ElementReference", "name": name},
            "x": x,
            "y": y,
            "width": w,
            "height": h,
        },
    }


def row(title: str, collapse: bool, items: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "kind": "RowsLayoutRow",
        "spec": {
            "collapse": collapse,
            "collapsed": collapse,
            "layout": {"kind": "GridLayout", "spec": {"items": items}},
            "title": title,
        },
    }


def constant_variable(name: str, label: str, value: str, hide: str = "hideVariable") -> dict[str, Any]:
    return {
        "kind": "ConstantVariable",
        "spec": {
            "current": {"text": value, "value": value},
            "hide": hide,
            "label": label,
            "name": name,
            "query": value,
            "skipUrlSync": True,
        },
    }


def variables() -> list[dict[str, Any]]:
    return [
        {
            "kind": "DatasourceVariable",
            "spec": {
                "allowCustomValue": True,
                "current": {"text": "Infinity", "value": DS_NAME},
                "hide": "dontHide",
                "includeAll": False,
                "label": "Infinity datasource",
                "multi": False,
                "name": "DS_INFINITY",
                "options": [],
                "pluginId": "yesoreyeram-infinity-datasource",
                "refresh": "onDashboardLoad",
                "regex": "",
                "skipUrlSync": False,
            },
        },
        {
            "kind": "CustomVariable",
            "spec": {
                "allowCustomValue": True,
                "current": {"text": "5", "value": "5"},
                "hide": "dontHide",
                "includeAll": False,
                "label": "Stage",
                "multi": False,
                "name": "stage",
                "options": [{"selected": i == 5, "text": str(i), "value": str(i)} for i in range(1, 22)],
                "query": ",".join(str(i) for i in range(1, 22)),
                "skipUrlSync": False,
                "valuesFormat": "csv",
            },
        },
        {
            "kind": "CustomVariable",
            "spec": {
                "allowCustomValue": True,
                "current": {"text": "NCI - Netcompany Ineos", "value": "NCI"},
                "hide": "dontHide",
                "includeAll": False,
                "label": "Watched team code",
                "multi": False,
                "name": "watched_team_code",
                "options": [{"selected": True, "text": "NCI - Netcompany Ineos", "value": "NCI"}],
                "query": "NCI : NCI - Netcompany Ineos",
                "skipUrlSync": False,
                "valuesFormat": "csv",
            },
        },
        constant_variable("giro_api_base", "Giro data service URL", "http://giro-data:8080"),
        constant_variable("giro_public_base", "Giro public asset URL", "http://localhost:8088", "dontHide"),
        constant_variable("giro_base", "Official Giro base URL", "https://www.giroditalia.it/en"),
    ]


def build() -> dict[str, Any]:
    elements: dict[str, Any] = {}

    def add(name: str, spec: dict[str, Any]) -> None:
        elements[name] = spec

    race_now = endpoint("/api/v1/stage/${stage}/race-now")
    updates = endpoint("/api/v1/stage/${stage}/updates?limit=5")
    updates_one = endpoint("/api/v1/stage/${stage}/updates?limit=1")
    front_groups = endpoint("/api/v1/stage/${stage}/front-groups")
    front_riders = endpoint("/api/v1/stage/${stage}/front-riders")
    ineos = endpoint("/api/v1/stage/${stage}/ineos?team=${watched_team_code}")

    add(
        "panel-1201",
        text_panel(
            1201,
            "Dashboard guide",
            "Explains the purpose and primary official data sources for the race-control dashboard.",
            "### Giro d'Italia 2026 race control\n\nThis dashboard prioritizes the live race questions: what is happening now, who is up front, how far is left, how fast the race is going, latest official updates, jersey leaders, and Netcompany Ineos status.\n\nPrimary live data comes from official Giro livefeed and headlines JSON. Classification panels use official Giro classification pages through the local `giro-data` normalization service.",
        ),
    )
    add(
        "panel-1202",
        text_panel(
            1202,
            "Race-control visual",
            "Decorative generated race-control visual. It does not provide race facts.",
            "![Generated Giro race-control visual](${giro_public_base}/assets/giro-control-room.svg)\n\nGenerated visual only. Race facts come from official Giro endpoints.",
        ),
    )
    add(
        "panel-1203",
        table_panel(
            1203,
            "Race right now",
            "Current selected stage state from the normalized official livefeed.",
            race_now,
            'parse-json\n| project "State"="state_label", "Stage"="stage_no", "Route"="route", "Profile"="profile", "Elapsed"="elapsed", "Speed"="avg_speed", "Done km"="done_km", "To go km"="km_to_go"',
            cell_height="md",
        ),
    )
    add(
        "panel-1204",
        table_panel(
            1204,
            "Latest official situation",
            "Most recent official headline/update from Giro headlines, cleaned by the local service.",
            updates_one,
            'parse-json\n| project "Time"="time", "Breaking"="breaking", "Title"="title", "Summary"="summary"',
            cell_height="md",
        ),
    )
    add("panel-1205", gauge_panel(1205, "Stage progress", "Percent of selected stage distance completed.", race_now, 'parse-json\n| project "Progress"="progress_pct"'))
    add("panel-1206", stat_panel(1206, "KM to go", "Kilometres remaining from the official livefeed.", race_now, 'parse-json\n| project "KM to go"="km_to_go"', "km", "red"))
    add("panel-1207", stat_panel(1207, "KM done", "Kilometres completed from the official livefeed.", race_now, 'parse-json\n| project "KM done"="done_km"', "km", "green"))
    add("panel-1208", stat_panel(1208, "Avg speed", "Average speed from the official livefeed, normalized to km/h.", race_now, 'parse-json\n| project "Avg speed"="avg_speed_kmh"', "velocitykmh", "blue"))
    add("panel-1209", stat_panel(1209, "Elapsed", "Elapsed stage time converted to minutes for a reliable numeric stat.", race_now, 'parse-json\n| project "Elapsed min"="elapsed_minutes"', "m", "purple"))
    add("panel-1210", stat_panel(1210, "Feed refresh", "Official livefeed refresh interval in seconds.", race_now, 'parse-json\n| project "Refresh sec"="feed_refresh_sec"', "s", "orange"))

    add(
        "panel-1301",
        table_panel(
            1301,
            "Current race groups",
            "Current race groups, gaps and rider counts from the official livefeed.",
            front_groups,
            'parse-json\n| project "Order"="order", "Group"="group_type", "KM"="km", "Gap"="gap", "Riders"="rider_count", "Names"="riders"',
            "Order",
        ),
    )
    add(
        "panel-1302",
        table_panel(
            1302,
            "Riders at the front",
            "Riders in live groups, ordered by group. The front group appears first.",
            front_riders,
            'parse-json\n| project "Group"="group_type", "Gap"="gap", "Rider"="rider", "Team"="team_code", "Front?"="is_front"',
        ),
    )
    add(
        "panel-1303",
        table_panel(
            1303,
            "INEOS watch badge",
            "Compact Netcompany Ineos metrics from livefeed, headlines and official classifications.",
            ineos,
            'parse-json\n| project "Metric"="metric", "Value"="value", "Source"="source"',
        ),
    )
    add(
        "panel-1304",
        table_panel(
            1304,
            "Latest official updates",
            "Latest five official updates/headlines with HTML stripped by the local service.",
            updates,
            'parse-json\n| project "Time"="time", "Breaking"="breaking", "Title"="title", "Summary"="summary", "Link"="link"',
            cell_height="md",
        ),
    )

    add(
        "panel-1401",
        table_panel(
            1401,
            "INEOS riders visible live",
            "Netcompany Ineos riders currently visible in official livefeed groups.",
            endpoint("/api/v1/stage/${stage}/ineos?team=${watched_team_code}&view=riders"),
            'parse-json\n| project "Group"="group_type", "Gap"="gap", "Rider"="rider", "Team"="team_code", "KM"="km"',
        ),
    )
    add(
        "panel-1402",
        table_panel(
            1402,
            "INEOS riders in front group",
            "Netcompany Ineos riders in the first livefeed group, if any.",
            endpoint("/api/v1/stage/${stage}/ineos?team=${watched_team_code}&view=front"),
            'parse-json\n| project "Group"="group_type", "Gap"="gap", "Rider"="rider", "Team"="team_code", "KM"="km"',
        ),
    )
    add(
        "panel-1403",
        table_panel(
            1403,
            "INEOS official-update mentions",
            "Official updates/headlines mentioning INEOS or Netcompany.",
            endpoint("/api/v1/stage/${stage}/ineos?team=${watched_team_code}&view=mentions"),
            'parse-json\n| project "Time"="time", "Title"="title", "Summary"="summary", "Source"="source"',
        ),
    )
    add(
        "panel-1404",
        table_panel(
            1404,
            "INEOS in official GC",
            "Netcompany Ineos riders found in the official GC classification parser.",
            endpoint("/api/v1/stage/${stage}/ineos?team=${watched_team_code}&view=gc"),
            'parse-json\n| project "Rank"="rank", "Rider"="rider", "Team"="team", "Time"="time", "Gap"="gap", "Source"="source"',
        ),
    )

    standings = {
        "gc": ("GC top 5", "Official general classification top five."),
        "points": ("Points top 5", "Official points classification top five."),
        "mountains": ("Mountains top 5", "Official mountains classification top five."),
        "youth": ("Youth top 5", "Official youth classification top five."),
        "team": ("Team top 5", "Official Super Team classification top five."),
    }
    for offset, (kind, (title, desc)) in enumerate(standings.items(), start=1):
        add(
            f"panel-15{offset:02d}",
            table_panel(
                1500 + offset,
                title,
                desc,
                endpoint(f"/api/v1/standings/{kind}?limit=5"),
                'parse-json\n| project "Rank"="rank", "Rider"="rider", "Team"="team", "Value"="value", "Gap"="gap", "Source"="source", "Status"="status", "Message"="message"',
                "Rank",
            ),
        )

    add(
        "panel-1601",
        table_panel(
            1601,
            "Source health",
            "Health and last-check status for the local service and official Giro sources.",
            endpoint("/api/v1/sources"),
            'parse-json\n| project "Source"="source", "OK"="ok", "URL"="url", "Error"="error", "Checked ms"="checked_at_ms"',
        ),
    )
    add(
        "panel-1602",
        table_panel(
            1602,
            "Weather checkpoints",
            "Weather checkpoints from the official livefeed for the selected stage.",
            endpoint("/api/v1/stage/${stage}/weather"),
            'parse-json\n| project "KM"="km", "Location"="location", "Description"="description", "Temperature"="temperature", "Wind"="wind"',
        ),
    )
    add(
        "panel-1603",
        table_panel(
            1603,
            "Full front-rider feed",
            "Full normalized rider/group feed for source inspection and troubleshooting.",
            front_riders,
            'parse-json\n| project "Group order"="group_order", "Group"="group_type", "Gap"="gap", "Rider"="rider", "Team"="team_code", "Front?"="is_front", "KM"="km"',
        ),
    )
    add(
        "panel-1604",
        table_panel(
            1604,
            "Route/visual source notes",
            "Route and visual metadata for the selected stage.",
            endpoint("/api/v1/stage/${stage}/visuals"),
            'parse-json\n| project "Stage"="stage", "Route"="route", "Profile"="profile", "Hero SVG"="hero_svg", "Official route"="official_route_url", "Note"="note"',
            cell_height="md",
        ),
    )
    add(
        "panel-1605",
        table_panel(
            1605,
            "All official updates",
            "More official updates/headlines for debugging and source inspection.",
            endpoint("/api/v1/stage/${stage}/updates?limit=25"),
            'parse-json\n| project "Time"="time", "Breaking"="breaking", "Title"="title", "Summary"="summary", "Link"="link"',
            cell_height="sm",
        ),
    )

    layout = {
        "kind": "RowsLayout",
        "spec": {
            "rows": [
                row(
                    "Race right now",
                    False,
                    [
                        item("panel-1201", 0, 0, 24, 3),
                        item("panel-1202", 0, 3, 8, 7),
                        item("panel-1203", 8, 3, 16, 3),
                        item("panel-1204", 8, 6, 16, 4),
                        item("panel-1205", 0, 10, 4, 4),
                        item("panel-1206", 4, 10, 4, 4),
                        item("panel-1207", 8, 10, 4, 4),
                        item("panel-1208", 12, 10, 4, 4),
                        item("panel-1209", 16, 10, 4, 4),
                        item("panel-1210", 20, 10, 4, 4),
                    ],
                ),
                row(
                    "Front of race",
                    False,
                    [
                        item("panel-1301", 0, 0, 8, 8),
                        item("panel-1302", 8, 0, 10, 8),
                        item("panel-1303", 18, 0, 6, 8),
                        item("panel-1304", 0, 8, 24, 7),
                    ],
                ),
                row(
                    "INEOS watch",
                    False,
                    [
                        item("panel-1401", 0, 0, 8, 7),
                        item("panel-1402", 8, 0, 8, 7),
                        item("panel-1403", 16, 0, 8, 7),
                        item("panel-1404", 0, 7, 24, 7),
                    ],
                ),
                row(
                    "GC & jerseys",
                    False,
                    [
                        item("panel-1501", 0, 0, 12, 8),
                        item("panel-1502", 12, 0, 12, 8),
                        item("panel-1503", 0, 8, 12, 8),
                        item("panel-1504", 12, 8, 12, 8),
                        item("panel-1505", 0, 16, 24, 8),
                    ],
                ),
                row(
                    "Details / Debug / Sources",
                    True,
                    [
                        item("panel-1601", 0, 0, 24, 7),
                        item("panel-1602", 0, 7, 12, 8),
                        item("panel-1603", 12, 7, 12, 8),
                        item("panel-1604", 0, 15, 24, 5),
                        item("panel-1605", 0, 20, 24, 9),
                    ],
                ),
            ]
        },
    }

    return {
        "annotations": [
            {
                "kind": "AnnotationQuery",
                "spec": {
                    "builtIn": True,
                    "enable": True,
                    "hide": True,
                    "iconColor": "rgba(0, 211, 255, 1)",
                    "name": "Annotations & Alerts",
                    "query": {
                        "datasource": {"name": "-- Grafana --"},
                        "group": "grafana",
                        "kind": "DataQuery",
                        "spec": {},
                        "version": "v0",
                    },
                },
            }
        ],
        "cursorSync": "Crosshair",
        "editable": True,
        "elements": elements,
        "layout": layout,
        "links": [
            {"asDropdown": False, "icon": "external link", "includeVars": True, "keepTime": True, "tags": [], "targetBlank": True, "title": "Official livefeed", "type": "link", "url": "${giro_base}/livefeed/tappa/${stage}/"},
            {"asDropdown": False, "icon": "external link", "includeVars": False, "keepTime": True, "tags": [], "targetBlank": True, "title": "Official classifications", "type": "link", "url": "${giro_base}/classifiche/"},
        ],
        "liveNow": True,
        "preload": False,
        "tags": ["giro-ditalia", "race-control", "infinity", "generated"],
        "timeSettings": {
            "autoRefresh": "30s",
            "autoRefreshIntervals": ["10s", "30s", "1m", "5m", "15m"],
            "from": "now-6h",
            "hideTimepicker": False,
            "timezone": "browser",
            "to": "now",
        },
        "title": DASHBOARD_TITLE,
        "variables": variables(),
    }


def wrap_dashboard(spec: dict[str, Any]) -> dict[str, Any]:
    return {
        "apiVersion": "dashboard.grafana.app/v2",
        "kind": "Dashboard",
        "metadata": {
            "name": DASHBOARD_NAME,
            "namespace": "default",
            "annotations": {
                "grafana.app/folder": "",
            },
        },
        "spec": spec,
    }


def _iter_layout_items(dashboard: dict[str, Any]) -> list[dict[str, Any]]:
    rows = dashboard.get("layout", {}).get("spec", {}).get("rows", [])
    items: list[dict[str, Any]] = []
    for row_index, row_obj in enumerate(rows):
        for item_obj in row_obj.get("spec", {}).get("layout", {}).get("spec", {}).get("items", []):
            spec = copy.deepcopy(item_obj["spec"])
            spec["_row"] = row_index
            spec["_row_title"] = row_obj.get("spec", {}).get("title", "")
            items.append(spec)
    return items


def validate(dashboard: dict[str, Any]) -> dict[str, Any]:
    if "spec" in dashboard and dashboard.get("kind") == "Dashboard":
        dashboard = dashboard["spec"]
    errors: list[str] = []
    elements = dashboard.get("elements", {})
    ids: dict[int, str] = {}
    query_count = 0
    risky_queries: list[str] = []

    for name, element in elements.items():
        spec = element.get("spec", {})
        panel_id = spec.get("id")
        if panel_id in ids:
            errors.append(f"duplicate panel id {panel_id}: {ids[panel_id]} and {name}")
        ids[panel_id] = name
        if not spec.get("description"):
            errors.append(f"panel {name} has empty description")
        for query in spec.get("data", {}).get("spec", {}).get("queries", []):
            query_count += 1
            qspec = query.get("spec", {}).get("query", {}).get("spec", {})
            qds = query.get("spec", {}).get("query", {}).get("datasource")
            if not qds:
                errors.append(f"panel {name} query missing datasource ref")
            uql = qspec.get("uql", "")
            if any(token in uql.lower() for token in ("jsonata", "percentage(", "round(")):
                risky_queries.append(f"{name}: {uql}")

    for item_spec in _iter_layout_items(dashboard):
        name = item_spec["element"]["name"]
        if name not in elements:
            errors.append(f"layout references missing element {name}")
        x, y, w, h = item_spec["x"], item_spec["y"], item_spec["width"], item_spec["height"]
        if x < 0 or y < 0 or w <= 0 or h <= 0:
            errors.append(f"invalid grid position for {name}: {item_spec}")
        if x + w > 24:
            errors.append(f"grid overflow for {name}: x+w={x + w}")

    for row_index, row_obj in enumerate(dashboard.get("layout", {}).get("spec", {}).get("rows", [])):
        visible_items = row_obj.get("spec", {}).get("layout", {}).get("spec", {}).get("items", [])
        for i, a in enumerate(visible_items):
            a_spec = a["spec"]
            ax1, ay1 = a_spec["x"], a_spec["y"]
            ax2, ay2 = ax1 + a_spec["width"], ay1 + a_spec["height"]
            for b in visible_items[i + 1 :]:
                b_spec = b["spec"]
                bx1, by1 = b_spec["x"], b_spec["y"]
                bx2, by2 = bx1 + b_spec["width"], by1 + b_spec["height"]
                if ax1 < bx2 and ax2 > bx1 and ay1 < by2 and ay2 > by1:
                    errors.append(f"visible overlap in row {row_index}: {a_spec['element']['name']} and {b_spec['element']['name']}")

    return {
        "panel_count": len(elements),
        "query_count": query_count,
        "duplicate_ids": len(ids) != len(elements),
        "grid_overflow": any("grid overflow" in err for err in errors),
        "visible_overlap": any("visible overlap" in err for err in errors),
        "datasource_variable": "DS_INFINITY",
        "risky_queries": risky_queries,
        "errors": errors,
    }


def main() -> None:
    dashboard = wrap_dashboard(build())
    report = validate(dashboard)
    if report["errors"]:
        raise SystemExit(json.dumps(report, indent=2))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(dashboard, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
