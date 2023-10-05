import boto3
import json
import os
from datetime import datetime

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
        if 'instance_type' not in body:
            body['instance_type'] = os.environ['default_instance_type']
        return True, body

def create_endpoint_config(instance_type, model_name):
    endpoint_config_name = 'xgboost-' + datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    print(endpoint_config_name)
    create_endpoint_config_response = sagemaker.create_endpoint_config(
        EndpointConfigName = endpoint_config_name,
        ProductionVariants = [
            {
                'InstanceType': instance_type,
                'InitialInstanceCount': 1,
                'InitialVariantWeight': 1,
                'ModelName': model_name,
                'VariantName': 'AllTraffic'
            }
        ]
    )
    print("Endpoint Configuration Arn: " + create_endpoint_config_response["EndpointConfigArn"])
    return endpoint_config_name

def create_endpoint(endpoint_config_name):
    endpoint_name = 'xgboost-realtime-ep-' + datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    print("EndpointName={}".format(endpoint_name))

    create_endpoint_response = sagemaker.create_endpoint(
        EndpointName=endpoint_name,
        EndpointConfigName=endpoint_config_name
    )
    print(create_endpoint_response['EndpointArn'])
    return endpoint_name

def lambda_handler(event, context):
    valid, body = check_body(event)
    if not valid:
        return body

    model_details = sagemaker.describe_model_package(
        ModelPackageName=body['model_package_arn']
    )

    try:
        model_name = model_details['CustomerMetadataProperties']['model_name']
    except:
        return {'statusCode': 502, 'body': 'Cannot deploy endpoint withou "ModelName" in its details. Please contact a Data Scientist responsible for the project.'}

    endpoint_config_name = create_endpoint_config(body['instance_type'], model_name)
    endpoint_name = create_endpoint(endpoint_config_name)

    model_details = sagemaker.describe_model_package(
        ModelPackageName=body['model_package_arn']
    )

    custom_properties = model_details['CustomerMetadataProperties']
    custom_properties['endpoint_config_name'] = endpoint_config_name
    custom_properties['endpoint_name'] = endpoint_name

    model_package_update_input_dict = {
        "ModelPackageArn" : body['model_package_arn'],
        "CustomerMetadataProperties" : custom_properties
    }
    model_package_update_response = sagemaker.update_model_package(**model_package_update_input_dict)
    print(model_package_update_response)
    
    model_details = sagemaker.describe_model_package(
        ModelPackageName=body['model_package_arn']
    )

    relevant_detais = {
        "ModelPackageArn": model_details.get('ModelPackageArn'),
        "ModelPackageStatus": model_details.get('ModelPackageStatus'),
        "ModelApprovalStatus": model_details.get('ModelApprovalStatus')
    }
    try:
        relevant_detais["CreationTime"] =  model_details['CreationTime'].strftime("%Y-%m-%d-%H-%M-%S")
    except:
        relevant_detais["CreationTime"] = 'Could not retrieve!'
    try:
        relevant_detais["F1-Score"] = round(float(model_details['CustomerMetadataProperties']['f1'])*100, 2)
    except:
        relevant_detais["F1-Score"] = 'Invalid data'
    try:
        relevant_detais["Precision"] = round(float(model_details['CustomerMetadataProperties']['precision'])*100, 2)
    except:
        relevant_detais["Precision"] = 'Invalid data'
    try:
        relevant_detais["Recall"] = round(float(model_details['CustomerMetadataProperties']['recall'])*100, 2)
    except:
        relevant_detais["Recall"] = 'Invalid data'
    try:
        relevant_detais["ModelName"] = model_details['CustomerMetadataProperties']['model_name']
    except:
        relevant_detais["ModelName"] = 'Invalid data. Please contact a Data Scientist to check SageMaker and Step Functions.'
    try:
        relevant_detais["EndpointConfigName"] = model_details['CustomerMetadataProperties']['endpoint_config_name']
    except:
        relevant_detais["EndpointConfigName"] = 'Invalid data. Please contact a Data Scientist to check SageMaker and Step Functions.'
    try:
        relevant_detais["EndpointName"] = model_details['CustomerMetadataProperties']['endpoint_name']
    except:
        relevant_detais["EndpointName"] = 'Invalid data. Please contact a Data Scientist to check SageMaker and Step Functions.'

    return {'statusCode': 200, 'body': json.dumps(relevant_detais)}
