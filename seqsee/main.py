import copy
import json
from pathlib import Path
import jsonschema
import math
import sys
import os
import pydantic

from collections import defaultdict
from jinja2 import Environment, FileSystemLoader
from seqsee.chart_internals import (
    Attribute,
    Attributes,
    DimensionRange,
    Edge,
    Header,
    Node,
)
from seqsee.css import CssStyle
from typing import Callable, Dict, List, Optional, Union


def load_schema():
    schema_path = os.path.join(os.path.dirname(__file__), "input_schema.json")
    with open(schema_path, "r") as f:
        schema = json.load(f)
    return schema


schema = load_schema()
chart_schema = schema["$defs"]["chart_spec"]


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
                    else:
                        # Impossible due to schema
                        raise NotImplementedError
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

    model_config = pydantic.ConfigDict(extra="allow")

    def __init__(self, chart_spec):
        # validate against schema
        jsonschema.validate(instance=chart_spec, schema=schema)
        super().__init__(**chart_spec)

    @property
    def css(self):
        """Generate CSS from the data in `header/aliases`"""

        chart_css = CssStyle()

        color_aliases = self.header.aliases.colors.model_dump()
        attribute_aliases = self.header.aliases.attributes.merge_with_defaults()

        # Save color aliases as CSS variables for use in the rest of the CSS
        chart_css += {
            f"--{color_name}": color_value
            for color_name, color_value in color_aliases.items()
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

        return chart_css

    def normalize_chart_dimensions(self):
        """
        This replaces the null values in `self.width` and `self.height` by autodetected boundaries,
        and ensures that the values are even numbers.

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

        # Make sure that the min and max values are even numbers
        self.header.chart.width.make_even()
        self.header.chart.height.make_even()

    def trim_contents(self):
        """Remove all nodes and edges that are not within bounds."""

        # Remove nodes that are not in the chart
        trimmed_nodes = {}
        for node_id, node in self.nodes.items():
            if node.x in self.header.chart.width and node.y in self.header.chart.height:
                trimmed_nodes[node_id] = node
        self.nodes = trimmed_nodes

        trimmed_edges = []
        for edge in self.edges:
            if edge.source in self.nodes:
                target_in_bounds = edge.target in self.nodes
                is_freestanding = edge.target is None
                if is_freestanding or target_in_bounds:
                    trimmed_edges.append(edge)
        self.edges = trimmed_edges

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

    def add_nodes_to_edges(self):
        """
        For each edge, set the `_concrete_source` and `_concrete_target` properties to the actual
        node objects.
        """

        for edge in self.edges:
            assert (
                edge.source in self.nodes
            ), f"Edge {edge} has source {edge.source} that is not in the chart."
            edge._concrete_source = self.nodes[edge.source]

            if edge.target is not None:
                assert (
                    edge.target in self.nodes
                ), f"Edge {edge} has target {edge.target} that is not in the chart."
                edge._concrete_target = self.nodes[edge.target]

    def prepare(self):
        # Trim contents to fit within the chart dimensions
        self.trim_contents()
        # Normalize chart dimensions. We do this after trimming because otherwise we might include
        # too many nodes in the computation.
        self.normalize_chart_dimensions()
        # First make sure that the absolute positions are calculated
        self.calculate_absolute_positions()
        # Then add the node objects to the edges
        self.add_nodes_to_edges()


class Collection(pydantic.BaseModel):
    header: Header = Header()
    charts: List[Union[Chart, str]] = []

    model_config = pydantic.ConfigDict(extra="allow")
    _input_file: Optional[str] = None

    def __init__(self, spec, input_file=None):
        from jsonschema import RefResolver

        # Create a resolver rooted at the full schema
        resolver = RefResolver.from_schema(schema)

        def matches_ref(ref):
            ref_schema = {"$ref": ref}
            validator = jsonschema.Draft7Validator(schema=ref_schema, resolver=resolver)
            return validator.is_valid(spec)

        if matches_ref("#/$defs/collection_spec"):
            # This is a genuine collection
            super().__init__(**spec)
        elif matches_ref("#/$defs/chart_spec"):
            # This is a single chart, so we need to wrap it in a collection
            super().__init__(charts=[Chart(spec)])
        else:
            # Impossible due to schema
            raise NotImplementedError

        self._input_file = input_file

        self._load_charts()

    def __iter__(self):
        return self.charts.__iter__()

    def _load_charts(self):
        """Replace all internal chart references with the actual chart objects."""

        expanded_charts = []
        for chart in self.charts:
            if isinstance(chart, str):
                # This is a reference to another chart
                assert (
                    self._input_file is not None
                ), "Cannot load chart from file without input file"
                chart_path = Path(self._input_file).parent / chart
                with open(chart_path, "r") as f:
                    chart_spec = json.load(f)
                expanded_charts.append(Chart(chart_spec))
            else:
                # This is a Chart object
                expanded_charts.append(chart)
        self.charts = expanded_charts

    def generate_html(self):
        for chart in self:
            chart.prepare()

        template = load_template()
        return template.render(collection=self)


def process_json(input_file, output_file):
    # Load input JSON
    with open(input_file, "r") as f:
        spec = json.load(f)

    chart = Collection(spec, input_file=input_file)

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
