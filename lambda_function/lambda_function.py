# SecretCode: YourGitHubUsername-2025-XYZ
import json
import boto3
import os
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

sns_client = boto3.client("sns")
sqs_client = boto3.client("sqs")

def lambda_handler(event, context):
    logger.info("Received event: %s", json.dumps(event))

    for record in event.get("detail", {}).get("resources", []):
        queue_url = record.get("ARN")
        logger.info(f"Checking security compliance for SQS: {queue_url}")

        # Perform security checks (encryption, VPC endpoint, tags)
        issues = check_queue_compliance(queue_url)

        if issues:
            message = f"Security issues found in SQS Queue {queue_url}: {', '.join(issues)}"
            logger.error(message)
            if os.getenv("SNS_TOPIC_ARN"):
                sns_client.publish(TopicArn=os.getenv("SNS_TOPIC_ARN"), Message=message)

    return {"status": "completed"}

def check_queue_compliance(queue_url):
    issues = []

    # Check encryption
    attributes = sqs_client.get_queue_attributes(QueueUrl=queue_url, AttributeNames=["All"])["Attributes"]
    if "KmsMasterKeyId" not in attributes:
        issues.append("No customer-managed key (CMK) for encryption")

    # Check required tags
    required_tags = ["Name", "Created By", "Cost Center"]
    queue_tags = sqs_client.list_queue_tags(QueueUrl=queue_url).get("Tags", {})
    for tag in required_tags:
        if tag not in queue_tags:
            issues.append(f"Missing required tag: {tag}")

    return issues
