import pandas as pd
import json
import argparse

def parse_excel_to_json(input_file: str) -> str:
    df = pd.read_excel(input_file)
    data = df.to_dict(orient='records')
    return json.dumps(data, indent=4)

def main() -> None:
    parser = argparse.ArgumentParser(description="Parse Excel file and convert to JSON")
    parser.add_argument("input_file", help="Path to the input Excel file")

    args = parser.parse_args()
    input_file = args.input_file

    result = parse_excel_to_json(input_file)
    print(result)

if __name__ == "__main__":
    main()



#     import pandas as pd
# import json
# import argparse

# def parse_excel_to_json(input_file: str) -> str:
#     df = pd.read_excel(input_file)
#     result = {}

#     for _, row in df.iterrows():
#         key = row.get("Unnamed: 0")
#         value = row.get("Unnamed: 6")

#         if pd.notna(key) and pd.notna(value):
#             result[str(key)] = value

#     return json.dumps(result, indent=4)

# def main() -> None:
#     parser = argparse.ArgumentParser(description="Parse Excel file and convert to JSON")
#     parser.add_argument("input_file", help="Path to the input Excel file")

#     args = parser.parse_args()
#     input_file = args.input_file

#     result = parse_excel_to_json(input_file)
#     print(result)

# if __name__ == "__main__":
#     main()