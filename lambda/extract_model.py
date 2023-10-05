import boto3

sagemaker = boto3.client('sagemaker')

def lambda_handler(event, context):
    response = sagemaker.describe_training_job(TrainingJobName=event['data']['BestTrainingJob']['TrainingJobName'])
    return response['ModelArtifacts']['S3ModelArtifacts']
