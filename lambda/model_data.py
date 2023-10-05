import pandas as pd
import boto3

s3 = boto3.client('s3')

fraudulend_types = [
    'CASH_OUT',
    'TRANSFER'
]

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

def change_type(type_str):
    return type_str.lower() if type_str in ['CASH_OUT', 'TRANSFER'] else 'other'

def check(text, compare=""):
    return 1 if text.lower() == compare.lower() else 0

def fill_dummies(df):
    for column in fraudulend_types+['other']:
        df[column.lower()] = df['type'].apply(check, compare=column)

def model_data(event):
    # Load dataset
    df_raw = pd.read_csv(load_bytes_from_s3(event["input_uri"]))
    # Select columns and rename
    df_modeled = df_raw[['isFraud', 'step', 'type', 'amount', 'oldbalanceOrg', 'newbalanceOrig', 'oldbalanceDest', 'newbalanceDest']]
    df_modeled.columns = ['is_fraud', 'step', 'type', 'amount', 'orig_balance_old', 'orig_balance_new', 'dest_balance_old', 'dest_balance_new']
    # Treat types and one-hot-encode
    df_modeled['type'] = df_modeled['type'].apply(change_type)
    fill_dummies(df_modeled)
    df_modeled = df_modeled[['is_fraud', 'step', 'amount', 'orig_balance_old', 'orig_balance_new', 'dest_balance_old', 'dest_balance_new', 'cash_out', 'other', 'transfer']]
    # Model balance
    df_modeled['orig_balance_change'] = round(df_modeled['orig_balance_new'] - df_modeled['orig_balance_old'], 2)
    df_modeled['dest_balance_change'] = round(df_modeled['dest_balance_new'] - df_modeled['dest_balance_old'], 2)
    df_modeled.drop(['orig_balance_new', 'dest_balance_new'], axis='columns', inplace=True)
    return df_modeled

def under_sample(df, ratio):
    df_true = df.query('is_fraud == 1')
    df_false = df.query('is_fraud == 0')
    min_value = df_true.shape[0]
    try:
        df_false = df_false.sample(min_value*ratio)
    except:
        print('Under sample ratio too high to cut data off!')
    return pd.concat([df_true, df_false])

def split_df(df, ratio):
    df_true = df.query('is_fraud == 1')
    df_false = df.query('is_fraud == 0')
    df_1 = pd.concat([df_true.sample(frac=ratio), df_false.sample(frac=ratio)])
    df_2 = df[~df.index.isin(df_1.index)]
    return df_1, df_2

def split_data(df_modeled, event):
    # Undersample
    df_under = under_sample(df_modeled, event['undersample_ratio'])
    # Split train, validation and test
    df_test, df_train = split_df(df_under, 0.1)
    df_validation, df_train = split_df(df_train, 0.2)
    # Save data
    save_bytes_to_s3(event["train_uri"], bytes(df_train.to_csv(index=False), encoding='utf-8'))
    save_bytes_to_s3(event["validation_uri"], bytes(df_validation.to_csv(index=False), encoding='utf-8'))
    save_bytes_to_s3(event["test_uri"].replace('.csv', '_full.csv'), bytes(df_test.to_csv(index=False), encoding='utf-8'))
    save_bytes_to_s3(event["test_uri"], bytes(df_test.drop('is_fraud', axis='columns').to_csv(index=False, header=False), encoding='utf-8'))

def lambda_handler(event, context):
    df_modeled = model_data(event)
    split_data(df_modeled, event)
