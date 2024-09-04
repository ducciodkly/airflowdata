from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import importlib.util
import os

def load_module(filename):
    path = os.path.join(os.path.dirname(__file__), '..', 'jobs', filename)
    spec = importlib.util.spec_from_file_location(filename[:-3], path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

job1 = load_module('job1_ingest_data.py')
job2 = load_module('job2_extract_data.py')
job3 = load_module('job3_transform_data.py')
job4 = load_module('job4_load_data.py')

default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "start_date": datetime(2024, 8, 28),
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

dag = DAG(
    "country_data_pipeline",
    default_args=default_args,
    description="Pipeline dữ liệu để xử lý thông tin quốc gia",
    schedule_interval="0 8 * * *",
)

t1 = PythonOperator(
    task_id="ingest_data",
    python_callable=job1.main,
    dag=dag,
)

t2 = PythonOperator(
    task_id="extract_data",
    python_callable=job2.main,
    dag=dag,
)

t3 = PythonOperator(
    task_id="transform_data",
    python_callable=job3.main,
    dag=dag,
)

t4 = PythonOperator(
    task_id="load_data",
    python_callable=job4.main,
    dag=dag,
)

t1 >> t2 >> t3 >> t4