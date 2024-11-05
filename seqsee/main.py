import copy
import json
import sys
import os
from jsonschema import validate
from jsonschema.exceptions import ValidationError
from jinja2 import Environment, FileSystemLoader

# The distance between successive x or y coordinates. Units are in pixels.
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
            if isinstance(value, dict) or isinstance(value, CssStyle):
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

        return result


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


def generate_style_from_attributes(attributes):
    """This function generates CSS styles from the attributes of a node or edge. Note that it
    ignores style aliases, that are handled by the CSS itself."""
    new_style = CssStyle()
    for attr in attributes:
        if isinstance(attr, dict):
            # This is a raw attribute object
            for key, value in attr.items():
                if key == "color":
                    new_style += {"fill": value, "stroke": value}
                elif key == "size":
                    new_style += {"r": scale * float(value)}
                elif key == "thickness":
                    new_style += {"stroke-width": value}
                elif key == "arrowTip":
                    new_style += f"marker-end: url(#arrow-{value});\n"
        elif isinstance(attr, str):
            # This is a style alias
            new_style += global_css["." + attr]
    return new_style


def generate_static_svg_content(data):
    static_svg_content = "<g id='edges-group'>\n"

    # Generate edges
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
        styles = generate_style_from_attributes(attributes)

        static_svg_content += f'<line x1="{x1}" y1="{y1}" x2="{target_x}" y2="{target_y}" style="{styles.generate()}"></line>\n'

    static_svg_content += '</g><g id="nodes-group">\n'

    # Generate nodes
    for node_id, node in data.get("nodes", {}).items():
        cx = node["x"] * scale
        cy = node["y"] * scale
        attributes = node.get("attributes", [])
        classes = " ".join([attr for attr in attributes if isinstance(attr, str)])
        if any([isinstance(attr, dict) and "size" in attr for attr in attributes]):
            radius = scale * int(next((attr["size"] for attr in attributes)))
            r_tag = f"r={radius}px"
        else:
            r_tag = ""
        label = node.get("label", "")

        static_svg_content += f'<circle id="{node_id}" cx="{cx}" cy="{cy}" {r_tag} data-label="{label}"></circle>\n'

    static_svg_content += "</g>\n"
    return static_svg_content


def generate_html(data):
    generate_css_styles(data)
    static_svg_content = generate_static_svg_content(data)
    template = load_template()
    html_output = template.render(
        data=data,
        spacing=scale,
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
        global_css += {css_class: generate_style_from_attributes(attributes_list)}

    # Generate CSS classes for color aliases
    for color_name, color_value in color_aliases.items():
        global_css += {color_name: {"fill": color_value, "stroke": color_value}}

    # Generate CSS classes for attribute aliases
    for alias_name, attributes_list in attribute_aliases.items():
        global_css += {
            "." + alias_name: generate_style_from_attributes(attributes_list)
        }


def main():
    if len(sys.argv) != 3:
        print("Usage: visualizer <input.json> <output.html>")
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

    # Generate HTML
    html_content = generate_html(data)

    # Write to output file
    with open(output_file, "w") as f:
        f.write(html_content)

    print(f"Generated {output_file} successfully.")


if __name__ == "__main__":
    main()
