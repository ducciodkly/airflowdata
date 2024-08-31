from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import requests
import json
import os
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import uuid
import hashlib
from sqlalchemy import create_engine

default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "start_date": datetime(2024, 8, 28),
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

# Create DAG
dag = DAG(
    "country_data_pipeline",
    default_args=default_args,
    description="Pipeline dữ liệu để xử lý thông tin quốc gia",
    schedule_interval="0 8 * * *",
)


# Job 1: Ingest Data
def ingest_data():
    url = "https://restcountries.com/v3.1/all"
    response = requests.get(url)
    data = response.json()

    if not os.path.exists("/opt/airflow/raw"):
        os.makedirs("/opt/airflow/raw")

    with open("/opt/airflow/raw/countries_data.json", "w") as f:
        json.dump(data, f)


# Job 2: Extract Data
def extract_data():
    with open("/opt/airflow/raw/countries_data.json", "r") as f:
        data = json.load(f)

    df = pd.json_normalize(data)

    if not os.path.exists("/opt/airflow/foundation"):
        os.makedirs("/opt/airflow/foundation")

    df.to_csv("/opt/airflow/foundation/countries_data.csv", index=False)


# Job 3: Transform Data
def transform_data():
    df = pd.read_csv("/opt/airflow/foundation/countries_data.csv", dtype=str)

    column_mapping = {
        "name.common": "ten",
        "ccn3": "ma_so_quoc_gia",
        "cca3": "ma_quoc_gia_3_chu_cai",
        "independent": "doc_lap",
        "status": "trang_thai",
        "region": "khu_vuc",
        "area": "dien_tich",
        # maps: only get googleMaps
        "maps.googleMaps": "ban_do",
        "continents": "chau_luc",
        "flags.svg": "co",
        "startOfWeek": "ngay_bat_dau_tuan",
    }
    df = df.rename(columns=column_mapping)

    # capital, altSpellings: concatenate all values ​​separated by "|"
    df["thu_do"] = df["capital"].apply(
        lambda x: "|".join(eval(x)) if pd.notna(x) else ""
    )
    df["ten_khac"] = df["altSpellings"].apply(
        lambda x: "|".join(eval(x)) if pd.notna(x) else ""
    )

    # change latlng column to kinh_do and vi_do
    df["kinh_do"] = df["latlng"].apply(lambda x: eval(x)[0] if pd.notna(x) else None)
    df["vi_do"] = df["latlng"].apply(lambda x: eval(x)[1] if pd.notna(x) else None)

    # create new su_dung_tieng_anh (bool)
    df["su_dung_tieng_anh"] = df["languages.eng"].notna()

    # timezones: get first
    df["mui_gio"] = df["timezones"].apply(lambda x: eval(x)[0] if pd.notna(x) else "")

    # create new quoc_gia_id column = hash(name.common + name.official) -namespace to hash = "9a5963f8-5a5c-4b8c-aa46-1068af074546" using uuid4
    namespace = uuid.UUID("9a5963f8-5a5c-4b8c-aa46-1068af074546")
    df["quoc_gia_id"] = df.apply(
        lambda row: hashlib.sha256(
            namespace.bytes +
            uuid.uuid4().bytes +
            (row["ten"] + row["name.official"]).encode()
        ).hexdigest(),
        axis=1
    )

    # convert all translations values ​​to columns (note these columns do not need to be converted to Vietnamese)
    translation_columns = [col for col in df.columns if col.startswith("translations.")]
    for col in translation_columns:
        new_col_name = col.replace(".", "_")
        df[new_col_name] = df[col]

    # select necessary column for dataFrame countries
    columns_to_keep = [
        "quoc_gia_id",
        "ten",
        "ma_so_quoc_gia",
        "ma_quoc_gia_3_chu_cai",
        "doc_lap",
        "trang_thai",
        "thu_do",
        "ten_khac",
        "khu_vuc",
        "dien_tich",
        "kinh_do",
        "vi_do",
        "ban_do",
        "mui_gio",
        "chau_luc",
        "co",
        "ngay_bat_dau_tuan",
        "su_dung_tieng_anh",
    ] + [col for col in df.columns if col.startswith("translations_")]

    df_countries = df[columns_to_keep]

    # currencies: separate datafram
    def process_currencies(row):
        currencies = {}
        for col in row.index:
            if col.startswith("currencies.") and pd.notna(row[col]):
                currency_code = col.split(".")[1]
                if currency_code not in currencies:
                    currencies[currency_code] = {}
                if col.endswith(".name"):
                    currencies[currency_code]["name"] = row[col]
                elif col.endswith(".symbol"):
                    currencies[currency_code]["symbol"] = row[col]

        return [
            {
                "quoc_gia_id": row["quoc_gia_id"],
                "currency_code": code,
                "currency_name": info.get("name", ""),
                "currency_symbol": info.get("symbol", ""),
            }
            for code, info in currencies.items()
        ]

    df_currencies = pd.DataFrame(
        [item for items in df.apply(process_currencies, axis=1) for item in items]
    )

    # save data into csv

    df_countries.to_csv("/opt/airflow/trusted/countries/countries.csv", index=False)
    df_currencies.to_csv(
        "/opt/airflow/trusted/country_currency/country_currency.csv", index=False
    )
    # save data into parquet
    table_countries = pa.Table.from_pandas(df_countries)
    pq.write_table(table_countries, "/opt/airflow/trusted/countries/countries.parquet")

    table_currencies = pa.Table.from_pandas(df_currencies)
    pq.write_table(
        table_currencies,
        "/opt/airflow/trusted/country_currency/country_currency.parquet",
    )


# Job 4: Load Data
def load_data():
    db_config = {
        "host": "host.docker.internal",
        "port": 3306,
        "user": "root",
        "password": "0358071492",
        "database": "airflow",
    }

    engine = create_engine(
        f"mysql+mysqlconnector://{db_config['user']}:{db_config['password']}@{db_config['host']}:{db_config['port']}/{db_config['database']}"
    )

    df_countries = pq.read_table(
        "/opt/airflow/trusted/countries/countries.parquet"
    ).to_pandas()
    df_countries.to_sql("countries", engine, if_exists="replace", index=False)

    df_country_currency = pq.read_table(
        "/opt/airflow/trusted/country_currency/country_currency.parquet"
    ).to_pandas()
    df_country_currency.to_sql(
        "country_currency", engine, if_exists="replace", index=False
    )

    df_currencies = df_country_currency[
        ["currency_code", "currency_name", "currency_symbol"]
    ].drop_duplicates()
    df_currencies.to_sql("currencies", engine, if_exists="replace", index=False)

    print("Lưu dữ liệu vào MySQL hoàn tất.")


t1 = PythonOperator(
    task_id="ingest_data",
    python_callable=ingest_data,
    dag=dag,
)

t2 = PythonOperator(
    task_id="extract_data",
    python_callable=extract_data,
    dag=dag,
)

t3 = PythonOperator(
    task_id="transform_data",
    python_callable=transform_data,
    dag=dag,
)

t4 = PythonOperator(
    task_id="load_data",
    python_callable=load_data,
    dag=dag,
)

t1 >> t2 >> t3 >> t4
