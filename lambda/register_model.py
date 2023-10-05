import os
import boto3
import pandas as pd
from datetime import datetime

sagemaker = boto3.client('sagemaker')
s3 = boto3.client('s3')

def split_uri(uri):
    # Remove o "s3://"
    uri = uri[5:]
    # Quebra o bucket e key
    bucket = uri.split('/')[0]
    key = uri[len(bucket)+1:]
    return (bucket, key)

def load_bytes_from_s3(uri):
    bucket, key = split_uri(uri)
    response = s3.get_object(
        Bucket = bucket,
        Key = key
    )
    return response['Body'] if 'Body' in response else None

def save_bytes_to_s3(uri, obj_bytes):
    bucket, key = split_uri(uri)
    s3.put_object(
        Bucket = bucket,
        Body = obj_bytes,
        Key = key
    )

def get_metrics(predictions_uri, test_uri):
    df_batch = pd.read_csv(load_bytes_from_s3(predictions_uri), names=['prediction'])
    df_test = pd.read_csv(load_bytes_from_s3(test_uri))
    df_test['prediction'] = round(df_batch['prediction'])
    df_confusion = pd.crosstab(index=df_test['is_fraud'], columns=df_test['prediction'], rownames=['actuals'], colnames=['predictions'])
    precision = df_confusion.iloc[1][1]/(df_confusion[1].sum())
    recall = df_confusion.iloc[1][1]/(df_confusion.iloc[1].sum())
    f1 = 2*(recall*precision)/(recall+precision)
    save_bytes_to_s3(predictions_uri.replace('.csv.out', '_confusion.csv'), bytes(df_confusion.to_csv(), encoding='utf-8'))
    return precision, recall, f1

def create_model_package(model_package_group_name, image_uri, model_uri, precision, recall, f1, model_name):
    try:
        model_package_group_arn = sagemaker.describe_model_package_group(
            ModelPackageGroupName=model_package_group_name
        )['ModelPackageGroupArn']
    except:
        model_package_group_input_dict = {
            "ModelPackageGroupName" : model_package_group_name,
            "ModelPackageGroupDescription" : "Model package group for xgboost regression model with Abalone dataset"
        }
        create_model_pacakge_group_response = sagemaker.create_model_package_group(**model_package_group_input_dict)
        model_package_group_arn = create_model_pacakge_group_response['ModelPackageGroupArn']
        print(f'ModelPackageGroup Arn : {model_package_group_arn}')

    modelpackage_inference_specification =  {
        "InferenceSpecification": {
            "Containers": [
                {
                    "Image": image_uri
                }
            ],
            "SupportedContentTypes": [ "text/csv" ],
            "SupportedResponseMIMETypes": [ "text/csv" ],
        }
    }
    # Specify the model data
    modelpackage_inference_specification["InferenceSpecification"]["Containers"][0]["ModelDataUrl"]=model_uri

    create_model_package_input_dict = {
        "ModelPackageGroupName" : model_package_group_arn,
        "ModelPackageDescription" : "Model for fraud prediction",
        "ModelApprovalStatus" : "PendingManualApproval",
        "CustomerMetadataProperties":{
            "precision": str(precision),
            "recall": str(recall),
            "f1": str(f1),
            "model_name": model_name
        }
    }
    create_model_package_input_dict.update(modelpackage_inference_specification)
    print(create_model_package_input_dict)

    # Create cross-account model package
    create_model_package_response = sagemaker.create_model_package(**create_model_package_input_dict)
    model_package_arn = create_model_package_response["ModelPackageArn"]
    print(f'ModelPackage Version ARN : {model_package_arn}')

    return model_package_arn

def lambda_handler(event, context):
    test_data_path = event['test_data_path'].replace('.csv', '_full.csv')
    batch_output_path = event['batch_output_path'] + event['test_data_path'].split('/')[-1]+'.out'
    print(batch_output_path)
    precision, recall, f1 = get_metrics(batch_output_path, test_data_path)
    create_model_package(
        model_package_group_name = os.environ['model_package_group_name'],
        model_uri=event['model_uri'],
        image_uri=event['image_uri'],
        precision=precision,
        recall=recall,
        f1=f1,
        model_name=event['model_name']
    )
