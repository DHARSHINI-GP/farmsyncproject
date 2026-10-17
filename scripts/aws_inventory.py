"""Read organizer services and the existing execution role; never print secrets."""
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dotenv import load_dotenv
load_dotenv(override=True)
from farmsync.aws import create_client, safe_error, system_ca_bundle, REGION


def inventory():
    checks = {}
    for service, method in [('sts', 'get_caller_identity'), ('lambda', 'list_functions'), ('s3', 'list_buckets'), ('dynamodb', 'list_tables'), ('apigateway', 'get_rest_apis')]:
        try:
            result = getattr(create_client(service), method)()
            names = result.get('TableNames', [])
            if service == 'lambda': names = [r['FunctionName'] for r in result.get('Functions', [])]
            if service == 's3': names = [r['Name'] for r in result.get('Buckets', [])]
            if service == 'apigateway': names = [r['name'] for r in result.get('items', [])]
            checks[service] = {'success': True, 'names': names}
        except Exception as exc:
            checks[service] = {'success': False, 'error': safe_error(exc)}
    try:
        import boto3
        role = boto3.client('iam', region_name=REGION, verify=system_ca_bundle()).get_role(RoleName='FAI-TCE-LambdaExecutionRole')['Role']
        # Read only. No IAM create/update/assume operation is performed.
        checks['execution_role'] = {'success': True, 'role_name': role['RoleName'], 'lambda_trust_present': 'lambda.amazonaws.com' in json.dumps(role['AssumeRolePolicyDocument'])}
    except Exception as exc:
        checks['execution_role'] = {'success': False, 'error': safe_error(exc)}
    return checks


if __name__ == '__main__':
    result = inventory()
    output = Path('scratch/aws-deployment-inventory.json')
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
