import boto3
import csv
import os
import time

class AthenaQueryRunner:
    def __init__(self, database, s3_output):
        self.database = database
        self.s3_output = s3_output
        self.athena = boto3.client('athena')
        self.glue = boto3.client('glue')

    def ensure_database_exists(self):
        """Ensure the Athena database exists, create if it does not."""
        try:
            self.glue.get_database(Name=self.database)
            print(f"Database '{self.database}' already exists.")
        except self.glue.exceptions.EntityNotFoundException:
            print(f"Creating database '{self.database}'...")
            self.glue.create_database(
                DatabaseInput={
                    'Name': self.database,
                    'Description': 'Database for storing Athena tables related to Daylight OSM'
                }
            )
            print(f"Database '{self.database}' created.")

    def run_query(self, query):
        """Submit a query to Athena and return the query execution ID."""
        response = self.athena.start_query_execution(
            QueryString=query,
            QueryExecutionContext={'Database': self.database},
            ResultConfiguration={'OutputLocation': self.s3_output}
        )
        return response['QueryExecutionId']

    def wait_for_query_to_complete(self, query_execution_id, wait_time=5):
        """Wait for the query to complete and handle any failures or cancellations with more details."""
        while True:
            response = self.athena.get_query_execution(QueryExecutionId=query_execution_id)
            state = response['QueryExecution']['Status']['State']

            if state in ['FAILED', 'CANCELLED']:
                reason = response['QueryExecution']['Status'].get('StateChangeReason', 'No specific reason provided.')
                raise Exception(f"Query {state.lower()} due to: {reason}")

            if state == 'SUCCEEDED':
                print("Query completed successfully")
                break

            time.sleep(wait_time)

    def get_query_results(self, query_execution_id):
        """Retrieve and return results from a completed Athena query."""
        results = []
        response = self.athena.get_query_results(QueryExecutionId=query_execution_id)
        for row in response['ResultSet']['Rows']:
            results.append([value.get('VarCharValue', '') for value in row['Data']])
        return results

    def save_results_to_csv(self, results, filepath):
        """Save query results to a CSV file."""
        with open(filepath, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerows(results)

    def create_external_table(self):
        """Create an external table for Daylight OSM features if it does not exist."""
        create_table_query = f"""
        CREATE EXTERNAL TABLE IF NOT EXISTS {self.database} (
          `id` bigint,
          `version` int,
          `changeset` bigint,
          `created_at` timestamp,
          `tags` map<string,string>,
          `wkt` string,
          `min_lon` double,
          `max_lon` double,
          `min_lat` double,
          `max_lat` double,
          `quadkey` string,
          `linear_meters` double
        )
        PARTITIONED BY (
          `release` string,
          `type` string
        )
        ROW FORMAT SERDE 'org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe'
        STORED AS INPUTFORMAT 'org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat'
        OUTPUTFORMAT 'org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat'
        LOCATION 's3://daylight-openstreetmap/parquet/osm_features/'
        """
        print(create_table_query)
        query_execution_id = self.run_query(create_table_query)
        print("Table creation query submitted.")
        self.wait_for_query_to_complete(query_execution_id)

        fsck_query = f"""
        MSCK REPAIR TABLE {self.database}
        """
        print(fsck_query)
        query_execution_id = self.run_query(fsck_query)
        print("Table fsk query submitted.")
        self.wait_for_query_to_complete(query_execution_id)

    def build_top_query(self, top_tags, aeroway_type, release_version):

        columns = []
        for tag in top_tags:
            tag_col = tag.replace(":", "_")
            columns.append(f"json_extract_scalar(CAST(tags AS JSON), '$.{tag}') AS {tag_col}")

        all = ",".join(columns)
        query = f"""
                SELECT
                id,
                ST_X(ST_CENTROID(ST_GEOMETRYFROMTEXT(wkt))) AS lon,
                ST_Y(ST_CENTROID(ST_GEOMETRYFROMTEXT(wkt))) AS lat,
                {all}
                FROM unidrome_daylight
                WHERE tags['aeroway'] = '{aeroway_type}'
                AND release = '{release_version}'
                """
        return query

    def get_top_tags(self, aeroway_type, n):
        query = f"""
            SELECT
                variable,
                COUNT(*) AS variable_count
            FROM (
                SELECT id, t.*
                FROM (
                    SELECT
                        id,
                        tags AS m
                    FROM unidrome_daylight
                    WHERE tags['aeroway'] = '{aeroway_type}'
                    AND release = '{release_version}'
                ) t1
                CROSS JOIN UNNEST(
                    coalesce(map_keys(m), array [ null ]),
                    coalesce(map_values(m), array [ null ])
                ) AS t (variable, value)
            )
            GROUP BY variable
            ORDER BY variable_count DESC
            LIMIT {n};
        """
        query_execution_id = self.run_query(query)
        self.wait_for_query_to_complete(query_execution_id)
        results = self.get_query_results(query_execution_id)
        top_tags = set([])
        for tag, count in results:
            top_tags.add(tag)

        return top_tags

class S3Fetcher:
    @staticmethod
    def get_latest_release(bucket, key):
        """Fetch the latest release version from S3."""
        s3 = boto3.client('s3')
        obj = s3.get_object(Bucket=bucket, Key=key)
        latest_release = obj['Body'].read().decode('utf-8').strip()
        print(f"Latest release version fetched: {latest_release}")
        return latest_release.split('/')[1]

if __name__ == "__main__":
    DATABASE = 'unidrome_daylight'
    S3_OUTPUT = 'unidrome-daylight-latest'
    BUCKET = 'daylight-map-distribution'
    KEY = 'release/latest.txt'
    
    runner = AthenaQueryRunner(DATABASE, f"s3://{S3_OUTPUT}/")
    runner.ensure_database_exists()
    runner.create_external_table()  # Ensure table exists

    release_version = S3Fetcher.get_latest_release(BUCKET, KEY)
    
    for tag in ["runway", "aerodrome"]:
        top_tags = runner.get_top_tags(tag, 50)
        query = runner.build_top_query(top_tags, tag, release_version)
        print(query)
        query_execution_id = runner.run_query(query)
        runner.wait_for_query_to_complete(query_execution_id)
        out = os.path.join('data', 'world', 'daylight-osm', f'{tag}.csv')
        s3 = boto3.client('s3')
        s3.download_file(S3_OUTPUT, f"{query_execution_id}.csv", out)
        print("Results saved to", out)
