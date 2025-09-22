# AWS Deployment Guide

## Using Locally Indexed Files on AWS

Yes, you can absolutely use your locally indexed files when deploying to AWS! The system stores all indexes and metadata in the `regulatory_storage/` directory, which is completely portable.

## Deployment Strategies

### Option 1: Direct File Transfer (Recommended for Small Datasets)

#### Step 1: Prepare Your Local Files
```bash
# Your local directory structure should look like:
regulatory-tracker/
├── llamindex/                    # Your Python modules
├── downloads/                    # Downloaded PDFs
├── regulatory_storage/          # ← This is what you'll transfer
│   ├── nodes/                   # Document nodes
│   ├── vector_indexes/          # Vector search indexes
│   ├── summary_indexes/         # Summary indexes
│   ├── metadata/               # Index metadata
│   └── chroma_db/              # ChromaDB vector store
├── cache/                      # Ingestion cache
└── embeddings_cache/           # Embedding model cache
```

#### Step 2: Transfer to AWS
```bash
# Option A: Using S3 (Recommended)
aws s3 sync regulatory_storage/ s3://your-bucket/regulatory_storage/

# Option B: Using scp
scp -r regulatory_storage/ ec2-user@your-ec2-instance:/path/to/app/

# Option C: Using rsync
rsync -avz regulatory_storage/ ec2-user@your-ec2-instance:/path/to/app/
```

#### Step 3: Deploy Application
```bash
# Transfer your application code
scp -r llamindex/ ec2-user@your-ec2-instance:/path/to/app/
scp requirements.txt .env ec2-user@your-ec2-instance:/path/to/app/
```

#### Step 4: Setup on AWS
```bash
# On your AWS instance
cd /path/to/app
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Your indexes are ready to use!
python llamindex/regulatory_tool_calling_test.py
```

### Option 2: S3-Based Storage (Recommended for Production)

#### Step 1: Modify Storage Manager for S3
```python
# llamindex/s3_storage_manager.py
import boto3
import os
from storage_manager import StorageManager

class S3StorageManager(StorageManager):
    def __init__(self, base_dir: str = "./regulatory_storage", s3_bucket: str = None):
        super().__init__(base_dir)
        self.s3_bucket = s3_bucket
        self.s3_client = boto3.client('s3') if s3_bucket else None
    
    def sync_to_s3(self):
        """Sync local storage to S3"""
        if not self.s3_bucket:
            return
        
        for root, dirs, files in os.walk(self.base_dir):
            for file in files:
                local_path = os.path.join(root, file)
                s3_key = os.path.relpath(local_path, self.base_dir)
                self.s3_client.upload_file(local_path, self.s3_bucket, f"regulatory_storage/{s3_key}")
    
    def sync_from_s3(self):
        """Sync S3 storage to local"""
        if not self.s3_bucket:
            return
        
        paginator = self.s3_client.get_paginator('list_objects_v2')
        for page in paginator.paginate(Bucket=self.s3_bucket, Prefix="regulatory_storage/"):
            for obj in page.get('Contents', []):
                s3_key = obj['Key']
                local_path = os.path.join(self.base_dir, s3_key.replace("regulatory_storage/", ""))
                os.makedirs(os.path.dirname(local_path), exist_ok=True)
                self.s3_client.download_file(self.s3_bucket, s3_key, local_path)
```

#### Step 2: Update Your Application
```python
# In your deployment scripts
from s3_storage_manager import S3StorageManager

# Initialize with S3
storage = S3StorageManager(
    base_dir="./regulatory_storage",
    s3_bucket="your-regulatory-bucket"
)

# Sync from S3 on startup
storage.sync_from_s3()
```

### Option 3: Containerized Deployment

#### Step 1: Create Dockerfile
```dockerfile
# Dockerfile
FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY llamindex/ ./llamindex/
COPY .env .

# Copy pre-built indexes (if using Option 1)
COPY regulatory_storage/ ./regulatory_storage/

# Create necessary directories
RUN mkdir -p downloads cache embeddings_cache

EXPOSE 8000

CMD ["python", "llamindex/your_app.py"]
```

#### Step 2: Build and Deploy
```bash
# Build image
docker build -t regulatory-tracker .

# Run container
docker run -p 8000:8000 \
  -e AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID \
  -e AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY \
  regulatory-tracker
```

## AWS Service Recommendations

### For Different Use Cases

#### 1. **EC2** (Simple, Cost-Effective)
```bash
# Launch EC2 instance
aws ec2 run-instances \
  --image-id ami-0c02fb55956c7d316 \
  --instance-type t3.medium \
  --key-name your-key-pair \
  --security-group-ids sg-xxxxxxxxx
```

