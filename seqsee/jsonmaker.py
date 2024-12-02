import pandas as pd
import re
import sys
from compact_json import Formatter
from jsonschema import validate
from seqsee import load_schema

# Regular expressions for substitutions
substitutions = [
    # Matches any string starting with an underscore, and surrounds it in \overline{}
    (re.compile(r"^_(.*)$"), r"\\overline{\1}"),
    # Matches the dot operator, which is rendered as a centered dot in LaTeX
    (re.compile(r"\."), r"\\cdot"),
    # Matches the string "DD" and replaces it with "{D}". This is necessary if we want to handle
    # both "DD" -> "D" and "D" -> "\Delta".
    (re.compile(r"DD"), r"{D}"),
    # Matches the string "D" and replaces it with "\Delta", but only if it is not surrounded by
    # curly braces. The `(?<!...)` and `(?!...)` expressions are negative lookbehind and negative
    # lookahead, respectively. They ensure that whatever we are matching is in the right "context",
    # i.e. in this case not being in square brackets, but without including that context in the
    # match. This is necessary to avoid replacing the "D" in "{D}".
    (re.compile(r"(?<!{)D(?!})"), r"\\Delta"),
    # Matches the word "t" and replaces it with "\tau". This 't' character needs to be surrounded by
    # either the beginning or end of the line, or a non-word character (something that matches
    # `\W`).
    (re.compile(r"\bt\b"), r"\\tau"),
    # Matches word expressions starting with a non-empty string of latin letters and curly braces
    # (group 1) and ending with a non-empty string of numbers or commas (,) (group 2). We insert an
    # underscore between the two groups and wrap the second one in curly braces. This ensures that
    # subscripts are correctly rendered in LaTeX. NB: Caret (^) is a word separator.
    (re.compile(r"\b([a-zA-Z{}]+)([\d,]+)\b"), r"\1_{\2}"),
    # Matches terms of the form '(letters or curly braces)^(numbers)', and wraps the second group in
    # curly braces. This ensures that superscripts are correctly rendered in LaTeX.
    (re.compile(r"\b([a-zA-Z{}]+)\^(\d+)\b"), r"\1^{\2}"),
]

# Regular expression for detecting "again" suffixes. We strip anything that is whitespace followed
# by any number of non-word characters, then the word "again", and then anything else until the end
# of the line.
detect_again = re.compile(r"\s\W*again.*")

arrow_length = 0.7


def try_get_key(row, key, default=None):
    """
    Get a key from a row.

    Return a default value if the key is not present or the value is `nan`.
    """

    try:
        if pd.isna(row[key]):
            return default
        return row[key]
    except KeyError:
        return default


def edge_offset(edge_type, arrow_length=1):
    if edge_type == "h0":
        offset = {"x": 0, "y": 1}
    elif edge_type == "h1":
        offset = {"x": 1, "y": 1}
    elif edge_type == "h2":
        offset = {"x": 3, "y": 1}
    elif edge_type == "dr":
        offset = {"x": -1, "y": 2}
    else:
        raise ValueError
    for key in offset:
        offset[key] *= arrow_length
    return offset


def extract_node_attributes(row):
    ret = []
    if row.get("tautorsion", []):
        torsion = int(row["tautorsion"])
        if torsion >= 4:
            ret.append("tau4plus")
        elif torsion > 0:
            ret.append(f"tau{torsion}")
    return ret


def extract_edge_attributes(row, edge_type, nodes):
    ret = []
    target_node = row[f"{edge_type}target"]
    # Info fields are sometimes missing, so we default to an empty string
    target_info = try_get_key(row, f"{edge_type}info")
    if edge_type == "dr":
        ret.append("dr")
    elif target_node in nodes:
        # Edges into a node inherit the attributes of their target, as long as they aren't
        # differentials
        target_node_attributes = try_get_key(
            nodes.get(target_node, {}), "attributes", default=[]
        )
        ret.extend(target_node_attributes)
    if target_node == "loc" or target_info == "loc":
        # This edge is an arrow
        if edge_type == "h1":
            # We treat h1 towers differently because they are also always red
            ret.append("h1tower")
        else:
            ret.append({"arrowTip": "simple"})
    if target_info:
        # The info field has other instructions for the edge. We treat them as aliases and let
        # SeqSee handle them. The only exception is "h", which we need to tag with "edge_type" so
        # the correct alias is applied.
        if isinstance(target_info, float):
            target_info = str(int(target_info))
        extra_attributes = target_info.split(" ")
        if "h" in extra_attributes:
            extra_attributes.remove("h")
            extra_attributes.append(f"h{edge_type}")
        ret.extend(extra_attributes)

    return ret


def label_from_node_name(node_name):
    """Apply substitutions to a node name to generate a label, wrapped in dollar signs for Latex."""
    label = node_name
    for pattern, replacement in substitutions:
        label = pattern.sub(replacement, label)
    if label:
        label = f"${label}$"
    return label


def deduplicate_name(name):
    """Deduplicate names by removing all variations of 'again'. We also return whether the name was
    a duplicate."""
    # I suggest we change the csv format to remove the "again" suffixes, and instead have a
    # semicolon-separated list of names for the targets of the edges. However, the input is
    # from a legacy dataset, so I don't have control over that.

    # First strip outer opening and closing parentheses if both are present. This makes it possible
    # for the regex to only match suffixes, while not affecting the rest of the name.
    if name.startswith("(") and name.endswith(")"):
        name = name[1:-1]
    if detect_again.search(name):
        return (detect_again.sub("", name), True)
    return (name, False)


