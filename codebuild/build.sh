#!/bin/bash
set -e  # exit when any command fails

echo "##### PACKAGING SAM TEMPLATE"
if ! sam package --s3-bucket "$ARTIFACT_BUCKET" -t "./cloudformation/serverless.yaml" \
  --output-template-file "./cloudformation/serverless.yaml"
then
  echo | cat tmp
  rm tmp
  exit 1
fi

echo "##### REPLACING VALUES IN PARAMETERS CONFIGURATIONS"
sed -i -e "s/STAGE_PLACEHOLDER/$STAGE/" cloudformation/configuration.json
sed -i -e "s+SECURITY_GROUP_ID_PLACEHOLDER+$SECURITY_GROUP_ID+" cloudformation/configuration.json
sed -i -e "s+SUBNET_IDS_PLACEHOLDER+$SUBNET_IDS+" cloudformation/configuration.json
sed -i -e "s+VPC_ENDPOINT_API_ID_PLACEHOLDER+$VPC_ENDPOINT_API_ID+" cloudformation/configuration.json
sed -i -e "s+ROLES_LIST_PLACEHOLDER+$ROLES_LIST+" cloudformation/configuration.json
