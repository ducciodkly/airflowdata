# Build a data pipeline using airflow: run 4 python jobs sequentially, Runs daily at 8am
1. Job 1 (ingest data): Get data from this api and save it to a folder called raw https://restcountries.com/v3.1/all
2. Job 2 (Extract): Convert data at raw folder from semi-structured to structured and save it to a folder called foundation
3. Job 3 (Transform): rename columns to Vietnamese and get the necessary columns (name,ccn3,cca3,independent,status,capital,altSpellings,region,area,maps,timezones,continents,flags,startOfWeek). Save structured data to 2 trusted folder (trusted/countries and trusted/country_currency)
- capital, altSpellings: concatenate all values ​​separated by "|"
- change latlng column to kinh_do and vi_do
- create new su_dung_tieng_anh (bool)
- convert all translations values ​​to columns (note these columns do not need to be converted to Vietnamese)
- maps: only get googleMaps
- timezones: get first
- flags: only get svg
- create new quoc_gia_id column = hash(name.common + name.official) -namespace to hash = "9a5963f8-5a5c-4b8c-aa46-1068af074546" using uuid4
- currencies: separate dataframe 
4. Job 4 (Load): save to mysql local 3 tables (countries, country_currency, currencies)
