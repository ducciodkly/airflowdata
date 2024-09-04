import json
import os
import pandas as pd
from airflow.models import Variable

def get_file_path(filename):
    return os.path.join(Variable.get("data_directory", "/opt/airflow"), filename)

def main():
    with open(get_file_path("raw/countries_data.json"), "r") as f:
        data = json.load(f)

    df = pd.json_normalize(data)

    foundation_dir = get_file_path("foundation")
    os.makedirs(foundation_dir, exist_ok=True)

    df.to_csv(os.path.join(foundation_dir, "countries_data.csv"), index=False)

    print("Data extracted successfully.")

if __name__ == "__main__":
    main()