import os
import pyarrow.parquet as pq
from sqlalchemy import create_engine
from airflow.models import Variable

def get_file_path(filename):
    return os.path.join(Variable.get("data_directory", "/opt/airflow"), filename)
def main():

    db_config = {
        "host": Variable.get("db_host", "host.docker.internal"),
        "port": int(Variable.get("db_port", 3306)),
        "user": Variable.get("db_user", "root"),
        "password": Variable.get("db_password", "0358071492"),
        "database": Variable.get("db_name", "airflow"),
    }

    engine = create_engine(
        f"mysql+mysqlconnector://{db_config['user']}:{db_config['password']}@{db_config['host']}:{db_config['port']}/{db_config['database']}"
    )

    trusted_dir = get_file_path("trusted")

    df_countries = pq.read_table(os.path.join(trusted_dir, "countries/countries.parquet")).to_pandas()
    df_countries.to_sql("countries", engine, if_exists="replace", index=False)

    df_country_currency = pq.read_table(os.path.join(trusted_dir, "country_currency/country_currency.parquet")).to_pandas()
    df_country_currency.to_sql("country_currency", engine, if_exists="replace", index=False)

    df_currencies = df_country_currency[["currency_code", "currency_name", "currency_symbol"]].drop_duplicates()
    df_currencies.to_sql("currencies", engine, if_exists="replace", index=False)

    print("Data loaded into MySQL successfully.")

if __name__ == "__main__":
    main()