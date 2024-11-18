# SeqSee

`SeqSee` (pronounced "seek-see") is a generic visualization tool for spectral sequence data. It
takes a JSON file as input, which conforms to the SeqSee schema, and outputs a self-contained HTML
file. This file includes an SVG figure representing the spectral sequence and JavaScript for
interactivity.

Because the files `SeqSee` generates have a few dependencies, they cannot be used offline. However,
these dependencies are small and likely to be cached after the HTML file is opened for the first
time. Specifically, they depend on:

- `svg-pan-zoom` 3.6.1 for interactivity.
- `katex` 0.16.2, along with its CSS and `auto-render` extension, for rendering LaTeX in titles and
  labels.
- `hammer` 2.0.8 to handle touch inputs.
- The "Computer Modern" font for the title and axis labels.

For convenience, this repository also includes a tool called `jsonmaker`, which can convert CSV
files (such as those found [here](https://zenodo.org/records/6987157) or
[here](https://zenodo.org/records/6987227)) into JSON files following the SeqSee schema.

The script `convert_all` takes every CSV file in `csv/` and converts it to a JSON file using
`jsonmaker`, then converts every JSON file in `json/` to an HTML file using `SeqSee`.

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

- **Convert CSV to JSON**: To convert CSV data to a JSON file compatible with `SeqSee`, use:

  ```bash
  jsonmaker input_file.csv output_file.json
  ```

- **Convert Multiple Files**: For batch conversion or processing:

  ```bash
  convert_all
  ```

  This will convert every CSV file in `csv/` to a JSON file in `json/`, then converts every JSON
  file in `json/` to an HTML chart in `html/`.

These commands are registered as Poetry scripts, so they can be run directly after activating the
environment with `poetry shell`.

## Input Schema

The input JSON file contains three primary sections: `header`, `nodes`, and `edges`. Each section
defines configuration options for generating a spectral sequence chart, and any section can be
omitted.

To validate the JSON file against the SeqSee schema in compatible IDEs, add `"$schema":
"seqsee/input_schema.json"` at the top level.

### Sections

#### `header`

Contains global settings for chart configuration.

- **`chart`**: Holds metadata and configuration for the spectral sequence visualization.
  - **`title`**: A string representing the chart title, allowing LaTeX syntax for mathematical
    expressions. Displayed in the chart's top-left corner and rendered with KaTeX. Also used as the
    HTML page title, with LaTeX markers removed. Defaults to an empty string.
  - **`width`**: The chart width, or `null` for automatic detection based on `nodes`. Defaults to
    `null`.
  - **`height`**: The chart height, or `null` for automatic detection based on `nodes`. Defaults to
    `null`.
  - **`scale`**: A number representing the grid scale in pixels. Each unit increase along the axes
    corresponds to this many pixels. Defaults to `100`.
  - **`nodeSize`**: Defines the radius of nodes as a multiple of `scale`. Defaults to `0.04`.
  - **`nodeSpacing`**: Specifies the distance between nodes in the same bidegree, measured between
    their circumferences. Defaults to `0.02`.
  - **`nodeSlope`**: The slope of the line along which nodes are positioned:
    - `0`: Horizontal alignment
    - `1`: 45° diagonal
    - `-2`: 60° clockwise diagonal
    - `null`: Vertical alignment

- **`defaultAttributes`**: Specifies default visual attributes for nodes and edges.
  - **`nodes`**: An [attribute list](#attribute-lists) applied to all nodes by default. Defaults to
    `[ {"color": "black"} ]` **Note:** Specifying default node size here overrides automatic
    spacing; node size should generally be set in `header/chart/nodeSize` for automatic spacing.
  - **`edges`**: An [attribute list](#attribute-lists) applied to all edges by default. Defaults to
    `[ {"thickness": 0.02, "pattern": "solid"} ]`

- **`aliases`**: Allows shorthand for reusable colors and attributes.
  - **`colors`**: Maps color names to valid CSS color values.
  - **`attributes`**: Maps names to predefined [attribute lists](#attribute-lists), which can be
    applied to nodes or edges for consistent styling.

#### `nodes`

Defines individual nodes in the chart. Each key is a unique node identifier mapping to an object
with the following properties:

- **`x`**: X-coordinate (required).
- **`y`**: Y-coordinate (required).
- **`position`**: An integer representing the index position within a bidegree. Negative values are
  positioned further left, and positive values are positioned further right. Defaults to `0`.
- **`label`**: A LaTeX string for the node label, displayed in a tooltip on hover.
- **`attributes`**: An [attribute list](#attribute-lists) for node-specific styling.

#### `edges`

Defines directed or undirected edges between nodes.

- **`source`**: The identifier of the starting node (required).
- **`target`**: The identifier of the ending node. Exactly one of `target` or `offset` is required.
- **`offset`**: Relative positioning from the source node, if `target` is not specified.
  - **`x`**: X-offset from the source node.
  - **`y`**: Y-offset from the source node.
- **`attributes`**: An [attribute list](#attribute-lists) for edge-specific styling.

#### Attribute Lists

Attribute lists are arrays of styling properties defining the visual characteristics of nodes and
edges. Each entry can be a string (aliasing an attribute list) or an object with the following
properties:

- **`color`**: A string representing the color. Accepts any CSS color value or a predefined color
  from `header/aliases/colors`.
- **`size`**: Specifies the element's size as a multiple of the chart scale. Applies to nodes
  (radius).
- **`thickness`**: Specifies thickness as a multiple of the chart scale. Applies mainly to edges;
  for nodes, it sets circle border thickness (typically kept at 0 to maintain proper spacing).
- **`arrowTip`**: Defines arrow tip type on an edge. Valid values are `"none"` (no arrow head) or
  `"simple"` (simple arrow head).
- **`pattern`**: Specifies the line pattern for edges, with values `"solid"`, `"dashed"`, or
  `"dotted"`.
- Any other property will be treated as raw CSS.

Strings in an attribute list reference their own attribute list in `header/aliases/attributes`. When
multiple properties are specified, directly specified properties take precedence, and if conflicts
remain, later entries in the list override previous ones.

### Examples

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
  "header": {
    "defaultAttributes": {
      "nodes": [ {"color": "gray"                   } ],
      "edges": [ {"color": "gray", "thickness": 0.02} ]
    },
    "aliases": {
      "attributes": {
        "tau1": [ {"color": "tau1color"} ]
      },
      "colors": {
        "gray"     : "#666666",
        "tau1color": "#DD0000",
        "magenta"  : "#FF00FF"
      }
    }
  },
  "nodes": {
    "1"   : { "x": 0, "y": 0                                         },
    "h0"  : { "x": 0, "y": 1, "label": "h_0"                         },
    "h0^2": { "x": 0, "y": 2                                         },
    "h0^3": { "x": 0, "y": 3                                         },
    "h1"  : { "x": 1, "y": 1, "label": "h_1"                         },
    "h1^2": { "x": 2, "y": 2                                         },
    "h2"  : { "x": 3, "y": 1, "label": "h_2"                         },
    "h0h2": { "x": 3, "y": 2                                         },
    "h1^3": { "x": 3, "y": 3                                         },
    "h1^4": { "x": 4, "y": 4,                 "attributes": ["tau1"] }
  },
  "edges": [
    {"source": "1", "target": "h0"},
    {"source": "1", "target": "h1"},
    {"source": "1", "target": "h2"},
    {"source": "h0", "target": "h0^2"},
    {"source": "h0", "target": "h0h2"},
    {"source": "h0^2", "target": "h0^3"},
    {
      "source": "h0^2",
      "target": "h1^3",
      "attributes": [ {"color": "magenta"} ]
    },
    {
      "source": "h0^3",
      "offset": {"x": 0, "y": 0.7},
      "attributes": [ {"arrowTip": "simple"} ]
    },
    {"source": "h1", "target": "h1^2"},
    {"source": "h1^2", "target": "h1^3"},
    {"source": "h2", "target": "h0h2"},
    {
      "source": "h0h2",
      "target": "h1^3",
      "attributes": [ {"color": "magenta"} ]
    },
    { "source": "h1^3", "target": "h1^4", "attributes": ["tau1"] },
    {
      "source": "h1^4",
      "offset": {"x": 0.7, "y": 0.7},
      "attributes": [ "tau1", {"arrowTip": "simple"} ]
    }
  ]
}
```

For significantly more involved examples, see the `json/` directory.
