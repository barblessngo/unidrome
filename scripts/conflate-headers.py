import json
import csv
import os
from openai import OpenAI
import pandas as pd
import argparse

client = OpenAI()

def determine_longitude_and_latitude(file_path, function):
    return file_path, function

def get_lon_lat_func(file_path, headers, example_data):
    messages = [{"role": "user", "content": "Headers: \n" + ",".join(headers)}]
    tools = [
        {
            "type": "function",
            "function": {
                "name": "write_lamda_function",
                "description": "For the given row of CSV header information and example data, return a lambda function that returns the decimal lon/lat for that row. Use the decimal form if it exists in the header.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "function": {
                            "type": "string",
                            "description": "The lambda function to return a shapely Point object. Expected argument of the function is a row called by pandas viadf.apply(). If no lon/lat header is found, return None. Otherwise return a shapely Point object in valid python. Lookup the fields you need from the data that is passed by index (starting at 0), not name. Should always start with 'lambda row: ... '"
                        }
                    },
                    "required": ["function"],
                },
            },
        }
    ]
    
    # Include example data in the user message
    example_data_str = "\n".join([",".join(row) for row in example_data])
    messages[0]["content"] += f"\nExample data:\n{example_data_str}"
    
    print(messages[0]["content"])
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        tools=tools,
        tool_choice={"type": "function", "function": {"name": "write_lamda_function"}}
    )
    
    tool_call = response.choices[0].message.tool_calls[0]
    function_args = json.loads(tool_call.function.arguments)
    return determine_longitude_and_latitude(file_path, function_args["function"])

root_directory = 'data'
lon_lat_lookup = {}

try:
    from lon_lat_lookup_gen import lon_lat_lookup as lll
except ImportError:
    lll = {}

from lon_lat_lookup_gen import lon_lat_lookup as lll
parser = argparse.ArgumentParser(description="Process a CSV file to group redundant fields.")
parser.add_argument('filename', type=str, help='The CSV file to process')
args = parser.parse_args()

df = pd.read_csv(args.filename)
original_headers = df.columns.tolist()
example_data = df.head(5)
file, func = get_lon_lat_func(args.filename, headers, example_data)

#output_file_path = "scripts/lon_lat_lookup_gen.py"
#with open(output_file_path, "w") as file:
#    file.write("from shapely.geometry import Point\n")
#    file.write("lon_lat_lookup = {\n")
#    for key, value in lon_lat_lookup.items():
#        file.write(f"    '{key}': {value},\n")
#    file.write("}\n")

