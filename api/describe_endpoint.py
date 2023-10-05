import boto3
import json

sagemaker = boto3.client('sagemaker')

def check_body(event):
    print("EVENT:", event)
    if 'body' not in event:
        return False, {'statusCode': 400, 'body': 'Missing endpoint required body!'}
    else:
        body = json.loads(event['body'])
        print("BODY:", body)
        if 'model_package_arn' not in body:
            return False, {'statusCode': 400, 'body': 'Missing required "model_package_arn" in body'}
        return True, body

def lambda_handler(event, context):
    valid, body = check_body(event)
    if not valid:
        return body
    
    model_details = sagemaker.describe_model_package(
        ModelPackageName=body['model_package_arn']
    )
    
    try:
        endpoint_name = model_details['CustomerMetadataProperties']['endpoint_name']
    except:
        return {'statusCode': 502, 'body': 'Cannot deploy endpoint withou "EndpointName" and "EndpointConfigName" in its details. Please contact a Data Scientist responsible for the project.'}
    
    describe_endpoint_response = sagemaker.describe_endpoint(EndpointName=endpoint_name)

    return {'statusCode': 200, 'body': f'Endpoint current status is: "{describe_endpoint_response["EndpointStatus"]}"'}