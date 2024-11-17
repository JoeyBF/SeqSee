import os
from .jsonmaker import process_csv
from .main import process_json


def main():
    # Run process_csv on all files in the csv directory in the poetry project root
    for csv_filename in os.listdir("csv"):
        if csv_filename.endswith(".csv"):
            json_filename = csv_filename.replace(".csv", ".json")
            process_csv("csv/" + csv_filename, "json/" + json_filename)

    # Then process all the json files in the json directory
    for json_filename in os.listdir("json"):
        if json_filename.endswith(".json"):
            html_filename = json_filename.replace(".json", ".html")
            process_json("json/" + json_filename, "html/" + html_filename)


if __name__ == "__main__":
    main()
