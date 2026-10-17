"""Stage FARMSYNC on organizer-approved AWS services in Mumbai.

Default: print a local plan. --apply creates private resources and verifies a
worker. --publish-api is a separate step and refuses an unverified worker bundle.
Uses the organizer's existing execution role; never creates/modifies IAM roles.
"""
import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from dotenv import load_dotenv
load_dotenv(ROOT/'.env',override=True)
from farmsync.aws import REGION,create_client,system_ca_bundle


def save(path,value):
    path.write_text(json.dumps(value,indent=2),encoding='utf8')

def file_digest(path):
    digest=sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):digest.update(chunk)
    return digest.hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply',action='store_true')
    parser.add_argument('--publish-api',action='store_true')
    parser.add_argument('--role-arn')
    args=parser.parse_args()
    out=ROOT/'.runtime/aws-build'
    manifest_path=out/'manifest.json'
    if not manifest_path.is_file(): raise SystemExit('Build worker artifacts first')
    manifest=json.loads(manifest_path.read_text())
    from build_aws import source_digest
    if manifest.get('source_sha256') != source_digest(ROOT/'farmsync'):
        raise SystemExit('Worker sources changed since build; rebuild with --refresh-code')
    if args.publish_api and (out/'api-source-sha256.txt').read_text() != source_digest(ROOT/'farmsync'):
        raise SystemExit('API sources changed since build; rebuild the API package')
    archive=out/'worker-bundle.tar.gz'
    if file_digest(archive)!=manifest['bundle_sha256'] or file_digest(out/'worker-entry.zip')!=manifest.get('entry_sha256'):
        raise SystemExit('Worker artifact checksum mismatch')
    prefix='fai-tce-team26-farmsync'
    plan={'region':REGION,'services':['S3','DynamoDB','Lambda','API Gateway','CloudWatch Logs'],
          'existing_execution_role':'FAI-TCE-LambdaExecutionRole','resource_prefix':prefix,
          'private_evidence':True,'credentials_in_lambda_environment':False,
          'worker_concurrency':2,'worker_memory_mb':8192,'worker_timeout_seconds':900,
          'ephemeral_storage_mb':10240,'global_daily_job_limit':200,
          'cost_notice':'Creates billable resources. Request caps are not a hard dollar budget. Inspect the organizer Cost-Viewer dashboard.',
          'public_api_requested':args.publish_api,'worker_bundle_verified':manifest.get('linux_runtime_verified',False)}
    save(out/'deployment-plan.json',plan)
    if not args.apply:
        print(json.dumps(plan,indent=2));return
    if args.publish_api and not manifest.get('linux_runtime_verified'):
        raise SystemExit('Private Lambda worker validation must pass before public API deployment')
    identity=create_client('sts').get_caller_identity()
    account=identity['Account']
    import boto3
    from botocore.config import Config
    from botocore.exceptions import ClientError
    role=args.role_arn
    if not role:
        role=boto3.client('iam',region_name=REGION,verify=system_ca_bundle()).get_role(RoleName='FAI-TCE-LambdaExecutionRole')['Role']['Arn']
    if not role.startswith('arn:aws:iam::'+account+':role/') or role.rsplit('/',1)[-1]!='FAI-TCE-LambdaExecutionRole':
        raise SystemExit('Only this organizer account\'s existing FAI-TCE-LambdaExecutionRole is accepted')
    s3,ddb,lam,api,logs=(create_client(s) for s in ['s3','dynamodb','lambda','apigateway','logs'])
    bucket=prefix+'-'+account
    table=prefix+'-records';worker=prefix+'-worker';api_name=prefix+'-api'
    try: s3.head_bucket(Bucket=bucket)
    except ClientError as exc:
        if exc.response['Error']['Code'] not in {'404','NoSuchBucket','NotFound'}:raise
        s3.create_bucket(Bucket=bucket,CreateBucketConfiguration={'LocationConstraint':REGION})
    protections=['BlockPublicAcls','IgnorePublicAcls','BlockPublicPolicy','RestrictPublicBuckets']
    try:
        protection=s3.get_public_access_block(Bucket=bucket)['PublicAccessBlockConfiguration']
    except ClientError as exc:
        raise SystemExit('Organizer-managed S3 security settings cannot be read. Ask the organizer to enable all four public-access protections and allow GetBucketPublicAccessBlock for this deployment bucket. No security restriction was bypassed.') from exc
    if not all(protection.get(k) for k in protections):
        raise SystemExit('Public-access protection is incomplete. The organizer must configure the bucket before deployment.')
    encryption=s3.get_bucket_encryption(Bucket=bucket)['ServerSideEncryptionConfiguration']['Rules']
    if not any(v.get('ApplyServerSideEncryptionByDefault',{}).get('SSEAlgorithm') in {'AES256','aws:kms'} for v in encryption):
        raise SystemExit('Required bucket encryption is not configured')
    if s3.get_bucket_versioning(Bucket=bucket).get('Status')!='Enabled':
        s3.put_bucket_versioning(Bucket=bucket,VersioningConfiguration={'Status':'Enabled'})
    s3.put_bucket_lifecycle_configuration(Bucket=bucket,LifecycleConfiguration={'Rules':[{'ID':'expire-incomplete-staging','Filter':{'Prefix':'staging/'},'Status':'Enabled','Expiration':{'Days':1},'NoncurrentVersionExpiration':{'NoncurrentDays':1}}]})
    try: ddb.describe_table(TableName=table)
    except ddb.exceptions.ResourceNotFoundException:
        ddb.create_table(TableName=table,KeySchema=[{'AttributeName':'PK','KeyType':'HASH'},{'AttributeName':'SK','KeyType':'RANGE'}],AttributeDefinitions=[{'AttributeName':k,'AttributeType':'S'} for k in ['PK','SK','GPK','GSK']],GlobalSecondaryIndexes=[{'IndexName':'owner-index','KeySchema':[{'AttributeName':'GPK','KeyType':'HASH'},{'AttributeName':'GSK','KeyType':'RANGE'}],'Projection':{'ProjectionType':'ALL'}}],BillingMode='PAY_PER_REQUEST',SSESpecification={'Enabled':True})
        ddb.get_waiter('table_exists').wait(TableName=table)
        ddb.update_time_to_live(TableName=table,TimeToLiveSpecification={'Enabled':True,'AttributeName':'ttl'})
    ddb.update_continuous_backups(TableName=table,PointInTimeRecoverySpecification={'PointInTimeRecoveryEnabled':True})
    key='releases/'+manifest['bundle_sha256']+'/worker-bundle.tar.gz'
    s3.upload_file(str(archive),bucket,key,ExtraArgs={'ServerSideEncryption':'AES256'})
    env={'FARMSYNC_BUCKET':bucket,'FARMSYNC_TABLE':table,'FARMSYNC_BUNDLE_KEY':key,'FARMSYNC_BUNDLE_SHA256':manifest['bundle_sha256'],
         'FARMSYNC_SOURCE_SHA256':manifest['source_sha256'],
         'FARMSYNC_ENV':'production','FARMSYNC_OFFLINE':'false','FARMSYNC_ALLOW_RUNTIME_CREDENTIALS':'false',
         'FARMSYNC_EMBEDDINGS_PROVIDER':'bedrock','FARMSYNC_DYNAMIC_PLANNER':'true','FARMSYNC_OCR_ENABLED':'true',
         'FARMSYNC_AMAZON_LOCATION_ENABLED':'true','FARMSYNC_REQUEST_DEADLINE_SECONDS':'180'}
    state={'bucket':bucket,'table':table,'worker':worker,'region':REGION,'bundle_sha256':manifest['bundle_sha256'],'execution_role':role}
    state_path=out/'deployment-state.json'
    previous=json.loads(state_path.read_text()) if state_path.exists() else None
    state={**(previous or {}),**state}
    def deploy_function(name,handler,zip_path,memory,timeout,environment,ephemeral=512):
        code_key='releases/'+file_digest(zip_path)+'/'+zip_path.name
        s3.upload_file(str(zip_path),bucket,code_key,ExtraArgs={'ServerSideEncryption':'AES256'})
        try:
            lam.get_function(FunctionName=name)
        except lam.exceptions.ResourceNotFoundException:
            lam.create_function(FunctionName=name,Runtime='python3.12',Role=role,Handler=handler,Code={'S3Bucket':bucket,'S3Key':code_key},MemorySize=memory,Timeout=timeout,EphemeralStorage={'Size':ephemeral},Architectures=['x86_64'],Environment={'Variables':environment},Publish=True)
            lam.get_waiter('function_active_v2').wait(FunctionName=name)
        else:
            if not previous or previous.get('bucket')!=bucket:
                raise SystemExit('Existing function is not recorded as this deployment; refusing to overwrite it')
            lam.update_function_code(FunctionName=name,S3Bucket=bucket,S3Key=code_key)
            lam.get_waiter('function_updated_v2').wait(FunctionName=name)
            lam.update_function_configuration(FunctionName=name,Runtime='python3.12',Role=role,Handler=handler,MemorySize=memory,Timeout=timeout,EphemeralStorage={'Size':ephemeral},Environment={'Variables':environment})
            lam.get_waiter('function_updated_v2').wait(FunctionName=name)
        try: logs.create_log_group(logGroupName='/aws/lambda/'+name)
        except logs.exceptions.ResourceAlreadyExistsException:pass
        logs.put_retention_policy(logGroupName='/aws/lambda/'+name,retentionInDays=14)
    save(state_path,state)
    deploy_function(worker,'worker_entry.handler',out/'worker-entry.zip',8192,900,env,10240)
    lam.put_function_concurrency(FunctionName=worker,ReservedConcurrentExecutions=2)
    lam.put_function_event_invoke_config(FunctionName=worker,MaximumRetryAttempts=0,MaximumEventAgeInSeconds=120)
    # Initialization and an actual GIS + local model smoke execute under the
    # organizer's role, on the target OS, before an HTTP API can be published.
    validation=boto3.client('lambda',region_name=REGION,verify=system_ca_bundle(),config=Config(read_timeout=910,connect_timeout=5,retries={'total_max_attempts':1}))
    response=validation.invoke(FunctionName=worker,InvocationType='RequestResponse',Payload=b'{"warmup":true,"selftest":true}')
    result=json.loads(response['Payload'].read())
    if response.get('FunctionError') or not result.get('ready') or not result.get('selftest_passed'):
        save(out/'worker-validation.json',{'passed':False,'result':result})
        raise SystemExit('Worker initialization/functional smoke failed. See local worker-validation.json and CloudWatch; public API was not created')
    manifest.update(linux_runtime_verified=True,worker_validation=result)
    save(manifest_path,manifest)
    save(out/'worker-validation.json',{'passed':True,'result':result})
    if not args.publish_api:
        print('Private worker passed Linux smoke. Provision an admin with scripts/manage.py --cloud create-user NAME --role admin, then review the API publication plan.');return
    from farmsync.cloud.store import CloudStore
    os.environ.update(FARMSYNC_TABLE=table,FARMSYNC_BUCKET=bucket)
    if not CloudStore().admin_count():
        raise SystemExit('Provision an active administrator before API publication')
    package=out/'api.zip'
    if not package.is_file():raise SystemExit('API package missing')
    if file_digest(package)!=(out/'api-sha256.txt').read_text():raise SystemExit('API package checksum mismatch')
    # Public endpoint is created only by the explicit --publish-api operation.
    rest=api.get_rest_api(restApiId=state['api_id']) if state.get('api_id') else api.create_rest_api(name=api_name,endpointConfiguration={'types':['REGIONAL']},binaryMediaTypes=['*/*'])
    api_id=rest['id'];origin=f'https://{api_id}.execute-api.{REGION}.amazonaws.com'
    api_env={**env,'FARMSYNC_WORKER':worker,'FARMSYNC_ALLOWED_ORIGINS':origin,'FARMSYNC_API_STAGE':'/prod'}
    deploy_function(api_name,'farmsync.cloud.api.handler',package,512,29,api_env)
    lam.put_function_concurrency(FunctionName=api_name,ReservedConcurrentExecutions=3)
    source=f'arn:aws:execute-api:{REGION}:{account}:{api_id}/*/*/*'
    try: lam.add_permission(FunctionName=api_name,StatementId='api-'+api_id,Action='lambda:InvokeFunction',Principal='apigateway.amazonaws.com',SourceArn=source)
    except lam.exceptions.ResourceConflictException: pass
    resources=api.get_resources(restApiId=api_id)['items']
    root=next(r['id'] for r in resources if r['path']=='/')
    proxy=next((r['id'] for r in resources if r['path']=='/{proxy+}'),None)
    if not proxy:proxy=api.create_resource(restApiId=api_id,parentId=root,pathPart='{proxy+}')['id']
    uri=f'arn:aws:apigateway:{REGION}:lambda:path/2015-03-31/functions/arn:aws:lambda:{REGION}:{account}:function:{api_name}/invocations'
    for resource in (root,proxy):
        api.put_method(restApiId=api_id,resourceId=resource,httpMethod='ANY',authorizationType='NONE')
        api.put_integration(restApiId=api_id,resourceId=resource,httpMethod='ANY',type='AWS_PROXY',integrationHttpMethod='POST',uri=uri)
    s3.put_bucket_cors(Bucket=bucket,CORSConfiguration={'CORSRules':[{'AllowedOrigins':[origin],'AllowedMethods':['GET','POST','HEAD'],'AllowedHeaders':['*'],'MaxAgeSeconds':300}]})
    api.create_deployment(restApiId=api_id,stageName='prod')
    api.update_stage(restApiId=api_id,stageName='prod',patchOperations=[{'op':'replace','path':'/*/*/throttling/rateLimit','value':'5'},{'op':'replace','path':'/*/*/throttling/burstLimit','value':'10'}])
    state.update(api_id=api_id,url=origin+'/prod/')
    save(state_path,state)
    print('API deployed; authenticated browser/upload/job/review smoke still required:',state['url'])


if __name__=='__main__':main()
