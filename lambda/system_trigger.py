import boto3
import os
import json
from datetime import datetime

step_functions = boto3.client('stepfunctions')

def lambda_handler(event, context):
    today = datetime.now().strftime("%Y-%m-%d")
    bucket = os.environ['project_bucket']
    payload = {
        "input_uri": os.environ['input_data'],
        "train_uri": f"s3://{bucket}/data/model-{today}/train.csv",
        "validation_uri": f"s3://{bucket}/data/model-{today}/validation.csv",
        "test_uri": f"s3://{bucket}/data/model-{today}/test.csv",
        "output_path": f"s3://{bucket}/models/model-{today}/",
        "batch_output_path": f"s3://{bucket}/batch/model-{today}/",
        "instance_type": os.environ['training_instance'],
        "batch_instance_type": os.environ['batch_instance'],
        "hpo_job_name": f"model-{today}"
    }
    response = step_functions.start_execution(
        stateMachineArn=os.environ['orchestrator_arn'],
        input=json.dumps(payload)
    )
    print(response)
