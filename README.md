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
  - **`nodes`**: An [attribute list](#attribute-lists) applied to all nodes by default. **Note:**
    Specifying default node size here overrides automatic spacing; node size should generally be set
    in `header/chart/nodeSize` for automatic spacing.
  - **`edges`**: An [attribute list](#attribute-lists) applied to all edges by default.

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