def nodes_to_json(df):
    nodes = {}
    for _, row in df.iterrows():
        # Process node information

        node_name, is_duplicate = deduplicate_name(row["name"])
        if is_duplicate:
            continue

        x = int(row["stem"])
        y = int(row["Adams filtration"])
        node_data = {
            "x": x,
            "y": y,
            "label": label_from_node_name(node_name),
        }
        if try_get_key(row, "weight", None):
            node_data["label"] += f"    ({row['weight']})"
        if try_get_key(row, "shift", None):
            node_data["position"] = row["shift"]
        if attributes := extract_node_attributes(row):
            # Only add an attributes key if there are attributes to add
            node_data["attributes"] = attributes
        nodes[node_name] = node_data
    return nodes


def edges_to_json(df, nodes):
    edges = []
    for _, row in df.iterrows():
        node_name, _ = deduplicate_name(row["name"])
        for edge_type in ["h0", "h1", "h2", "dr"]:
            target_col = f"{edge_type}target"
            info_col = f"{edge_type}info"
            if target_col not in row:
                # In some CSVs, the target column is missing completely
                continue
            target_node = row[target_col]
            target_info = try_get_key(row, info_col, "")
            edge_data = {"source": node_name}
            if pd.notna(target_node):
                if target_node in nodes:
                    # This is a structline
                    edge_data["target"] = target_node
                elif target_node == "loc" or target_info == "loc":
                    # This is an arrow
                    edge_data["offset"] = edge_offset(edge_type, arrow_length)
                else:
                    print(
                        f"Invalid target node: ({target_node}) for {edge_type} on ({node_name})"
                    )
                    continue
            elif target_info == "free" or target_info == "loc":
                # This is also an arrow, but with a different notation
                edge_data["offset"] = edge_offset(edge_type, arrow_length)
            else:
                # no edge to be drawn
                continue

            if attributes := extract_edge_attributes(row, edge_type, nodes=nodes):
                # Only add an attributes key if there are attributes to add
                edge_data["attributes"] = attributes

            edges.append(edge_data)
        # Check for `tauextn` if we're printing an E_infinity page
        if target_node := try_get_key(row, "tauextn"):
            if target_node in nodes:
                edges.append(
                    {
                        "source": node_name,
                        "target": target_node,
                        "attributes": ["tauextn"],
                    }
                )
    return edges


def process_csv(input_file, output_file):
    # Define the JSON schema
    schema = load_schema()

    # Load CSV data
    df = pd.read_csv(input_file)

    # Build a header that complies with the schema
    header = {
        "defaultAttributes": {
            "nodes": [{"color": "gray"}],
            "edges": [{"color": "gray", "thickness": 0.02, "pattern": "solid"}],
        },
        "aliases": {
            "attributes": {
                "tau1": [{"color": "red"}],
                "tau2": [{"color": "blue"}],
                "tau3": [{"color": "darkgreen"}],
                "tau4plus": [{"color": "purple"}],
                "dr": [{"color": "darkcyan"}],
                "2": [{"color": "darkcyan"}],
                "3": [{"color": "red"}],
                "4": [{"color": "darkgreen"}],
                "5": [{"color": "blue"}],
                "6": [{"color": "orange"}],
                "7": [{"color": "orange"}],
                "8": [{"color": "orange"}],
                "9": [{"color": "orange"}],
                "10": [{"color": "orange"}],
                "11": [{"color": "orange"}],
                "t": [{"color": "magenta"}],
                "t2": [{"color": "orange"}],
                "t3": [{"color": "orange"}],
                "t4": [{"color": "orange"}],
                "t5": [{"color": "orange"}],
                "t6": [{"color": "orange"}],
                "p": [{"pattern": "dashed"}],
                "hh0": [{"color": "red"}],
                "hh1": [{"color": "blue"}],
                "hh2": [{"color": "darkgreen"}],
                "tauextn": [{"color": "darkgreen"}],
                "free": [{"arrowTip": "simple"}],
                "h1tower": ["tau1", {"arrowTip": "simple"}],
            },
            "colors": {
                "darkcyan": "#00B3B3",
                "darkgreen": "#00B300",
                "gray": "#666666",
                "red": "#FF0000",
                "magenta": "#FF00FF",
            },
        },
    }

    # Process nodes first
    nodes = nodes_to_json(df)

    # Process edges after, since they depend on nodes
    edges = edges_to_json(df, nodes)

    # Combine the data into a single JSON object
    json_data = {"header": header, "nodes": nodes, "edges": edges}

    # Validation and output
    try:
        validate(instance=json_data, schema=schema)
        formatter = Formatter()
        formatter.indent_spaces = 2
        formatter.dump(json_data, output_file)
        print("JSON data successfully generated and validated against the schema.")
    except Exception as e:
        print("Validation error:", e)


def main():
    if len(sys.argv) != 3:
        print("Usage: jsonmaker <input.csv> <output.json>")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]

    process_csv(input_file, output_file)


if __name__ == "__main__":
    main()
