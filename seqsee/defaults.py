SCHEMA_DEFAULTS = {
    "header": {
        "metadata": {"htmltitle": "", "title": ""},
        "chart": {
            "width": {"min": None, "max": None},
            "height": {"min": None, "max": None},
            "scale": 60.00,
            "nodeSize": 0.04,
            "nodeSpacing": 0.02,
            "nodeSlope": 0.00,
        },
        "aliases": {
            "colors": {
                "backgroundColor": "white",
                "borderColor": "black",
                "textColor": "black",
            },
            "attributes": {
                "grid": [{"color": "#ccc", "thickness": 0.01}],
                "defaultNode": [{"color": "black"}],
                "defaultEdge": [{"color": "black", "thickness": 0.02}],
            },
        },
    },
    "nodes": {
        "position": 0,
    },
    "edges": {},
}


def get_schema_default(path):
    """
    Get the default value from the schema at the given path.

    This is useful for when we need to know the default value of a field in the schema, but the field
    is not present in the data.
    """

    current_value = SCHEMA_DEFAULTS

    for key in path:
        current_value = current_value[key]

    return current_value
