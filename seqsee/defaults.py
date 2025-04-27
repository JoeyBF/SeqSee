SCHEMA_DEFAULTS = {
    "header": {
        "metadata": {"htmltitle": ""},
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
}


def get_value_at_path(data, path):
    current_value = data

    for key in path:
        current_value = current_value[key]

    return current_value


def get_schema_default(path):
    """
    Get the default value from the schema at the given path.

    This is useful for when we need to know the default value of a field in the schema, but the field
    is not present in the data.
    """

    return get_value_at_path(SCHEMA_DEFAULTS, path)


def get_value_or_schema_default(data, path):
    """
    Attempt to get a value from `data` at the given path.

    If it is not specified, get the default value from the schema. The schema is always assumed to
    contain a default value for the given path.
    """

    try:
        return get_value_at_path(data, path)
    except KeyError:
        return get_schema_default(path)
