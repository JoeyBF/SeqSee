import copy
import json
import jsonschema
import math
import sys
import os
from collections import defaultdict
from jinja2 import Environment, FileSystemLoader
import pydantic
from seqsee.chart_internals import (
    Attribute,
    Attributes,
    DimensionRange,
    Edge,
    Header,
    Node,
)
from typing import Callable, Dict, List, Optional


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


def css_class_name(name):
    """
    Given a name, return a CSS class name. This is done by prefixing the name with a dot.
    """
    return "." + name


def style_and_aliases_from_attributes(attributes: Attributes):
    """
    Given a list of attributes, return a `CssStyle` object that contains the union of all raw
    attribute objects, and a list of aliases.

    We return the aliases separately because we may want to specify them in a `class` attribute
    instead of a `style` attribute.
    """

    new_style = CssStyle()
    aliases: List[str] = []

    for attr in attributes:
        if isinstance(attr, Attribute):
            # This is a raw attribute object
            for key, value in attr.items():
                if key == "color":
                    new_style += {"fill": value, "stroke": value}
                elif key == "size":
                    new_style += {"r": f"calc({float(value)} * var(--spacing))"}
                elif key == "thickness":
                    new_style += {
                        "stroke-width": f"calc({float(value)} * var(--spacing))"
                    }
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
            aliases.append(attr)
    return (new_style, aliases)


