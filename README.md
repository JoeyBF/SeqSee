# SeqSee

`SeqSee` (pronounced "seek-see") is a generic visualization tool for spectral sequence data. It aims
to decouple the challenge of working with spectral sequences mathematically from the challenge of
displaying them graphically. We present a [JSON schema](#input-schema) that can serve as a lingua
franca between these two aspects.

By way of example, we have included a tool called `jsonmaker`, which can convert the CSV files found
[here](https://zenodo.org/records/6987157) and [here](https://zenodo.org/records/6987227) into JSON
files following our schema. This script is specific to the format of those CSV files, but serves as
a template for creating tools to generate JSON data that `SeqSee` can display. It is expected that
any software that outputs spectral sequence data will require a customized tool to produce JSON
files that follow the SeqSee schema.

`SeqSee` takes a JSON file as input, conforming to the SeqSee schema, and outputs a self-contained
HTML file. This file includes an SVG figure representing the spectral sequence along with JavaScript
for interactivity.

The HTML files generated by `SeqSee` have a few dependencies and cannot be used offline. However,
these dependencies are small and are likely to be cached after the file is opened for the first
time. Specifically, they depend on:

- `svg-pan-zoom` 3.6.1 for interactivity.
- `katex` 0.16.2, along with its CSS and `auto-render` extension, for rendering LaTeX in titles and
  labels.
- `hammer` 2.0.8 to handle touch inputs.
- `path-data-polyfill` 1.0.9 to handle curved edges.
- The "Computer Modern" font for the axis labels.

For demonstration purposes, the script `convert_all` takes every CSV file in `csv/`, converts them
to JSON using `jsonmaker`, and then converts each JSON file in `json/` into an HTML file using
`SeqSee`.

## Controls

- `-` key: Zoom out
- `+` key: Zoom in
- `0` key or `backspace`: Reset view

## Running SeqSee

`SeqSee` is packaged with Poetry for easy dependency management and script execution. Below are the
instructions for setting up and running `SeqSee`.

### Prerequisites

Ensure you have the following installed:

- **Python** 3.11+
- **Poetry** for dependency management

### Installation

1. **Clone the Repository:**

   ```bash
   git clone git@github.com:JoeyBF/SeqSee.git
   cd SeqSee
   ```

2. **Initialize the Environment:** Install the scripts using Poetry:

   ```bash
   poetry shell
   poetry install
   ```

### Usage

Once set up, you can use the following commands:

- **Generate a Spectral Sequence Chart**:

  ```bash
  seqsee input_file.json output_chart.html
  ```

- **Convert CSV to JSON**: To convert the CSV data in `csv/` to a JSON file compatible with
  `SeqSee`, use:

  ```bash
  jsonmaker input_file.csv output_file.json
  ```

- **Convert Multiple Files**: For batch conversion or processing:

  ```bash
  convert_all
  ```

  This script converts every CSV file in `csv/` to a JSON file in `json/`, then converts every JSON
  file in `json/` to an HTML chart in `html/`.

These commands are registered as Poetry scripts, so they can be run directly after activating the
environment with `poetry shell`.

## Input Schema

The input JSON file contains three primary sections: `header`, `nodes`, and `edges`. Each section
defines configuration options for generating a spectral sequence chart, and any section can be
omitted.

To validate the JSON file against the SeqSee schema in compatible IDEs, add `"$schema":
"https://raw.githubusercontent.com/JoeyBF/SeqSee/refs/heads/master/seqsee/input_schema.json"` at the
top level.

### Sections

#### `header`

Contains global settings for chart configuration.

- **`metadata`**: Holds metadata about the chart.
  - **`htmltitle`**: The `<title>` of the HTML output. Defaults to an empty string.
  - Any other key-value pair is accepted, but will have no effect on the output. This is useful for
    tagging output files, since the JSON format does not allow comments. Potentially useful data
    might include `author`, `date`, `source`, `version`, `description`, etc.

- **`chart`**: Holds configuration for the visuals of the chart.
  - **`width` and `height`**: Objects specifying the chart dimensions. Each has `min` and `max`
    properties, which are either signed integers or `null`. If `null`, an appropriate value is computed
    automatically based on `nodes`. All defaults are `null`.
  - **`scale`**: A number representing the grid scale in pixels. Each unit increase along the axes
    corresponds to this many pixels. Defaults to `60`.
  - **`nodeSize`**: Defines the radius of nodes as a multiple of `scale`. Defaults to `0.04`.
  - **`nodeSpacing`**: Specifies the distance between nodes in the same bidegree, measured between
    their circumferences. Defaults to `0.02`.
  - **`nodeSlope`**: The slope of the line along which nodes are positioned:
    - `0`: Horizontal alignment
    - `null`: Vertical alignment
    - Any floating point value is accepted. Defaults to `0`.

- **`aliases`**: Allows shorthand for reusable colors and attributes.
  - **`colors`**: Maps color names to valid CSS color values. Some special colors are predefined but
    can be customized:
    - **`backgroundColor`**: The background color of the chart. Defaults to `"white"`.
    - **`borderColor`**: The color of the chart and tooltip borders. Defaults to `"black"`.
    - **`textColor`**: The color of text and labels. Defaults to `"black"`.
  - **`attributes`**: Maps names to predefined [attribute lists](#attribute-lists), which can be
    applied to nodes or edges for consistent styling. Some special aliases are predefined but can be
    customized:
    - **`grid`**: An attribute list applied to the grid itself. Defaults to `[ {"color": "#ccc",
      "thickness": 0.01} ]`.
    - **`defaultNode`**: An attribute list applied to all nodes. Defaults to `[ {"color": "black"}
      ]`. **Note:** Specifying default node size here overrides automatic spacing; node size should
      generally be set in `header/chart/nodeSize` for automatic spacing.
    - **`defaultEdge`**: An attribute list applied to all edges. Defaults to `[ {"color": "black",
      "thickness": 0.02} ]`.

#### `nodes`

Defines individual nodes in the chart. Each key is a unique node identifier mapping to an object
with the following properties:

- **`x`**: X-coordinate (required). Must be an integer.
- **`y`**: Y-coordinate (required). Must be an integer.
- **`position`**: An integer representing the index position within a bidegree. Negative values are
  positioned further left, and positive values are positioned further right. Ties are broken by the
  order in which the nodes occur in the input JSON. Defaults to `0`.
- **`label`**: A LaTeX string for the node label, displayed in a tooltip on hover.
- **`attributes`**: An [attribute list](#attribute-lists) for node-specific styling.

#### `edges`

Defines directed or undirected edges between nodes.

- **`source`**: The identifier of the starting node (required).
- **`target`**: The identifier of the ending node. Exactly one of `target` or `offset` is required.
- **`offset`**: Relative positioning from the source node, if `target` is not specified. Used for
  freestanding edges, often styled as arrows, with only one endpoint anchored to a node.
  - **`x`**: Floating point value encoding the X-offset from the source node.
  - **`y`**: Floating point value encoding the Y-offset from the source node.
- **`bezier`**: Specifies the control point(s) for the Bézier curve representing this edge. If
  present, it is an array containing one or two objects with keys `"x"` and `"y"`, representing
  coordinates:
  - **Length 1**: A single control point for a quadratic Bézier curve. Coordinates are relative to
    the source node.
  - **Length 2**: Two control points for a cubic Bézier curve. The first point's coordinates are
    relative to the source node, and the second point's coordinates are relative to the endpoint.
- **`attributes`**: An [attribute list](#attribute-lists) for edge-specific styling.

#### Attribute Lists

Attribute lists are arrays of styling properties defining the visual characteristics of nodes and
edges. Each entry is a string (aliasing an attribute list) or an object with the following
properties:

- **`color`**: A string representing the color. Accepts any CSS color value or a predefined color
  from `header/aliases/colors`.
- **`size`**: Specifies the element's size as a multiple of the chart scale. Applies to nodes
  (radius).
- **`thickness`**: Specifies thickness as a multiple of the chart scale. Applies mainly to edges;
  for nodes, it sets the circle border thickness (typically kept at 0 to maintain proper spacing).
- **`arrowTip`**: Defines the arrow tip type on an edge. Valid values are `"none"` (no arrow head)
  or `"simple"` (simple arrow head).
- **`pattern`**: Specifies the line pattern for edges. Valid values are `"solid"`, `"dashed"`, or
  `"dotted"`.
- Any other property is treated as raw CSS.

Strings in an attribute list reference their own attribute list in `header/aliases/attributes`. When
multiple properties are specified, directly specified properties take precedence. If conflicts
remain, later entries in the list override previous ones.

## Examples

- An empty chart:

  ```json
  {}
  ```

- A 2x2 chart showing a single black node at the origin, labeled `1`:

  ```json
  {
    "nodes": { "1": {"x": 0, "y": 0, "label": "1"} }
  }
  ```

- The first few stems of the 2-primary $\mathbb{C}$-motivic Adams spectral sequence:

  ```json
  {
    "$schema": "https://raw.githubusercontent.com/JoeyBF/SeqSee/refs/heads/master/seqsee/input_schema.json",
    "header": {
      "metadata": {
        "htmltitle": "First few C-motivic stable stems",
        "title": "First few $\\mathbb{C}$-motivic stable stems",
        "authors": ["Joey Beauvais-Feisthauer", "Daniel C. Isaksen"]
      },
      "aliases": {
        "attributes": {
          "defaultNode": [ {"color": "gray"         } ],
          "defaultEdge": [ {"color": "gray"         } ],
          "tau1"       : [ {"color": "tau1color"    } ],
          "tau1extn"   : [ {"color": "tau1extncolor"} ]
        },
        "colors": {
          "gray"         : "#666"   ,
          "tau1color"    : "#DD0000",
          "tau1extncolor": "magenta"
        }
      }
    },
    "nodes": {
      "1"   : {"x": 0, "y": 0, "label": "$1$ (0)"}                              ,
      "h0"  : {"x": 0, "y": 1, "label": "$h_0$ (0)"}                            ,
      "h0^2": {"x": 0, "y": 2, "label": "$h_0^2$ (0)"}                          ,
      "h0^3": {"x": 0, "y": 3, "label": "$h_0^3$ (0)"}                          ,
      "h1"  : {"x": 1, "y": 1, "label": "$h_1$ (1)"}                            ,
      "h1^2": {"x": 2, "y": 2, "label": "$h_1^2$ (2)"}                          ,
      "h2"  : {"x": 3, "y": 1, "label": "$h_2$ (2)"}                            ,
      "h0h2": {"x": 3, "y": 2, "label": "$h_0 h_2$ (2)"}                        ,
      "h1^3": {"x": 3, "y": 3, "label": "$h_1^3$ (3)"}                          ,
      "h1^4": { "x": 4, "y": 4, "label": "$h_1^4$ (4)", "attributes": ["tau1"] }
    },
    "edges": [
      {"source": "1", "target": "h0"},
      {"source": "1", "target": "h1"},
      {"source": "1", "target": "h2"},
      {"source": "h0", "target": "h0^2"},
      {"source": "h0", "target": "h0h2"},
      {"source": "h0^2", "target": "h0^3"},
      { "source": "h0^2", "target": "h1^3", "attributes": ["tau1extn"] },
      {
        "source": "h0^3",
        "offset": {"x": 0, "y": 0.7},
        "attributes": [ {"arrowTip": "simple"} ]
      },
      {"source": "h1", "target": "h1^2"},
      {"source": "h1^2", "target": "h1^3"},
      {"source": "h2", "target": "h0h2"},
      { "source": "h0h2", "target": "h1^3", "attributes": ["tau1extn"] },
      { "source": "h1^3", "target": "h1^4", "attributes": ["tau1"] },
      {
        "source": "h1^4",
        "offset": {"x": 0.7, "y": 0.7},
        "attributes": [ "tau1", {"arrowTip": "simple"} ]
      }
    ]
  }
  ```

- See `json/example4.json` for an example of how to define curved edges.

- See `json/example5.json` for an example of how to define nodes with no radius.

- See `json/example6.json` for an example of a dark themed chart.

- See the rest of the `json/` directory for significantly more involved examples. These have all
  been generated from the files in the `csv/` directory using `jsonmaker`, through `convert_all`.

## Future Development

`SeqSee` is designed with flexibility in mind, making it straightforward to extend its capabilities.
Potential areas for development include:

- **Customizable Styles**: Add support for more node and edge styles, shadow effects, or different
  node shapes.
- **Advanced Interactivity**: Implement features like node/edge selection, more hover effects, and
  dynamic highlighting.
- **Improved Coordinate Systems**: Allow more customization of axes, gridlines, and coordinates for
  specialized use cases.
- **Enhanced Output Formats**: Support additional export formats, such as PDFs, Tikz figures, or raw
  SVG files for presentations and publications.

Contributions to the `SeqSee` project are welcome! Please open issues or submit pull requests for
new features or bug fixes.
