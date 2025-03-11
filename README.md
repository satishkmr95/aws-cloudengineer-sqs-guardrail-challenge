## Overview
This project implements an enterprise-grade security guardrail for newly created Amazon SQS queues. 
The solution consists of an AWS Lambda function triggered by EventBridge and enforced security policies using AWS Control Tower.

## Architecture
- **AWS Lambda**: Checks compliance for newly created SQS queues.
- **IAM Role**: Provides permissions for Lambda with a permission boundary.
- **EventBridge Rule**: Triggers Lambda when an SQS queue is created.
- **SNS Topic (Optional)**: Sends alerts if compliance checks fail.
- **AWS Control Tower**: Enforces a guardrail requiring all SQS queues to have a Dead-Letter Queue (DLQ).

## Deployment Instructions


### **1. Deploy CloudFormation to Create the S3 Bucket**
```sh
aws cloudformation deploy \
    --template-file s3_bucket.yaml \
    --stack-name SQSInitialSetup \
    --capabilities CAPABILITY_NAMED_IAM
```

### **1. Package and Upload Lambda Code to S3**
```sh
zip -r lambda_function.zip lambda_function/

S3_BUCKET_NAME=$(
    aws cloudformation describe-stacks \
        --stack-name SQSInitialSetup \
        --query "Stacks[0].Outputs[?OutputKey=='S3BucketName'].OutputValue" \
        --output text
)

aws s3 cp lambda_function.zip s3://$S3_BUCKET_NAME/lambda_function.zip
```

### **2. Deploy CloudFormation Stack**
```sh

TARGET_OU_ARN=arn:aws:organizations::123456789012:ou/o-abcdefg/ou-xyz
CONTROL_IDENTIFIER=AWS-GR_RESTRICTED_SQS_NO_DEAD_LETTER_QUEUE

aws cloudformation deploy \
    --template-file template.yaml \
    --stack-name SQSSecurityGuardrail \
    --capabilities CAPABILITY_NAMED_IAM \
    --parameter-overrides S3BucketName=$S3_BUCKET_NAME TargetOUArn=$TARGET_OU_ARN ControlIdentifier=$CONTROL_IDENTIFIER
```

## Parameters
| Parameter              | Description |
|------------------------|------------|
| LambdaRuntime         | Python runtime version for Lambda (default: python3.11) |
| LambdaMemory          | Memory allocation for Lambda (default: 256MB) |
| PermissionBoundaryArn | ARN of IAM Permission Boundary |
| SNSTopicArn           | ARN of SNS topic for alerts (optional) |
| S3BucketName          | Name of the S3 bucket containing the Lambda function code |
| LambdaFunctionZip     | Name of the Lambda function code ZIP file in the S3 bucket |

## Outputs
| Output              | Description |
|---------------------|------------|
| LambdaFunctionARN  | ARN of the deployed Lambda function |
| IAMRoleARN        | ARN of the IAM role for Lambda |
| SNSTopicARN       | ARN of the SNS topic (if enabled) |

## Design Decisions
- **Permission Boundary**: Ensures Lambda operates within a strict security scope.
- **Multi-Account Strategy**: The solution can be applied across multiple accounts using AWS Organizations.

## Enhancements (Future Work)
- Add GitHub Actions for CI/CD deployment automation.
- Implement additional compliance checks (e.g., SQS policy validation).

## Author
Andres Solarte, [GitHub](https://github.com/andres-solarte)
