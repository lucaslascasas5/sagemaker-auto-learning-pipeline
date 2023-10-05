#!/bin/bash

echo "##### VALIDATING CLOUDFORMATION TEMPLATES"

while IFS= read -r -d '' cfn_template
do
  echo "### Validating CloudFormation template file $cfn_template"
  if ! aws cloudformation validate-template --template-body "file://$cfn_template" > tmp
  then
    echo | cat tmp
    rm tmp
    exit 1
  fi
done < <(find ./cloudformation -type f -regex ".*\.\(yaml\|yml\)$" -print0)

echo "##### VALIDATING CLOUDFORMATION PARAMETERS CONFIGURATIONS"

while IFS= read -r -d '' conf
do
  echo "### Validating CFN parameters config file $conf"
  if ! python3 -m json.tool < "$conf" > tmp
  then
    echo | cat tmp
    rm tmp
    exit 1
  fi
done < <(find ./cloudformation -type f -regex ".*\.json$" -print0)

rm tmp
