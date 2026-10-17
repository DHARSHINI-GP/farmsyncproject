# Organizer action required for cloud release

Checked 17 October 2026 after refreshing both assigned development identities.

**Passed live:** STS, Ministral 3B text, Ministral 8B vision, Titan Text Embeddings
V2, Titan Multimodal Embeddings, Amazon Location reverse geocoding and road routing.
S3/DynamoDB/Lambda/API Gateway inventory and the existing execution-role metadata
are readable. These are point-in-time checks, not a deployment certificate.

**Blocked:** the Builder-AI role has an explicit deny on
`s3:PutBucketPublicAccessBlock`. Reading the bucket's public-access configuration
also returns AccessDenied. No IAM or bucket-publicness restriction was bypassed.
The deployment stopped before creating a Lambda function, API Gateway endpoint or
new DynamoDB table. One empty deployment bucket was created under
`fai-tce-team26-farmsync-<organizer-account-id>`; no dataset/model bundle was uploaded.

The organizer can unblock the release without granting permission to weaken
public-access protections:

1. Configure/confirm **all four S3 Block Public Access settings enabled** on that
   deployment bucket, encryption enabled and public ACLs/policies prohibited.
2. Permit the assigned Builder-AI role to read that bucket's configuration through
   `s3:GetBucketPublicAccessBlock`. The updated deployer reads existing protection
   and does not attempt to change it.
3. Ensure the existing **FAI-TCE-LambdaExecutionRole** can read this deployment's
   private bundle/evidence/results, write owner-scoped evidence/results, use its
   DynamoDB table/index, invoke the worker, write logs, use the four approved
   Bedrock models and call the assigned Location index/calculator in Mumbai.
   Development Builder-Location access does not automatically grant Lambda access.

Only the first security-configuration gate has been reached; further execution-role
permissions are not yet verified. Existing guide restrictions and resource naming
remain applicable. Do not create another IAM role, change regions, embed temporary
SSO credentials in Lambda or substitute another cloud provider to avoid this gate.

After the organizer action, rerun the private worker deployment, inspect its actual
Linux functional/AI/Location checks, provision an individual administrator, and
complete authenticated HTTPS/browser/upload/job/review/recovery acceptance before
public release. The application is not certified production-ready while these
steps remain unverified. No message has been sent to the organizer automatically.
