# UWSS Cloud Deployment Script
# This script prepares and deploys the UWSS system to AWS ECS

param(
    [string]$Region = "ap-southeast-1",
    [string]$Cluster = "uwss-cluster",
    [string]$TaskFamily = "uwss-task"
)

Write-Host "🚀 Starting UWSS Cloud Deployment..." -ForegroundColor Green

# Set environment variables
$env:AWS_DEFAULT_REGION = $Region
$BUCKET = "uwss-data-duynguyen"
$ECR_URI = "167004608161.dkr.ecr.$Region.amazonaws.com"
$REPO = "uwss"

# Step 1: Build and push Docker image
Write-Host "📦 Building and pushing Docker image..." -ForegroundColor Yellow
docker build -t uwss:latest .
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Docker build failed!" -ForegroundColor Red
    exit 1
}

docker tag uwss:latest "$ECR_URI/$REPO:latest"
aws ecr get-login-password --region $Region | docker login --username AWS --password-stdin $ECR_URI
docker push "$ECR_URI/$REPO:latest"

# Step 2: Create task definition
Write-Host "📋 Creating ECS task definition..." -ForegroundColor Yellow
$TASK_DEFINITION = @"
{
    "family": "$TaskFamily",
    "networkMode": "awsvpc",
    "requiresCompatibilities": ["FARGATE"],
    "cpu": "1024",
    "memory": "2048",
    "executionRoleArn": "arn:aws:iam::167004608161:role/uwssEcsTaskExecutionRole",
    "taskRoleArn": "arn:aws:iam::167004608161:role/uwssTaskRole",
    "containerDefinitions": [
        {
            "name": "uwss",
            "image": "$ECR_URI/$REPO:latest",
            "command": [
                "python", "-m", "src.uwss.cli", "export",
                "--db", "data/uwss.sqlite",
                "--out", "s3://$BUCKET/exports/candidates_cloud.jsonl",
                "--min-score", "0.05",
                "--year-min", "1995",
                "--sort", "relevance",
                "--skip-missing-core",
                "--include-provenance"
            ],
            "environment": [
                {"name": "UWSS_CONTACT_EMAIL", "value": "ddnguyen@go.olemiss.edu"},
                {"name": "USER_AGENT", "value": "UWSS/0.1 (contact: ddnguyen@go.olemiss.edu)"},
                {"name": "UWSS_THROTTLE_SEC", "value": "0.5"},
                {"name": "UWSS_JITTER_SEC", "value": "0.2"}
            ],
            "logConfiguration": {
                "logDriver": "awslogs",
                "options": {
                    "awslogs-group": "/ecs/uwss",
                    "awslogs-region": "$Region",
                    "awslogs-stream-prefix": "uwss"
                }
            },
            "healthCheck": {
                "command": ["CMD-SHELL", "python -c 'import sys; sys.exit(0)'"],
                "interval": 30,
                "timeout": 5,
                "retries": 3,
                "startPeriod": 60
            }
        }
    ]
}
"@

$TASK_DEFINITION | Out-File -FilePath "$env:TEMP\uwss-task-cloud.json" -Encoding UTF8
aws ecs register-task-definition --cli-input-json file://$env:TEMP/uwss-task-cloud.json --region $Region

# Step 3: Get network configuration
Write-Host "🌐 Configuring network..." -ForegroundColor Yellow
$VPC = aws ec2 describe-vpcs --filters Name=isDefault,Values=true --query "Vpcs[0].VpcId" --output text --region $Region
$SUBNETS = aws ec2 describe-subnets --filters Name=vpc-id,Values=$VPC --query "Subnets[].SubnetId" --output text --region $Region
$SUBNET_LIST = $SUBNETS -split "\s+"
$SUBNET1 = $SUBNET_LIST[0]
$SUBNET2 = $SUBNET_LIST[1]
$SG_ID = aws ec2 describe-security-groups --filters Name=group-name,Values=uwss-ecs-sg Name=vpc-id,Values=$VPC --query "SecurityGroups[0].GroupId" --output text --region $Region

# Step 4: Run ECS task
Write-Host "🚀 Running ECS task..." -ForegroundColor Yellow
aws ecs run-task `
    --cluster $Cluster `
    --task-definition $TaskFamily `
    --launch-type FARGATE `
    --network-configuration "awsvpcConfiguration={subnets=[$SUBNET1,$SUBNET2],securityGroups=[$SG_ID],assignPublicIp=ENABLED}" `
    --region $Region

Write-Host "✅ Cloud deployment initiated!" -ForegroundColor Green
Write-Host "📊 Monitor logs: aws logs describe-log-groups --region $Region" -ForegroundColor Cyan
Write-Host "📁 Check S3: aws s3 ls s3://$BUCKET/exports/ --region $Region" -ForegroundColor Cyan
