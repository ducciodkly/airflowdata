import requests
import json
import os
from airflow.models import Variable

def get_file_path(filename):
    return os.path.join(Variable.get("data_directory", "/opt/airflow"), filename)

def main():
    url = "https://restcountries.com/v3.1/all"
    response = requests.get(url)
    data = response.json()

    raw_dir = get_file_path("raw")
    os.makedirs(raw_dir, exist_ok=True)

    with open(os.path.join(raw_dir, "countries_data.json"), "w") as f:
        json.dump(data, f)

    print("Data ingested successfully.")

if __name__ == "__main__":
    main()