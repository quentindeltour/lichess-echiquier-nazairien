import os 
import boto3
import pandas as pd

def create_s3_object():
    return boto3.resource(
        service_name='s3',
        region_name='us-east-2',
        aws_access_key_id=os.environ['AWS_ACCESS_KEY_ID'],
        aws_secret_access_key=os.environ['AWS_SECRET_ACCESS_KEY']
    )

def read_s3_csv_file(filename, bucket='lichess-app-assets'):
    s3 = create_s3_object()
    obj = s3.Bucket(bucket).Object(filename).get()
    df = pd.read_csv(obj['Body'], index_col=0)
    return df


def get_list_s3_objects(bucket='lichess-app-assets'):
    s3 = create_s3_object()
    return [obj.key for obj in s3.Bucket('lichess-app-assets').objects.all()]