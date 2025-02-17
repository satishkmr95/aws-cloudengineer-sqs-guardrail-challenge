# SecretCode: satishkmr95-2025-192
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
AWS_REGION_NAME = os.environ.get('AWS_REGION_NAME')


def check_vpc_endpoint_exists():
    """
    Verify that a VPC endpoint for SQS exists.
    """
    try:
        response = ec2_client.describe_vpc_endpoints(
            Filters=[
                {'Name': 'service-name', 'Values': [f'com.amazonaws.{AWS_REGION_NAME}.sqs']}
            ]
        )
        if not response['VpcEndpoints']:
            logger.error(f"VpcEndpoints doesn't exist!!")
            return False
        else:
            logger.info(f"VpcEndpoints exist!!")
            return True
    except ClientError as e:
        logger.error(f"Error checking VPC endpoint: {e}")

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
            logger.error(f"encryption doesn't exist!!")
            return False
        else:
            logger.info(f"Encryption exist!!")
            return True
    except Exception as e:
        logger.error(f"Unexpected error: {e} in check_encryption_at_rest function")
        logger.error(f"Encryption doesn't exist!!")

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
            logger.error(f"CMK doesn't exist!!")
            return False
        else:
            logger.info(f"CMK exist!!")
            return True
    except Exception as e:
        logger.error(f"Unexpected error: {e} in check_customer_managed_key function")
        logger.error(f"CMK doesn't exist!!")

def check_tags(queue_url):
    """
    Check that the queue is tagged with the required keys.
    """
    try:
        response = sqs_client.list_queue_tags(QueueUrl=queue_url)
        tags = response.get('Tags', {})
        for tag in REQUIRED_TAGS:
            if tag not in tags:
                logger.error(f"Tag doesn't exist!!")
                return False
            else:
                logger.info(f"Tag exist!!")
                return True
    except Exception as e:
        logger.error(f"Unexpected error: {e} in check_tags function")

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
    queue_url = event["detail"]["responseElements"]["queueUrl"]
    if not queue_url:
        logger.error("QueueUrl not provided in the event.")
        return

    checks = {
        'VPC Endpoint Check': check_vpc_endpoint_exists(),
        'Encryption-at-Rest Check': check_encryption_at_rest(queue_url),
        'Customer-Managed Key Check': check_customer_managed_key(queue_url),
        'Tag Verification Check': check_tags(queue_url)
    }
    result_messages = []

    for check, value in checks.items():
        if value:
            result_messages.append(f"✅ {check} passed.")
        else:
            result_messages.append(f"❌ {check} doesn't exist or failed.")

    # Join the messages into a single string
    final_message = "\n".join(result_messages)

    # Print the final report
    trigger_alert(final_message)
    return {
        'statusCode': 200,
        'body': 'Compliance checks completed.'
    }
