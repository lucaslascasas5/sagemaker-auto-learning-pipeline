import boto3
import os
import pandas as pd
import json

sagemaker = boto3.client('sagemaker-runtime')
sagemaker_client = boto3.client('sagemaker')

fraudulend_types = [
    'CASH_OUT',
    'TRANSFER'
]

def check_body(event):
    print("EVENT:", event)
    if 'body' not in event:
        return False, {'statusCode': 400, 'body': 'Missing endpoint required body!'}
    else:
        body = json.loads(event['body'])
        print("BODY:", body)
        if 'transactions' not in body:
            return False, {'statusCode': 400, 'body': 'Missing required "transactions" in body'}
        if 'endpoint_name' not in body and 'model_package_arn' not in body:
            return False, {'statusCode': 400, 'body': 'Missing required "endpoint_name" or "model_package_arn" in body'}
        return True, body

def change_type(type_str):
    return type_str.lower() if type_str in ['CASH_OUT', 'TRANSFER'] else 'other'

def check(text, compare=""):
    return 1 if text.lower() == compare.lower() else 0

def fill_dummies(df):
    for column in fraudulend_types+['other']:
        df[column.lower()] = df['type'].apply(check, compare=column)

def treat_transaction(transactions):
    df = pd.read_json(json.dumps(transactions), orient='index')
    df_modeled = df[['step', 'type', 'amount', 'oldbalanceOrg', 'newbalanceOrig', 'oldbalanceDest', 'newbalanceDest']]
    df_modeled.columns = ['step', 'type', 'amount', 'orig_balance_old', 'orig_balance_new', 'dest_balance_old', 'dest_balance_new']
    df_modeled['type'] = df_modeled['type'].apply(change_type)
    fill_dummies(df_modeled)
    df_modeled = df_modeled[['step', 'type', 'amount', 'orig_balance_old', 'orig_balance_new', 'dest_balance_old', 'dest_balance_new', 'cash_out', 'other', 'transfer']]
    df_modeled.drop('type', axis='columns', inplace=True)
    df_modeled['orig_balance_change'] = round(df_modeled['orig_balance_new'] - df_modeled['orig_balance_old'], 2)
    df_modeled['dest_balance_change'] = round(df_modeled['dest_balance_new'] - df_modeled['dest_balance_old'], 2)
    df_modeled.drop(['orig_balance_new', 'dest_balance_new'], axis='columns', inplace=True)
    payload = df_modeled.to_csv(header=False, index=False)
    if df_modeled.shape[0] == 1:
        payload = payload[:-1].replace('\n', ',')
    return payload

def treat_inference(transactions, inference_response):
    keys = list(transactions.keys())
    inferences = inference_response.decode('utf-8').split('\n')
    print(inferences)
    print('-')
    response = {}
    for i, key in enumerate(keys):
        response[key] = {
            "is_fraud": 1 if float(inferences[i]) >= float(os.environ['fraud_treshold']) else 0,
            "fraud_chance": round(float(inferences[i])*100, 2)
        }
    return response

def lambda_handler(event, context):
    valid, body = check_body(event)
    
    if not valid:
        return body
    
    try:
        payload = treat_transaction(body['transactions'])
        print("PAYLOAD:", payload)
    except:
        return {"statusCode": 400, "body": "Could not transform input. Check API documentation for details!"}
    
    if 'model_package_arn' in body:
        try:
            model_details = sagemaker_client.describe_model_package(
                ModelPackageName=body['model_package_arn']
            )
            endpoint_name = model_details['CustomerMetadataProperties']['endpoint_name']
        except:
            return {'statusCode': 502, 'body': 'Could not find endpoint name. Try deploying endpoint first.'}
    else:
        endpoint_name = body['endpoint_name']

    try:
        response = sagemaker.invoke_endpoint(
            EndpointName=endpoint_name,
            Body=payload,
            ContentType='csv'
        )
        print("SAGEMAKER RESPONSE:", response)
    except:
        return {"statusCode": 500, "body": "Could not infer payload. Check SageMaker logs for detais!"}
    
    try:
        response_body = treat_inference(body['transactions'], response['Body'].read())
        print("FINAL RESPONSE:", response_body)
    except:
        return {"statusCode": 500, "body": "Could not process inference output. Check CloudWatch logs for details"}
    
    return {"statusCode": 200, "body": json.dumps(response_body)}
