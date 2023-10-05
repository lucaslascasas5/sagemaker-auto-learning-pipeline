import boto3
import os
import datetime
import json

sagemaker = boto3.client('sagemaker')

def lambda_handler(event, context):
    try:
        sagemaker.describe_model_package_group(
            ModelPackageGroupName=os.environ['model_package_group_name']
        )['ModelPackageGroupArn']
    except:
        return {'statusCode': 502, 'body': 'Model Group does not exist. Please contact a Data Scientist responsible for the project.'}

    model_list = boto3.client('sagemaker').list_model_packages(
        ModelPackageGroupName=os.environ['model_package_group_name']
    )

    details = {}

    for model in model_list['ModelPackageSummaryList']:
        model_details = sagemaker.describe_model_package(
            ModelPackageName=model['ModelPackageArn']
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
            relevant_detais["EndpointConfigName"] = 'Not deployed.'
        try:
            relevant_detais["EndpointName"] = model_details['CustomerMetadataProperties']['endpoint_name']
        except:
            relevant_detais["EndpointName"] = 'Not deployed.'

        if model_details['ModelApprovalStatus'] in details:
            details[model_details['ModelApprovalStatus']].append(relevant_detais)
        else:
            details[model_details['ModelApprovalStatus']] = [relevant_detais]
    return {
        'statusCode': 200,
        'body': json.dumps(details)
    }
