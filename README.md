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

The HTML files generated by `SeqSee` have a few dependencies and cannot be used offline.
Specifically, they depend on:

- `svg-pan-zoom` 3.6.1 for interactivity.
- `katex` 0.16.2, along with its CSS and `auto-render` extension, for rendering LaTeX in titles and
  labels.
- `hammer` 2.0.8 to handle touch inputs.
- `path-data-polyfill` 1.0.9 to handle curved edges.
- The "Computer Modern" font for the axis labels.

For demonstration purposes, the script `seqsee-convert-all` takes every CSV file in `csv/`, converts
them to JSON using `seqsee-jsonmaker`, and then converts each JSON file in `json/` into an HTML file
using `seqsee`.

## Collections

Spectral sequences consist of multiple pages $E_2$, $E_3$, ..., $E_\infty$. SeqSee supports bundling
these into a single HTML file called a _collection_.

When you open a collection, you'll see an index page with links to all charts. Navigate between
charts using the W/S keys, or press Escape to return to the index. This makes it easy to explore a
spectral sequence across multiple pages.

Examples of collections can be found in `html/Adams-classical.html` and `html/Adams-motivic.html`.

## Controls

- Chart controls
  - `-`: Zoom out
  - `+`: Zoom in
  - `0` or Backspace: Reset view
  - Arrow keys: Pan
  - `c`: Copy current hovertext to clipboard
- Collection controls
  - Esc: Return to index page
  - `w`: Previous chart
  - `s`: Next chart

## Installation

Install SeqSee from PyPI:

```bash
pip install seqsee
```

## Usage

Once installed, you can use the following commands:

- **Generate a Spectral Sequence Chart**:

  ```bash
  seqsee input_file.json output_chart.html
  ```

- **Convert CSV to JSON**: To convert CSV data to a JSON file compatible with SeqSee:

  ```bash
  seqsee-jsonmaker input_file.csv output_file.json
  ```

- **Convert Multiple Files**: For batch conversion or processing:

  ```bash
  seqsee-convert-all
  ```

  This script converts every CSV file in `csv/` to a JSON file in `json/`, then converts every JSON
  file in `json/` to an HTML chart in `html/`.

## Development

For contributors and developers, see [DEVELOPMENT.md](DEVELOPMENT.md) for setup instructions and
development workflows.

## Input Schema

SeqSee accepts JSON input defining either a single chart or a collection of charts:

