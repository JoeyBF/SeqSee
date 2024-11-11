import json
import pandas as pd
import re
import sys
from .main import load_schema
from collections import defaultdict
from compact_json import Formatter
from jsonschema import validate


# Match the words 'D' and 't', respectively
substitute_Delta = re.compile(r"\bD\b")
substitute_tau = re.compile(r"\bt\b")
# Matches words starting with latin letters (group 1) and
# ending with numbers or a comma (,) (group 2).
# NB: Caret (^) is a word separator.
make_subscript = re.compile(r"\b([a-zA-Z]+)([\d,]+)\b")
# Matches terms of the form '(letters)^(numbers)'
make_exponents = re.compile(r"\b([a-zA-Z]+)\^(\d+)\b")

arrow_length = 0.7


def extract_node_attributes(row):
    ret = []
    if pd.notna(row["tautorsion"]):
        torsion = int(row["tautorsion"])
        if torsion >= 4:
            ret.append("tau4plus")
        elif torsion > 0:
            ret.append(f"tau{torsion}")
    return ret


def extract_edge_attributes(row, edge_type, nodes):
    ret = []
    target_node = row[f"{edge_type}target"]
    target_info = row[f"{edge_type}info"]
    if edge_type == "dr":
        ret.append("dr")
    elif target_node in nodes:
        # Edges into a node inherit the attributes of their target
        target_node_attributes = nodes.get(target_node, {}).get("attributes", [])
        ret.extend(target_node_attributes)
    if target_node == "loc":
        if edge_type == "h1":
            ret.append("h1tower")
        else:
            ret.append({"arrowTip": "simple"})
    if pd.notna(target_info):
        ret.extend(target_info.split(" "))

    return ret


def label_from_node_name(node_name):
    # Regular expressions working their magic:
    label = substitute_Delta.sub(r"\\Delta", node_name)
    label = substitute_tau.sub(r"\\tau", label)
    label = make_subscript.sub(r"\1_{\2}", label)
    label = make_exponents.sub(r"\1^{\2}", label)
    return label


def deduplicate_name(name):
    """Deduplicate names by removing the "again" suffix. We also return whether the name was a
    duplicate."""
    # I suggest we change the csv format to remove the "again" suffixes, and instead have a
    # semicolon-separated list of names for the targets of the edges. However, the input is
    # from a legacy dataset, so I don't have control over that.
    if "again" in name:
        return (name.replace(" again2", "").replace(" again", ""), True)
    return (name, False)


def main():
    if len(sys.argv) != 3:
        print("Usage: jsonmaker <input.csv> <output.json>")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]

    # Define the JSON schema
    schema = load_schema()

    # Load CSV data
    df = pd.read_csv(input_file)

    # Build the JSON object based on the schema
    json_data = {
        "header": {
            "chart": {
                "title": "The $E_2$-page of the motivic Adams spectral sequence",
                "width": 120,
                "height": 60,
            },
            "defaultAttributes": {
                "nodes": [{"color": "gray", "shape": "circle"}],
                "edges": [{"color": "gray", "thickness": "0.02", "lineStyle": "solid"}],
            },
            "aliases": {
                "attributes": {
                    "tau1": [{"color": "red"}],
                    "tau2": [{"color": "blue"}],
                    "tau3": [{"color": "green"}],
                    "tau4plus": [{"color": "purple"}],
                    "dr": [{"color": "darkcyan"}],
                    "t": [{"color": "magenta"}],
                    "t2": [{"color": "orange"}],
                    "t3": [{"color": "orange"}],
                    "t4": [{"color": "orange"}],
                    "t5": [{"color": "orange"}],
                    "t6": [{"color": "orange"}],
                    "p": [{"lineStyle": "dashed"}],
                    "h": [{"lineStyle": "dotted"}],
                    "free": [{"arrowTip": "simple"}],
                    "h1tower": [{"color": "red", "arrowTip": "simple"}],
                },
                "colors": {
                    "darkcyan": "#00B3B3",
                    "gray": "#666666",
                    "red": "#FF0000",
                    "magenta": "#FF00FF",
                },
            },
        },
        "nodes": {},
        "edges": [],
    }

    bidegree_to_rank = defaultdict(int)

    # Process nodes first
    for _, row in df.iterrows():
        # Process node information

        node_name, is_duplicate = deduplicate_name(row["name"])
        if is_duplicate:
            continue

        x = int(row["stem"])
        y = int(row["Adams filtration"])
        bidegree_to_rank[x, y] += 1
        json_data["nodes"][node_name] = {
            "x": x,
            "y": y,
            "position": bidegree_to_rank[x, y] - 1,
            "label": label_from_node_name(node_name),
        }
        if attributes := extract_node_attributes(row):
            # Only add an attributes key if there are attributes to add
            json_data["nodes"][node_name]["attributes"] = attributes

    # Process edges after, since they depend on nodes
    for _, row in df.iterrows():
        node_name, _ = deduplicate_name(row["name"])
        for edge_type in ["h0", "h1", "h2", "dr"]:
            target_col = f"{edge_type}target"
            target_info = f"{edge_type}info"
            target_node = row[target_col]
            edge_data = {
                "source": node_name,
                # We can label edges, but it's not necessary for this example
                # "label": edge_type,
            }
            if pd.notna(target_node):
                if target_node in json_data["nodes"]:
                    # This is a structline
                    edge_data["target"] = target_node
                elif target_node == "loc":
                    # This is an arrow
                    if edge_type == "h0":
                        x_offset = 0 * arrow_length
                        y_offset = 1 * arrow_length
                    elif edge_type == "h1":
                        x_offset = 1 * arrow_length
                        y_offset = 1 * arrow_length
                    else:
                        raise ValueError
                    edge_data["offset"] = {"x": x_offset, "y": y_offset}
                else:
                    print(
                        f"Invalid target node: ({target_node}) for {edge_type} on ({node_name})"
                    )
                    continue
            elif row[target_info] == "free":
                # This is also an arrow, but with a different notation
                if edge_type == "dr":
                    x_offset = -1 * arrow_length
                    y_offset = 2 * arrow_length
                else:
                    raise ValueError
                edge_data["offset"] = {"x": x_offset, "y": y_offset}
            else:
                # no edge to be drawn
                continue

            if attributes := extract_edge_attributes(
                row, edge_type, nodes=json_data["nodes"]
            ):
                # Only add an attributes key if there are attributes to add
                edge_data["attributes"] = attributes

            json_data["edges"].append(edge_data)

    # Validation and output
    try:
        validate(instance=json_data, schema=schema)
        formatter = Formatter()
        formatter.indent_spaces = 2
        formatter.dump(json_data, output_file)
        print("JSON data successfully generated and validated against the schema.")
    except Exception as e:
        print("Validation error:", e)


if __name__ == "__main__":
    main()