#### 2. **ECS/Fargate** (Containerized, Scalable)
```yaml
# task-definition.json
{
  "family": "regulatory-tracker",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "executionRoleArn": "arn:aws:iam::account:role/ecsTaskExecutionRole",
  "containerDefinitions": [
    {
      "name": "regulatory-tracker",
      "image": "your-account.dkr.ecr.region.amazonaws.com/regulatory-tracker:latest",
      "portMappings": [{"containerPort": 8000}],
      "environment": [
        {"name": "AWS_ACCESS_KEY_ID", "value": "your-key"},
        {"name": "AWS_SECRET_ACCESS_KEY", "value": "your-secret"}
      ]
    }
  ]
}
```

#### 3. **Lambda** (Serverless, Event-Driven)
```python
# lambda_function.py
import json
from llamindex.storage_manager import StorageManager
from llamindex.ingestion import extract_nodes_from_pdf
from llamindex.index_builders import build_tools_for_document

def lambda_handler(event, context):
    # Load pre-built indexes from S3
    storage = StorageManager(base_dir="/tmp/regulatory_storage")
    
    # Your RAG logic here
    return {
        'statusCode': 200,
        'body': json.dumps('Hello from Lambda!')
    }
```

## Storage Considerations

### S3 Bucket Setup
```bash
# Create S3 bucket for indexes
aws s3 mb s3://your-regulatory-indexes-bucket

# Set up lifecycle policy (optional)
aws s3api put-bucket-lifecycle-configuration \
  --bucket your-regulatory-indexes-bucket \
  --lifecycle-configuration file://lifecycle-policy.json
```

### EBS Volume (for EC2)
```bash
# Create EBS volume for persistent storage
aws ec2 create-volume \
  --size 100 \
  --availability-zone us-east-1a \
  --volume-type gp3 \
  --tag-specifications 'ResourceType=volume,Tags=[{Key=Name,Value=regulatory-indexes}]'
```

## Performance Optimization

### 1. **Use EBS-Optimized Instances**
- Choose instances with EBS optimization for better I/O
- Consider `i3` instances for high I/O workloads

### 2. **S3 Transfer Acceleration**
```bash
# Enable transfer acceleration
aws s3api put-bucket-accelerate-configuration \
  --bucket your-bucket \
  --accelerate-configuration Status=Enabled
```

### 3. **CloudFront for Global Access**
```bash
# Create CloudFront distribution for global access
aws cloudfront create-distribution \
  --distribution-config file://cloudfront-config.json
```

## Cost Optimization

### 1. **Spot Instances** (for non-critical workloads)
```bash
aws ec2 request-spot-instances \
  --spot-price "0.05" \
  --instance-count 1 \
  --type "one-time" \
  --launch-specification file://spot-specification.json
```

### 2. **S3 Intelligent Tiering**
```bash
# Enable intelligent tiering
aws s3api put-bucket-intelligent-tiering-configuration \
  --bucket your-bucket \
  --id "regulatory-indexes" \
  --intelligent-tiering-configuration file://tiering-config.json
```

## Security Best Practices

### 1. **IAM Roles** (instead of access keys)
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::your-regulatory-bucket",
        "arn:aws:s3:::your-regulatory-bucket/*"
      ]
    }
  ]
}
```

### 2. **VPC Configuration**
- Use private subnets for your application
- Configure security groups to restrict access
- Use NAT Gateway for outbound internet access

## Monitoring and Logging

### 1. **CloudWatch Logs**
```python
import logging
import boto3

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Your application logs will automatically go to CloudWatch
logger.info("Processing regulatory document: %s", document_name)
```

### 2. **CloudWatch Metrics**
```python
import boto3

cloudwatch = boto3.client('cloudwatch')

# Send custom metrics
cloudwatch.put_metric_data(
    Namespace='RegulatoryTracker',
    MetricData=[
        {
            'MetricName': 'DocumentsProcessed',
            'Value': 1,
            'Unit': 'Count'
        }
    ]
)
```

## Quick Deployment Checklist

- [ ] Transfer `regulatory_storage/` to AWS
- [ ] Set up environment variables
- [ ] Install dependencies
- [ ] Configure IAM roles/permissions
- [ ] Set up monitoring and logging
- [ ] Test the application
- [ ] Configure auto-scaling (if needed)
- [ ] Set up backup strategy

Your locally indexed files will work seamlessly on AWS with minimal configuration changes! 