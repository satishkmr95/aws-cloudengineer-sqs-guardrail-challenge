# AWS CloudFormation Guardrails for SQS Queues

This repository contains an AWS CloudFormation template to enforce guardrails for newly created SQS queues. The solution includes:

- A Python-based AWS Lambda function
- An IAM role with a permission boundary
- A SNS Topic
- A Lambda function
- An EventBridge rule to trigger the Lambda function
- A Control Tower guardrail
- GitHub Actions for CI/CD

## Prerequisites

Ensure you have the following:

- An S3 bucket to store artifacts in management account. i.e github-action-cicdsqs-guardrail-artifactbucket

- Enabled AWS Control Tower, AWS Organizations with Organizational Units (OUs) and stacksets in your AWS account.

- AWS CloudTrail must be enabled; otherwise, the Lambda function won't trigger on SQS create events.

- OIDC authentication established with proper permissions (i.e., Administrator access) with the IAM role name **GitHub-OIDC** in management account so that it can be assumed by GitHub Actions while running the pipeline. Ref : https://mahendranp.medium.com/configure-github-openid-connect-oidc-provider-in-aws-b7af1bca97dd

- A GitHub self hosted runner based on Linux. If you are using Amazon Linux, run the following command to install a required dependency before you run the command to run a runner, you can get the details around setting up runner from Github Repo's Settings->Actions->Runners:

  ```sh
  sudo yum install libicu -y
  ```

- Set up the following as repository variables:

  ```sh
  ARN=arn:aws:iam::xxxxxxxxxxx:role/GitHub-OIDC
  LambdaCodeS3Bucket=github-action-cicdsqs-guardrail-artifactbucket
  LambdaCodeS3Key=lambda_function.zip
  ManagementAccountId=xxxxxxxxxxxx
  OrganizationalUnitIds=ou-ome8-xxxxxxxxx
  OrganizationId=oxxxxxxx
  AWS_REGION=us-east-1
  ```
  **LambdaCodeS3Bucket** variable will be used to store the Artifacts of GitHub action pipeline \
  **LambdaCodeS3Key** variable store the zip file name \
  **OrganizationId** variable stores AWS Organization ID \
  **OrganizationalUnitIds** variable stores OU Id where you want to deploy your solution

- One secret: `ROLENAME` i.e basically a session name, set this as a repository secret

## Deployment Instructions

1. Setup the GitHub action runner in management account 

2. Setup the repository variables in GitHub Repository

3. Setup the OIDC auth in management account. 

4. Run the pipeline
 

## Design Decisions

### Permission Boundary Implementation

- The IAM role created for the Lambda function enforces a permission boundary, ensuring that only explicitly allowed actions can be performed.
- The boundary restricts excessive permissions while allowing necessary operations.

### CFT Parameters

- I have added following parameters in the ``` deploy.yml``` file as it will change according to your setup
- LambdaCodeS3Bucket
- LambdaCodeS3Key
- OrganizationId
- OrganizationalUnitId
- ManagementAccountId


### Multi-Account Considerations

- This solution can be extended to a multi-account environment&#x20;
- You just need to change the OU id.

## GitHub Actions CI/CD

For automation, a GitHub Actions workflow (`.github/workflows/deploy.yml`) can be used to deploy changes automatically:

```yaml
name: AWS OIDC Connect
on:
  push  
permissions:
  id-token: write
  contents: read
jobs:
  SQSGuardRail:
    runs-on: self-hosted
    steps:
      - name: Git clone the repository
        uses: actions/checkout@v3

      - name: configure aws credentials
        uses: aws-actions/configure-aws-credentials@v1
        with:
          role-to-assume: ${{ vars.ARN }}
          role-session-name: ${{ secrets.ROLENAME }}
          aws-region: ${{ vars.AWS_REGION }}

      - name: Print assumed role
        run: aws sts get-caller-identity

      - name: ziping lambda code
        run: |
          cd lambda_code
          zip lambda_function.zip lambda_function.py
          aws s3 cp lambda_function.zip s3://${{ vars.LambdaCodeS3Bucket }}/

      - name: Run aws CloudFormation command
        run: aws s3 cp template.yaml s3://${{ vars.LambdaCodeS3Bucket }}/ 

      - name: Run aws CloudFormation create stack set command
        run: |
          aws cloudformation create-stack-set \
            --stack-set-name MySQSGuardRailSet \
            --template-body file://template.yaml \
            --capabilities CAPABILITY_NAMED_IAM \
            --parameters \
            ParameterKey=LambdaCodeS3Bucket,ParameterValue=${{ vars.LambdaCodeS3Bucket }} \
            ParameterKey=LambdaCodeS3Key,ParameterValue=${{ vars.LambdaCodeS3Key }} \
            ParameterKey=OrganizationalUnitId,ParameterValue=${{ vars.OrganizationalUnitIds }} \
            ParameterKey=ManagementAccountId,ParameterValue=${{ vars.ManagementAccountId }} \
            ParameterKey=AWSRegion,ParameterValue=${{ vars.AWS_REGION }} \
            ParameterKey=OrganizationId,ParameterValue=${{ vars.OrganizationId }} \
            --region ${{ vars.AWS_REGION }} \
            --permission-model SERVICE_MANAGED --auto-deployment Enabled=true,RetainStacksOnAccountRemoval=false
            
       

      - name: Run aws CloudFormation create stack instances command
        run: |
          export OPERATION_ID=$(aws cloudformation create-stack-instances \
            --stack-set-name MySQSGuardRailSet \
            --parameter-overrides \
            ParameterKey=LambdaCodeS3Bucket,ParameterValue=${{ vars.LambdaCodeS3Bucket }} \
            ParameterKey=LambdaCodeS3Key,ParameterValue=${{ vars.LambdaCodeS3Key }} \
            ParameterKey=OrganizationalUnitId,ParameterValue=${{ vars.OrganizationalUnitIds }} \
            ParameterKey=ManagementAccountId,ParameterValue=${{ vars.ManagementAccountId }} \
            ParameterKey=AWSRegion,ParameterValue=${{ vars.AWS_REGION }} \
            ParameterKey=OrganizationId,ParameterValue=${{ vars.OrganizationId }} \
            --deployment-targets OrganizationalUnitIds=${{ vars.OrganizationalUnitIds }} \
            --regions ${{ vars.AWS_REGION }} \
            --operation-preferences FailureToleranceCount=0,MaxConcurrentCount=1 --output text --query OperationId)
          echo "OPERATION_ID=$OPERATION_ID" >> $GITHUB_ENV

      - name: Check the status of Stack instances
        run: |
          while true; do
              STATUS=$(aws cloudformation describe-stack-set-operation \
          --stack-set-name MySQSGuardRailSet \
          --operation-id $OPERATION_ID \
                  --query "StackSetOperation.Status" \
                  --output text)
              echo "Current Status: $STATUS"

              if [[ "$STATUS" == "SUCCEEDED" ]]; then
                  echo "Stack set operation succeeded!"
                  break
              elif [[ "$STATUS" == "FAILED" || "$STATUS" == "STOPPED" ]]; then
                  echo "Stack set operation failed or was stopped."
                  exit 1
              fi
              # Wait for 10 seconds before checking again
              sleep 10
          done
```

This CI/CD setup ensures that updates to the repository are automatically deployed to AWS.