- **Collections**: Include a [`charts`](#charts) section to bundle multiple charts. The
  [`nodes`](#nodes) and [`edges`](#edges) sections are ignored.
- **Single charts**: Omit the [`charts`](#charts) section. Use [`nodes`](#nodes) and
  [`edges`](#edges) to define chart content.

The [`header`](#header) section configures chart appearance and behavior. All sections are optional.

**Schema validation**: Add `"$schema":
"https://raw.githubusercontent.com/JoeyBF/SeqSee/refs/heads/master/seqsee/input_schema.json"` for
IDE validation support.

### Sections

#### `header`

Contains global settings for chart configuration.

- **`metadata`**: Chart metadata and display information.
  - **`htmltitle`**: Sets the HTML document title (shown in browser tabs). Defaults to an empty
    string.
  - **`displaytitle`**: The title shown in the top-left corner of the chart. LaTeX is automatically
    rendered. For collections, this appears as the chart label on the index page. Defaults to an
    empty string.
  - **`title`**: The main title displayed at the top of collection index pages. LaTeX is
    automatically rendered. Has no effect for standalone charts. Defaults to an empty string.
  - **`id`**: A numerical identifier for the chart. This is typically set to the page number (e.g.,
    `2` for the $E_2$ page). Defaults to `0`.
  - Any other key-value pair is accepted, but will have no effect on the output. This is useful for
    tagging output files, since the JSON format does not allow comments. Potentially useful data
    might include `author`, `date`, `source`, `version`, `description`, etc.

- **`chart`**: Holds configuration for the visuals of the chart.
  - **`width` and `height`**: Objects specifying the chart dimensions. Each has `min` and `max`
    properties, which are either signed integers or `null`. If `null`, an appropriate value is
    computed automatically based on `nodes`. All defaults are `null`.
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
    applied to nodes or edges for consistent styling. We require the attribute names to be [valid
    CSS identifiers][css-identifiers]. Some special aliases are predefined but can be customized:
    - **`grid`**: An attribute list applied to the grid itself. Defaults to `[ {"color": "#ccc",
      "thickness": 0.01} ]`.
    - **`defaultNode`**: An attribute list applied to all nodes. Defaults to `[ {"color": "black"}
      ]`. **Note:** Specifying default node size here overrides automatic spacing; node size should
      generally be set in `header/chart/nodeSize` for automatic spacing.
    - **`defaultEdge`**: An attribute list applied to all edges. Defaults to `[ {"color": "black",
      "thickness": 0.02} ]`.

[css-identifiers]: https://walterebert.com/playground/css/valid-identifiers/

#### `nodes`

Defines individual nodes in the chart. Each node has a unique identifier (the key) and an object
specifying its properties:

- **`x` and `y`**: Integer grid coordinates. Most nodes use these for automatic positioning.
- **`absoluteX` and `absoluteY`**: Precise floating-point coordinates. Use these when you need exact
  positioning and want to override automatic spacing.
- **`position`**: Controls stacking order for nodes at the same grid coordinates. Negative values
  position nodes to the left, positive values to the right. Defaults to `0`.
- **`label`**: LaTeX string displayed in tooltips when hovering over the node.
- **`attributes`**: An [attribute list](#attribute-lists) for custom styling.

**Coordinate system**: Each node requires exactly one X coordinate (`x` or `absoluteX`) and one Y
coordinate (`y` or `absoluteY`).

- **Grid coordinates** (`x`, `y`): Nodes are positioned automatically using the global `nodeSpacing`
  and `nodeSlope` settings, with multiple nodes at the same coordinates arranged according to their
  `position` values.
- **Absolute coordinates** (`absoluteX`, `absoluteY`): Nodes are positioned at exact pixel locations
  (scaled by the chart `scale` factor). If either coordinate is absolute, the node bypasses
  automatic spacing entirely.

#### `edges`

Defines directed or undirected edges between nodes.

- **`source`**: The identifier of the starting node (required).
- **`target`**: The identifier of the ending node. Exactly one of `target` or `offset` is required.
- **`offset`**: Relative positioning from the source node, if `target` is not specified. Used for
  freestanding edges, often styled as arrows, with only one endpoint anchored to a node.
  - **`x`**: Floating point value encoding the X-offset from the source node.
  - **`y`**: Floating point value encoding the Y-offset from the source node.
- **`bezier`**: Specifies the control point(s) for the Bézier curve representing this edge. If
  present, it is an array containing one or two objects with keys `x` and `y`, representing
  coordinates:
  - **1 Object**: A single control point for a quadratic Bézier curve. Coordinates are relative to
    the source node.
  - **2 Objects**: Two control points for a cubic Bézier curve. The first point's coordinates are
    relative to the source node, and the second point's coordinates are relative to the endpoint.
- **`attributes`**: An [attribute list](#attribute-lists) for edge-specific styling. Defaults to
  `[]`.

#### `charts`

Defines a collection of charts to be bundled into a single HTML file. When this section is present,
the `nodes` and `edges` sections are ignored, and each chart in the collection is defined as a
separate object with its own `header`, `nodes`, and `edges` sections.

Each chart in the collection can be either:

- A complete chart specification object with `header`, `nodes`, and `edges` sections
- A string path to a separate JSON file containing a chart specification

Collections are useful for displaying multiple pages of a single spectral sequence or related charts
together. The generated HTML will show an index page with links to all charts, and keyboard
navigation (W/S/Esc) is available.

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

- See `json/curves.json` for an example of how to define curved edges.

- See `json/hidden_nodes.json` for an example of how to define nodes with no radius.

- See `json/dark_theme.json` for an example of a dark themed chart.

- See the rest of the `json/` directory for significantly more involved examples. These have all
  been generated from the files in the `csv/` directory using `seqsee-jsonmaker`, through
  `seqsee-convert-all`.

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
