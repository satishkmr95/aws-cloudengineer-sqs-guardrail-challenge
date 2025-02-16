# SecretCode: <YourGitHubUsername>-2025-<YourRandom3CharCode>

import boto3
import logging
import os
from botocore.exceptions import ClientError

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
sqs_client = boto3.client('sqs')
ec2_client = boto3.client('ec2')
sns_client = boto3.client('sns')

# Constants
REQUIRED_TAGS = ['Name', 'Created By', 'Cost Center']
SNS_TOPIC_ARN = os.environ.get('SNS_TOPIC_ARN')

def check_vpc_endpoint_exists():
    """
    Verify that a VPC endpoint for SQS exists.
    """
    try:
        response = ec2_client.describe_vpc_endpoints(
            Filters=[
                {'Name': 'service-name', 'Values': ['com.amazonaws.us-east-1.sqs']}
            ]
        )
        if not response['VpcEndpoints']:
            return False
        return True
    except ClientError as e:
        logger.error(f"Error checking VPC endpoint: {e}")
        raise

def check_encryption_at_rest(queue_url):
    """
    Ensure that the SQS queue has encryption enabled.
    """
    try:
        response = sqs_client.get_queue_attributes(
            QueueUrl=queue_url,
            AttributeNames=['KmsMasterKeyId']
        )
        if 'KmsMasterKeyId' not in response['Attributes']:
            return False
        return True
    except ClientError as e:
        logger.error(f"Error checking encryption: {e}")
        raise

def check_customer_managed_key(queue_url):
    """
    Confirm that the queue uses a customer-managed key (CMK) rather than an AWS-managed key.
    """
    try:
        response = sqs_client.get_queue_attributes(
            QueueUrl=queue_url,
            AttributeNames=['KmsMasterKeyId']
        )
        key_id = response['Attributes'].get('KmsMasterKeyId')
        if not key_id or key_id.startswith('alias/aws/'):
            return False
        return True
    except ClientError as e:
        logger.error(f"Error checking CMK: {e}")
        raise

def check_tags(queue_url):
    """
    Check that the queue is tagged with the required keys.
    """
    try:
        response = sqs_client.list_queue_tags(QueueUrl=queue_url)
        tags = response.get('Tags', {})
        for tag in REQUIRED_TAGS:
            if tag not in tags:
                return False
        return True
    except ClientError as e:
        logger.error(f"Error checking tags: {e}")
        raise

def trigger_alert(message):
    """
    Trigger an alert by publishing a message to an SNS topic.
    """
    try:
        sns_client.publish(
            TopicArn=SNS_TOPIC_ARN,
            Message=message,
            Subject='SQS Queue Compliance Check Failed'
        )
        logger.info(f"Alert triggered: {message}")
    except ClientError as e:
        logger.error(f"Error triggering alert: {e}")
        raise

def lambda_handler(event, context):
    """
    Main Lambda function handler.
    """
    queue_url = event.get('QueueUrl')
    if not queue_url:
        logger.error("QueueUrl not provided in the event.")
        return

    checks = {
        'VPC Endpoint Check': check_vpc_endpoint_exists(),
        'Encryption-at-Rest Check': check_encryption_at_rest(queue_url),
        'Customer-Managed Key Check': check_customer_managed_key(queue_url),
        'Tag Verification Check': check_tags(queue_url)
    }

    failed_checks = [check_name for check_name, result in checks.items() if not result]

    if failed_checks:
        alert_message = f"Compliance checks failed for queue {queue_url}. Failed checks: {', '.join(failed_checks)}"
        trigger_alert(alert_message)
    else:
        logger.info("All compliance checks passed.")

    return {
        'statusCode': 200,
        'body': 'Compliance checks completed.'
    }