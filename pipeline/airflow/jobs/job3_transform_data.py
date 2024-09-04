import os
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import uuid
import hashlib
from airflow.models import Variable

def get_file_path(filename):
    return os.path.join(Variable.get("data_directory", "/opt/airflow"), filename)

def main():
    df = pd.read_csv(get_file_path("foundation/countries_data.csv"), dtype=str)

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
    print("Data transformed successfully.")

if __name__ == "__main__":
    main()