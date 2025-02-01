from airflow import DAG
from airflow.providers.http.operators.http import SimpleHttpOperator
from airflow.decorators import task
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.utils.dates import days_ago
import json


#Generate the dag

with DAG(
    dag_id='apod_postgres_etl_dag',
    start_date=days_ago(1),
    schedule_interval='@daily',
    catchup=False

)as dag:
    
    # task 1 creating the database using postgres

    @task
    def create_table():
        ##initialize the postgres hook
        postgres_hook=PostgresHook(postgres_conn_id='my_postgres_connection')

        ##give the sql querry 
        create_table_query="""CREATE TABLE IF NOT EXISTS apod_data(id SERIAL PRIMARY KEY,title VARCHAR(255),explanation TEXT,url TEXT,date DATE,media_type VARCHAR(50));"""

        #execute the table creation query
        postgres_hook.run(create_table_query)

    # task 2 getting the data from the nasa(apod) api 
    # https://api.nasa.gov/planetary/apod?api_key=0B6MbVkkhr4jFLAWzayWBXIcdSubZDNDTkzw7Dai - this is the link we need to map using airflow by astronomer
    extract_apod = SimpleHttpOperator(
        task_id='extract_apod',# name of the task ie the operator reading the api and giving output as the response in form of json
        http_conn_id='nasa_api',#we have to map the nasa apod link ie the official nasa/gov/in link to this nasa_api_place we will be defining this connection id in airflow
        endpoint='planetary/apod',#here we have to paste the endpoint for the nasa api for apod
        method='GET',# we will be getting information and storing it in json format so we will be using get method
        data={'api_key':'{{conn.nasa_api.extra_dejson.api_key}}'},#here we have to get the api key from the connection
        response_filter =lambda response:response.json(),#converting response to json for further transformation and saving it in postgres db
    )




    # task 3 transforming the data into the form we want 


    @task

    def transform_data(response):
        apod_data={
            'title':response.get('title',' '),
            'explanation':response.get('explanation',' '),
            'url':response.get('url',' '),
            'date':response.get('date',' '),
            'media_type':response.get('media_type',' ')
        }
        return apod_data

    # task 4 uploading the data to the database ie postgres sql here

    @task
    def load_data(apod_data):
        #connecting to the postgres server

        postgres_hook_load=PostgresHook(postgres_conn_id='my_postgres_connection')

        #writing the query

        insert_query="""INSERT INTO apod_data(title,explanation,url,date,media_type) VALUES (%s,%s,%s,%s,%s);
        """

        # execute the sql query 

        postgres_hook_load.run(insert_query,parameters=(
            apod_data['title'],
            apod_data['explanation'],
            apod_data['url'],
            apod_data['date'],
            apod_data['media_type']
        ))  




    # task 5 viewing the uploaded data using dbviewer

    # task 6 defining the dependencies

    #Extract
    create_table() >>  extract_apod
    api_response = extract_apod.output
    #Transform
    transformed = transform_data(api_response)
    #Load
    loaded = load_data(transformed)

