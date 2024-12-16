import copy
import json
import jsonschema
import math
import sys
import os
from collections import defaultdict
from jsonschema.exceptions import ValidationError
from jinja2 import Environment, FileSystemLoader

# The distance between successive x or y coordinates. Units are in pixels. This will be fixed
# throughout the html file, but zooming is implemented through a transformation matrix applied to
# the <g> element that contains the nodes, edges, and background grid.
scale = None


# Lifted/adapted from MIT-licensed https://github.com/slacy/pyssed/
class CssStyle:
    """A list of CSS styles, but stored as a dict.
    Can contain nested styles."""

    def __init__(self, *args, **kwargs):
        self._styles = {}
        for a in args:
            self.append(a)

        for name, value in kwargs.items():
            self._styles[name] = value

    def __getitem__(self, key):
        return self._styles[key]

    def keys(self):
        """Return keys of the style dict."""
        return self._styles.keys()

    def items(self):
        """Return iterable contents."""
        return self._styles.items()

    def append(self, other):
        """Append style 'other' to self."""
        self._styles = self.__add__(other)._styles

    def __add__(self, other):
        """Add self and other, and return a new style instance."""
        summed = copy.deepcopy(self)
        if isinstance(other, str):
            single = other.split(":")
            summed._styles[single[0]] = single[1]
        elif isinstance(other, dict):
            summed._styles.update(other)
        elif isinstance(other, CssStyle):
            summed._styles.update(other._styles)
        else:
            raise "Bad type for style"
        return summed

    def __repr__(self):
        return str(self._styles)

    def generate(self, parent="", indent=4):
        """Given a dict mapping CSS selectors to a dict of styles, generate a
        list of lines of CSS output."""
        subnodes = []
        stylenodes = []
        result = []

        for name, value in self.items():
            # If the sub node is a sub-style...
            if isinstance(value, dict):
                subnodes.append((name, CssStyle(value)))
            elif isinstance(value, CssStyle):
                subnodes.append((name, value))
            # Else, it's a string, and thus, a single style element
            elif (
                isinstance(value, str)
                or isinstance(value, int)
                or isinstance(value, float)
            ):
                stylenodes.append((name, value))
            else:
                raise "Bad error"

        if stylenodes:
            result.append(parent.strip() + " {")
            for stylenode in stylenodes:
                attribute = stylenode[0].strip(" ;:")
                if isinstance(stylenode[1], str):
                    # string
                    value = stylenode[1].strip(" ;:")
                else:
                    # everything else (int or float, likely)
                    value = str(stylenode[1]) + "px"

                result.append(" " * indent + "%s: %s;" % (attribute, value))

            result.append("}")
            result.append("")  # a newline

        for subnode in subnodes:
            result += subnode[1].generate(
                parent=(parent.strip() + " " + subnode[0]).strip()
            )

        if parent == "":
            ret = "\n".join(result)
        else:
            ret = result

        return ret


global_css = CssStyle()


def load_schema():
    schema_path = os.path.join(os.path.dirname(__file__), "input_schema.json")
    with open(schema_path, "r") as f:
        schema = json.load(f)
    return schema


schema = load_schema()


def load_template():
    env = Environment(loader=FileSystemLoader(searchpath=os.path.dirname(__file__)))
    template = env.get_template("template.html.jinja")
    return template


def get_value_or_schema_default(data, path):
    """
    Attempt to get a value from `data` at the given path.

    If it is not specified, get the default value from the schema. The schema is always assumed to
    contain a default value for the given path.
    """

    try:
        current_value = data
        for key in path:
            current_value = current_value[key]
        return current_value
    except KeyError:
        default_value = schema
        for key in path:
            default_value = default_value["properties"][key]
        return default_value["default"]


def cssify_name(name):
    """
    Get a CSS-safe identifier from a name.

    This is more complicated than just adding a period. This is because aliases can start with
    numbers, but CSS classes cannot.
    """
    if name.isnumeric():
        name = "n" + name
    return "." + name


