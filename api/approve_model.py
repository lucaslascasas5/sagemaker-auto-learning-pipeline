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
    
    model_package_update_input_dict = {
        "ModelPackageArn" : body['model_package_arn'],
        "ModelApprovalStatus" : "Approved"
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
        relevant_detais["ModelName"] = round(float(model_details['CustomerMetadataProperties']['model_name'])*100, 2)
    except:
        relevant_detais["ModelName"] = 'Invalid data. Please contact a Data Scientist to check SageMaker and Step Functions.'

    return {'statusCode': 200, 'body': json.dumps(relevant_detais)}