class Chart(pydantic.BaseModel):
    header: Header = Header()
    nodes: Dict[str, Node] = {}
    edges: List[Edge] = []

    model_config = pydantic.ConfigDict(extra="allow", arbitrary_types_allowed=True)
    _chart_css: Optional[CssStyle] = None

    def __init__(self, chart_spec):
        # validate against schema
        jsonschema.validate(instance=chart_spec, schema=schema)
        super().__init__(**chart_spec)

        self.generate_css_styles()

    def compute_chart_dimensions(self):
        """
        This replaces the null values in `self.width` and `self.height` by autodetected boundaries.

        The bounds on the width and height are calculated based on the positions of the nodes in the
        chart. For maximum values, we give the smallest even size that makes the last column/row
        empty. We do the opposite for minimum values. Defaults to a 4x4 grid centered at the origin
        if there are no nodes.
        """

        def compute_dimension_bounds(
            dim_range: DimensionRange, coord: Callable[[Node], int], default: int
        ):
            coords = [coord(node) for node in self.nodes.values()]

            if dim_range.min is None:
                # Greatest even number strictly smaller than the minimum coordinate of any node
                dimension = 2 * (min(coords, default=default) // 2 - 1)
                dim_range.min = dimension

            if dim_range.max is None:
                # Smallest even number strictly greater than the maximum coordinate of any node
                dimension = 2 * (max(coords, default=default) // 2 + 1)
                dim_range.max = dimension

        # Arbitrary default values. These are only used if there are no nodes.
        compute_dimension_bounds(self.header.chart.width, lambda node: node.x, 0)
        compute_dimension_bounds(self.header.chart.height, lambda node: node.y, 0)

    def calculate_absolute_positions(self):
        """
        Compute the final positions of the nodes in the chart.

        This computes the values of the `_absoluteX` and `_absoluteY` properties of all nodes in
        `self.nodes`. Those values will be used by the SVG generation code to place the nodes at the
        correct positions and to draw the edges.
        """

        nodes_by_bidegree = defaultdict(list)

        # Group nodes by bidegree
        for node_id, node in self.nodes.items():
            x, y = node.x, node.y
            nodes_by_bidegree[x, y].append(node_id)

        # Sort bidegrees by the `position` attribute of the nodes
        for bidegree, nodes in nodes_by_bidegree.items():
            nodes_by_bidegree[bidegree] = sorted(
                nodes, key=lambda node_id: self.nodes[node_id].position
            )

        # Get defaults and compute constants
        chart_data = self.header.chart
        node_size = chart_data.nodeSize
        node_spacing = chart_data.nodeSpacing
        node_slope = chart_data.nodeSlope

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
                self.nodes[node_id]._absoluteX = x + offset * math.cos(theta)
                self.nodes[node_id]._absoluteY = y + offset * math.sin(theta)

    def generate_nodes_svg(self):
        """Generate an SVG <g> element containing all nodes."""

        scale = self.header.chart.scale
        nodes_svg = '<g id="nodes-group">\n'

        for node_id, node in self.nodes.items():
            cx = node._absoluteX * scale
            cy = node._absoluteY * scale

            attributes = node.attributes
            style, aliases = style_and_aliases_from_attributes(attributes)
            style = style.generate(indent=0).replace("\n", " ").strip(" {}")
            if style:
                style = f'style="{style}"'
            aliases = " ".join(aliases)

            label = node.label

            nodes_svg += f'<circle id="{node_id}" class="defaultNode {aliases}" cx="{cx}" cy="{cy}" {style} data-label="{label}"></circle>\n'

        nodes_svg += "</g>\n"
        return nodes_svg

    def generate_edges_svg(self):
        """Generate an SVG <g> element containing all edges."""

        scale = self.header.chart.scale
        edges_svg = '<g id="edges-group">\n'

        for edge in self.edges:
            source = self.nodes[edge.source]
            if edge.target is not None:
                target = self.nodes[edge.target]
                target_x = target._absoluteX * scale
                target_y = target._absoluteY * scale
            elif edge.offset is not None:
                target_x = (source._absoluteX + edge.offset.x) * scale
                target_y = (source._absoluteY + edge.offset.y) * scale
            else:
                # Impossible due to schema
                raise NotImplementedError

            x1 = source._absoluteX * scale
            y1 = source._absoluteY * scale

            attributes = edge.attributes
            style, aliases = style_and_aliases_from_attributes(attributes)
            style = style.generate(indent=0).replace("\n", " ").strip(" {}")
            aliases = " ".join(aliases)

            if edge.bezier is not None:
                control_points = edge.bezier
                if len(control_points) == 1:
                    control_x = control_points[0].x * scale + x1
                    control_y = control_points[0].y * scale + y1
                    curve_d = f"Q {control_x} {control_y} {target_x} {target_y}"
                elif len(control_points) == 2:
                    control0_x = control_points[0].x * scale + x1
                    control0_y = control_points[0].y * scale + y1
                    control1_x = control_points[1].x * scale + target_x
                    control1_y = control_points[1].y * scale + target_y
                    curve_d = f"C {control0_x} {control0_y} {control1_x} {control1_y} {target_x} {target_y}"
                else:
                    # Impossible due to schema
                    raise NotImplementedError
                edge_svg = f'<path d="M {x1} {y1} {curve_d}" class="{aliases}" style="fill: none;{style}"></path>\n'
            else:
                edge_svg = f'<line x1="{x1}" y1="{y1}" x2="{target_x}" y2="{target_y}" class="defaultEdge {aliases}" style="{style}"></line>\n'

            # Remove empty style attribute for cleaner output. This is not strictly necessary, but it
            # makes me feel better.
            edges_svg += edge_svg.replace(' style=""', "")

        edges_svg += "</g>\n"
        return edges_svg

    def generate_svg(self):
        # First make sure that the absolute positions are calculated
        self.calculate_absolute_positions()
        # We generate nodes after edges so that they are drawn on top
        return self.generate_edges_svg() + self.generate_nodes_svg()

    def generate_html(self):
        # Generate CSS styles to be placed in <head>
        self.generate_css_styles()
        # Calculate chart dimensions
        self.compute_chart_dimensions()
        # Generate SVG content
        static_svg_content = self.generate_svg()

        template = load_template()
        html_output = template.render(
            chart=self.header.chart,
            metadata=self.header.metadata,
            css_styles=self._chart_css.generate(),
            static_svg_content=static_svg_content,
        )
        return html_output

    def generate_css_styles(self):
        """Generate `self.chart_css` from the data in "header/aliases" """

        chart_css = CssStyle()

        color_aliases = self.header.aliases.colors.model_dump()
        attribute_aliases = self.header.aliases.attributes.merge_with_defaults()

        # Generate CSS classes for color aliases. We do it first because we may need to reference them
        # in the attribute aliases.
        for color_name, color_value in color_aliases.items():
            chart_css += {
                css_class_name(color_name): {"fill": color_value, "stroke": color_value}
            }

        # Save color aliases as CSS variables for use in the rest of the CSS
        chart_css += {
            ":root": {
                f"--{color_name}": color_value
                for color_name, color_value in color_aliases.items()
            }
        }

        # Generate CSS class for nodes to set the appropriate size
        node_size = self.header.chart.nodeSize
        chart_css += {
            "circle": {"stroke-width": 0, "r": f"calc({node_size} * var(--spacing))"}
        }

        # Generate CSS classes for attribute aliases
        for alias_name, attributes_list in attribute_aliases.items():
            style, aliases = style_and_aliases_from_attributes(attributes_list)

            style = copy.deepcopy(style)
            for alias in aliases:
                style.append(chart_css[css_class_name(alias)])

            for property in ["fill", "stroke"]:
                if property in style.keys() and style[property] in color_aliases:
                    # This is a color alias, so we need to use the CSS variable instead
                    style += {property: f"var(--{style[property]})"}

            chart_css += {css_class_name(alias_name): style}

        self._chart_css = chart_css


def process_json(input_file, output_file):
    # Load input JSON
    with open(input_file, "r") as f:
        chart_spec = json.load(f)

    chart = Chart(chart_spec)

    # Generate HTML
    html_content = chart.generate_html()

    # Write to output file
    with open(output_file, "w") as f:
        f.write(html_content)

    print(f"Generated {output_file} successfully.")


def main():
    if len(sys.argv) != 3:
        print("Usage: seqsee <input.json> <output.html>")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]

    process_json(input_file, output_file)


if __name__ == "__main__":
    main()