def style_and_aliases_from_attributes(attributes):
    """
    Given a list of attributes, return a `CssStyle` object that contains the union of all raw
    attribute objects, and a list of aliases.

    We return the aliases separately because we may want to specify them in a `class` attribute
    instead of a `style` attribute.
    """

    new_style = CssStyle()
    aliases = []
    for attr in attributes:
        if isinstance(attr, dict):
            # This is a raw attribute object
            for key, value in attr.items():
                if key == "color":
                    if (value_key := cssify_name(value)) in global_css.keys():
                        # This is a color alias
                        new_style += global_css[value_key]
                    else:
                        # This is a CSS color value
                        new_style += {"fill": value, "stroke": value}
                elif key == "size":
                    new_style += {"r": scale * float(value)}
                elif key == "thickness":
                    new_style += {"stroke-width": scale * float(value)}
                elif key == "arrowTip":
                    if value == "none":
                        new_style += {"marker-end": "none"}
                    else:
                        # We only support a few hardcoded arrow tips. To define a new arrow tip
                        # `foo`, you need to define a `<marker>` element with id `arrow-foo` in the
                        # template file. See the `arrow-simple` marker for an example.
                        new_style += {"marker-end": f"url(#arrow-{value})"}
                elif key == "pattern":
                    # We only support a few hardcoded patterns
                    if value == "solid":
                        new_style += {"stroke-dasharray": "none"}
                    elif value == "dashed":
                        new_style += {"stroke-dasharray": "5, 5"}
                    elif value == "dotted":
                        new_style += {
                            "stroke-dasharray": "0, 2",
                            "stroke-linecap": "round",
                        }
                    # Other values impossible due to schema
                else:
                    # Just treat the key-value pair as raw CSS
                    new_style += {key: value}
        elif isinstance(attr, str):
            # This is a style alias
            aliases.append(cssify_name(attr).removeprefix("."))
    return (new_style, aliases)


def generate_style(style, aliases):
    """Collapse a list of styles and aliases into a single `CssStyle` object."""
    style = copy.deepcopy(style)
    for alias in aliases:
        style.append(global_css[cssify_name(alias)])
    return style


def ensure_json_path_is_defined(data, path):
    """
    Ensure that the path exists in the JSON data, creating it if necessary.

    This modifies `data` in-place. If the path doesn't already exist, we create a JSON object, which
    is equivalent to a Python `dict`.
    """

    current_value = data
    for key in path:
        if key not in current_value:
            current_value[key] = {}
        current_value = current_value[key]


def compute_chart_dimensions(data):
    """
    This modifies `data` in-place to set `header.chart.width` and `header.chart.height`, if they are
    `null` in the input.

    The width and height are calculated based on the positions of the nodes in the chart. We give
    the smallest even size that makes the last column/row empty. We default to a 2x2 grid if there
    are no nodes.
    """

    nodes = data.get("nodes", {})

    def compute_dimension(dim_name, coord_name, default):
        if data.get("header", {}).get("chart", {}).get(dim_name) is None:
            ensure_json_path_is_defined(data, ["header", "chart", dim_name])
            # Smallest even number strictly greater than the maximum coordinate of any node
            dimension = 2 * (
                max((node[coord_name] for node in nodes.values()), default=default) // 2
                + 1
            )
            data["header"]["chart"][dim_name] = dimension

    # Arbitrary default values. These are only used if there are no nodes.
    compute_dimension("width", "x", 0)
    compute_dimension("height", "y", 0)


