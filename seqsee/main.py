import copy
import json
import sys
import os
from jsonschema import validate
from jsonschema.exceptions import ValidationError
from jinja2 import Environment, FileSystemLoader

# The distance between successive x or y coordinates. Units are in pixels. This will be fixed
# throughout the html file, but zooming is implemented through a transformation matrix applied to
# the <g> element that contains the nodes, edges, and background grid.
scale = 50


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


def load_template():
    env = Environment(loader=FileSystemLoader(searchpath=os.path.dirname(__file__)))
    template = env.get_template("template.html.jinja")
    return template


def style_and_aliases_from_attributes(attributes):
    """Given a list of attributes, return a CssStyle object that contains the union of all raw
    attribute objects, and a list of aliases. We return the aliases separately because we may want
    to specify them in a `class` attribute instead of a `style` attribute."""

    new_style = CssStyle()
    aliases = []
    for attr in attributes:
        if isinstance(attr, dict):
            # This is a raw attribute object
            for key, value in attr.items():
                if key == "color":
                    if (value_key := "." + value) in global_css.keys():
                        new_style += global_css[value_key]
                    else:
                        new_style += {"fill": value, "stroke": value}
                elif key == "size":
                    new_style += {"r": scale * float(value)}
                elif key == "thickness":
                    new_style += {"stroke-width": scale * float(value)}
                elif key == "arrowTip":
                    new_style += {"marker-end": f"url(#arrow-{value})"}
        elif isinstance(attr, str):
            # This is a style alias
            aliases.append(attr)
    return (new_style, aliases)


def generate_style(style, aliases):
    """Collapse a list of styles and aliases into a single style object."""
    style = copy.deepcopy(style)
    for alias in aliases:
        style.append(global_css["." + alias])
    return style


def generate_static_svg_content(data):

    def generate_nodes(data):
        nodes_svg = '<g id="nodes-group">\n'

        for node_id, node in data.get("nodes", {}).items():
            cx = node["x"] * scale
            cy = node["y"] * scale

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

    def generate_edges(data):
        edges_svg = '<g id="edges-group">\n'
        for edge in data.get("edges", []):
            source = data["nodes"][edge["source"]]
            if "target" in edge:
                target = data["nodes"][edge["target"]]
                target_x = target["x"] * scale
                target_y = target["y"] * scale
            elif "offset" in edge:
                target_x = (source["x"] + edge["offset"]["x"]) * scale
                target_y = (source["y"] + edge["offset"]["y"]) * scale
            else:
                # Impossible due to schema
                raise NotImplementedError

            x1 = source["x"] * scale
            y1 = source["y"] * scale

            attributes = edge.get("attributes", [])
            style, aliases = style_and_aliases_from_attributes(attributes)
            style = style.generate(indent=0).replace("\n", " ").strip(" {}")
            if style:
                style = f'style="{style}"'
            aliases = " ".join(aliases)

            edges_svg += f'<line x1="{x1}" y1="{y1}" x2="{target_x}" y2="{target_y}" class="{aliases}" {style}></line>\n'

        edges_svg += "</g>\n"
        return edges_svg

    # We generate nodes after edges so that they are drawn on top
    return generate_edges(data) + generate_nodes(data)


def generate_html(data):
    generate_css_styles(data)
    static_svg_content = generate_static_svg_content(data)
    template = load_template()
    html_output = template.render(
        data=data,
        title=data.get("header", {}).get("title", "").replace("$", ""),
        spacing=scale,
        chart_width=data.get("header", {}).get("dimensions", {}).get("width", 10),
        chart_height=data.get("header", {}).get("dimensions", {}).get("height", 10),
        css_styles=global_css.generate(),
        static_svg_content=static_svg_content,
    )
    return html_output


def generate_css_styles(data):
    global global_css

    color_aliases = data.get("header", {}).get("aliases", {}).get("colors", {})
    attribute_aliases = data.get("header", {}).get("aliases", {}).get("attributes", {})
    default_attributes = data.get("header", {}).get("defaultAttributes", {})

    # Generate CSS classes for defaultAttributes
    for element_type, attributes_list in default_attributes.items():
        if element_type == "nodes":
            css_class = "circle"
        elif element_type == "edges":
            css_class = "line"
        else:
            raise ValueError
        style, aliases = style_and_aliases_from_attributes(attributes_list)
        global_css += {css_class: generate_style(style, aliases)}

    # Generate CSS classes for color aliases
    for color_name, color_value in color_aliases.items():
        global_css += {"." + color_name: {"fill": color_value, "stroke": color_value}}

    # Generate CSS classes for attribute aliases
    for alias_name, attributes_list in attribute_aliases.items():
        style, aliases = style_and_aliases_from_attributes(attributes_list)
        global_css += {"." + alias_name: generate_style(style, aliases)}


def main():
    if len(sys.argv) != 3:
        print("Usage: seqsee <input.json> <output.html>")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]

    # Load input JSON
    with open(input_file, "r") as f:
        data = json.load(f)

    # Load schema and validate
    schema = load_schema()
    try:
        validate(instance=data, schema=schema)
    except ValidationError as e:
        print("Input JSON validation error:")
        print(e)
        sys.exit(1)

    global scale
    scale = data.get("header", {}).get("dimensions", {}).get("scale", 50)

    # Generate HTML
    html_content = generate_html(data)

    # Write to output file
    with open(output_file, "w") as f:
        f.write(html_content)

    print(f"Generated {output_file} successfully.")


if __name__ == "__main__":
    main()
