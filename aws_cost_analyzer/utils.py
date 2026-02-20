"""
Shared utility functions for AWS Cost Analyzer
"""


def clean_service_name(service_name, max_length=16):
    """Clean and abbreviate AWS service names for better readability"""
    name = service_name

    # Remove redundant prefixes
    name = name.replace("Amazon ", "").replace("AWS ", "")

    # Common AWS service abbreviations that are still readable
    name = name.replace("Elastic Compute Cloud", "EC2")
    name = name.replace("Relational Database Service", "RDS")
    name = name.replace("Simple Storage Service", "S3")
    name = name.replace("Elastic Load Balancing", "ELB")
    name = name.replace("Virtual Private Cloud", "VPC")
    name = name.replace("CloudFormation", "CFN")
    name = name.replace("Application Load Balancer", "ALB")
    name = name.replace("Network Load Balancer", "NLB")
    name = name.replace("Elastic Container Service", "ECS")
    name = name.replace("Elastic Kubernetes Service", "EKS")
    name = name.replace("Route 53", "Route53")
    name = name.replace("Simple Queue Service", "SQS")
    name = name.replace("Simple Notification Service", "SNS")

    # Truncate if still too long, but keep it readable
    if len(name) > max_length:
        name = name[: max_length - 3] + "..."

    return name