def calculate_absolute_positions(data):
    """
    Compute the final positions of the nodes in the chart.

    This modifies `data` in-place to add attributes `absoluteX` and `absoluteY`. They will be used
    by the SVG generation code to place the nodes at the correct positions and to draw the edges.
    """

    nodes_by_bidegree = defaultdict(list)

    # Group nodes by bidegree
    for node_id, node in data.get("nodes", {}).items():
        x, y = node["x"], node["y"]
        nodes_by_bidegree[x, y].append(node_id)

    # Sort bidegrees by the `position` attribute of the nodes
    default_position = schema["properties"]["nodes"]["additionalProperties"][
        "properties"
    ]["position"]["default"]
    for bidegree, nodes in nodes_by_bidegree.items():
        nodes_by_bidegree[bidegree] = sorted(
            nodes,
            key=lambda node_id: data["nodes"][node_id].get(
                "position", default_position
            ),
        )

    # Get defaults and compute constants
    node_size = get_value_or_schema_default(data, ["header", "chart", "nodeSize"])
    node_spacing = get_value_or_schema_default(data, ["header", "chart", "nodeSpacing"])
    node_slope = get_value_or_schema_default(data, ["header", "chart", "nodeSlope"])

    distance_between_centers = node_spacing + 2 * node_size

    # Calculate the angle of the line that the nodes will be placed on
    if node_slope is not None:
        theta = math.atan(node_slope)
    else:
        # null means vertical
        theta = math.pi / 2

    # Calculate absolute positions
    for (x, y), nodes in nodes_by_bidegree.items():
        bidegree_rank = len(nodes)
        first_center_to_last_center = (bidegree_rank - 1) * distance_between_centers
        for i, node_id in enumerate(nodes):
            offset = -first_center_to_last_center / 2 + i * distance_between_centers
            data["nodes"][node_id]["absoluteX"] = x + offset * math.cos(theta)
            data["nodes"][node_id]["absoluteY"] = y + offset * math.sin(theta)


def generate_nodes_svg(data):
    """Generate an SVG <g> element containing all nodes."""

    nodes_svg = '<g id="nodes-group">\n'

    for node_id, node in data.get("nodes", {}).items():
        cx = node["absoluteX"] * scale
        cy = node["absoluteY"] * scale

        attributes = node.get("attributes", [])
        style, aliases = style_and_aliases_from_attributes(attributes)
        style = style.generate(indent=0).replace("\n", " ").strip(" {}")
        if style:
            style = f'style="{style}"'
        aliases = " ".join(aliases)

        label = node.get("label", "")

        nodes_svg += f'<circle id="{node_id}" class="{aliases}" cx="{cx}" cy="{cy}" {style} data-label="{label}"></circle>\n'

    nodes_svg += "</g>\n"
    return nodes_svg


def generate_edges_svg(data):
    """Generate an SVG <g> element containing all edges."""

    edges_svg = '<g id="edges-group">\n'

    for edge in data.get("edges", []):
        source = data["nodes"][edge["source"]]
        if "target" in edge:
            target = data["nodes"][edge["target"]]
            target_x = target["absoluteX"] * scale
            target_y = target["absoluteY"] * scale
        elif "offset" in edge:
            target_x = (source["absoluteX"] + edge["offset"]["x"]) * scale
            target_y = (source["absoluteY"] + edge["offset"]["y"]) * scale
        else:
            # Impossible due to schema
            raise NotImplementedError

        x1 = source["absoluteX"] * scale
        y1 = source["absoluteY"] * scale

        attributes = edge.get("attributes", [])
        style, aliases = style_and_aliases_from_attributes(attributes)
        style = style.generate(indent=0).replace("\n", " ").strip(" {}")
        aliases = " ".join(aliases)

        if edge.get("bezier"):
            control_points = edge["bezier"]
            if len(control_points) == 1:
                control_x = control_points[0]["x"] * scale + x1
                control_y = control_points[0]["y"] * scale + y1
                curve_d = f"Q {control_x} {control_y} {target_x} {target_y}"
            elif len(control_points) == 2:
                control0_x = control_points[0]["x"] * scale + x1
                control0_y = control_points[0]["y"] * scale + y1
                control1_x = control_points[1]["x"] * scale + target_x
                control1_y = control_points[1]["y"] * scale + target_y
                curve_d = f"C {control0_x} {control0_y} {control1_x} {control1_y} {target_x} {target_y}"
            else:
                # Impossible due to schema
                raise NotImplementedError
            edge_svg = f'<path d="M {x1} {y1} {curve_d}" class="{aliases}" style="fill: none;{style}"></path>\n'
        else:
            edge_svg = f'<line x1="{x1}" y1="{y1}" x2="{target_x}" y2="{target_y}" class="{aliases}" style="{style}"></line>\n'

        # Remove empty style attribute for cleaner output. This is not strictly necessary, but it
        # makes me feel better.
        edges_svg += edge_svg.replace(' style=""', "")

    edges_svg += "</g>\n"
    return edges_svg


def generate_svg(data):
    # First make sure that the absolute positions are calculated
    calculate_absolute_positions(data)
    # We generate nodes after edges so that they are drawn on top
    return generate_edges_svg(data) + generate_nodes_svg(data)


def generate_html(data):
    # Generate CSS styles to be placed in <head>
    generate_css_styles(data)
    # Calculate chart dimensions
    compute_chart_dimensions(data)
    # Generate SVG content
    static_svg_content = generate_svg(data)

    template = load_template()
    html_output = template.render(
        data=data,
        spacing=scale,
        css_styles=global_css.generate(),
        static_svg_content=static_svg_content,
    )
    return html_output


def generate_css_styles(data):
    """Populate the global_css variable with CSS classes for color and attribute aliases."""
    global global_css

    color_aliases = get_value_or_schema_default(data, ["header", "aliases", "colors"])
    attribute_aliases = get_value_or_schema_default(
        data, ["header", "aliases", "attributes"]
    )

    # We do nodes and edges separately because they have default values, but defaultAttributes
    # itself doesn't. We don't want to give it a default value either, because the user should be
    # able to specify only one and have the other one be the default.
    default_node_attributes = get_value_or_schema_default(
        data, ["header", "defaultAttributes", "nodes"]
    )
    default_edge_attributes = get_value_or_schema_default(
        data, ["header", "defaultAttributes", "edges"]
    )

    # Generate CSS classes for color aliases. We do it first because we may need to reference them
    # in the default attributes.
    for color_name, color_value in color_aliases.items():
        global_css += {
            cssify_name(color_name): {"fill": color_value, "stroke": color_value}
        }

    # Generate CSS classes for defaultAttributes
    ## First for nodes
    style, aliases = style_and_aliases_from_attributes(default_node_attributes)
    generated_style = generate_style(style, aliases)

    node_size = get_value_or_schema_default(data, ["header", "chart", "nodeSize"])
    generated_style += {"stroke-width": 0, "r": scale * node_size}

    global_css += {"circle": generated_style}

    ## Then for edges
    style, aliases = style_and_aliases_from_attributes(default_edge_attributes)
    global_css += {"line": generate_style(style, aliases)}

    # Generate CSS classes for attribute aliases
    for alias_name, attributes_list in attribute_aliases.items():
        style, aliases = style_and_aliases_from_attributes(attributes_list)
        global_css += {cssify_name(alias_name): generate_style(style, aliases)}


def process_json(input_file, output_file):
    global global_css

    # Load input JSON
    with open(input_file, "r") as f:
        data = json.load(f)

    # validate against schema
    try:
        jsonschema.validate(instance=data, schema=schema)
    except ValidationError as e:
        print("Input JSON validation error:")
        print(e)
        sys.exit(1)

    global scale
    scale = get_value_or_schema_default(data, ["header", "chart", "scale"])

    # Generate HTML
    html_content = generate_html(data)

    # Write to output file
    with open(output_file, "w") as f:
        f.write(html_content)

    print(f"Generated {output_file} successfully.")

    # Reset global_css for the next file
    global_css = CssStyle()


def main():
    if len(sys.argv) != 3:
        print("Usage: seqsee <input.json> <output.html>")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]

    process_json(input_file, output_file)


if __name__ == "__main__":
    main()
