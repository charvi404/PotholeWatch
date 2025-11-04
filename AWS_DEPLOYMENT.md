# AWS Deployment Checklist

## Prerequisites
☐ AWS Account created
☐ AWS CLI installed and configured
☐ Docker installed locally
☐ MongoDB Atlas account (or AWS DocumentDB)

## Step 1: S3 Setup
```bash
# Create S3 bucket for images
aws s3 mb s3://pothole-images-pune --region ap-south-1

# Enable public read access (for image viewing)
aws s3api put-bucket-acl --bucket pothole-images-pune --acl public-read

# Add CORS configuration
aws s3api put-bucket-cors --bucket pothole-images-pune --cors-configuration file://aws/s3-cors.json
```

## Step 2: MongoDB Setup

### Option A: MongoDB Atlas (Free Tier)
1. Visit https://www.mongodb.com/cloud/atlas
2. Create free cluster (512MB)
3. Get connection string
4. Whitelist IP: `0.0.0.0/0` (all IPs)

### Option B: AWS DocumentDB
```bash
aws docdb create-db-cluster \
  --db-cluster-identifier pothole-db \
  --engine docdb \
  --master-username admin \
  --master-user-password YourSecurePassword \
  --region ap-south-1
```

## Step 3: SNS Setup for SMS
```bash
# Create SNS topic
aws sns create-topic --name pothole-alerts --region ap-south-1

# Note the TopicArn from output
# Enable SMS spending limit (to avoid unexpected charges)
aws sns set-sms-attributes \
  --attributes MonthlySpendLimit=10 \
  --region ap-south-1
```

## Step 4: Elastic Beanstalk (Backend Deployment)

### 4.1 Install EB CLI
```bash
pip install awsebcli
```

### 4.2 Initialize EB Application
```bash
cd backend
eb init -p docker pothole-backend --region ap-south-1
```

### 4.3 Create Environment
```bash
eb create pothole-backend-prod \
  --instance-type t2.micro \
  --single
```

### 4.4 Set Environment Variables
```bash
eb setenv \
  MONGO_URL="mongodb+srv://username:password@cluster.mongodb.net/pothole_detection" \
  DB_NAME="pothole_detection" \
  JWT_SECRET="change-this-to-random-secure-string" \
  AWS_ACCESS_KEY_ID="YOUR_ACCESS_KEY" \
  AWS_SECRET_ACCESS_KEY="YOUR_SECRET_KEY" \
  AWS_REGION="ap-south-1" \
  S3_BUCKET="pothole-images-pune" \
  USE_SNS="true" \
  MOCK_SMS="false" \
  USE_LOCAL_STORAGE="false" \
  PHONE_AUTHORITY="+918010303436"
```

### 4.5 Deploy
```bash
eb deploy
```

### 4.6 Get Backend URL
```bash
eb status
# Note the CNAME (your backend URL)
```

## Step 5: Frontend Deployment to S3 + CloudFront

### 5.1 Update Frontend Environment
```bash
cd frontend
# Edit .env.production
REACT_APP_BACKEND_URL=http://pothole-backend-prod.ap-south-1.elasticbeanstalk.com
```

### 5.2 Build Frontend
```bash
yarn build
```

### 5.3 Create S3 Bucket for Frontend
```bash
aws s3 mb s3://pothole-watch-app --region ap-south-1

# Configure for static website hosting
aws s3 website s3://pothole-watch-app \
  --index-document index.html \
  --error-document index.html

# Set bucket policy for public access
aws s3api put-bucket-policy \
  --bucket pothole-watch-app \
  --policy file://aws/s3-bucket-policy.json
```

### 5.4 Upload Build
```bash
aws s3 sync build/ s3://pothole-watch-app --acl public-read
```

### 5.5 Create CloudFront Distribution (Optional but Recommended)
```bash
aws cloudfront create-distribution \
  --origin-domain-name pothole-watch-app.s3.ap-south-1.amazonaws.com \
  --default-root-object index.html

# Note the Distribution Domain Name
```

## Step 6: IAM Permissions

Create IAM role with these policies:
- `AmazonS3FullAccess`
- `AmazonSNSFullAccess`
- `CloudWatchLogsFullAccess`

Attach to EB environment:
```bash
eb config
# Add IAM role under aws:elasticbeanstalk:environment
```

## Step 7: Testing

### Backend Health Check
```bash
curl http://pothole-backend-prod.ap-south-1.elasticbeanstalk.com/api/
# Should return: {"message":"Pothole Detection API","status":"operational"}
```

### Frontend Access
- Direct S3: `http://pothole-watch-app.s3-website.ap-south-1.amazonaws.com`
- CloudFront: `https://d1234567890.cloudfront.net`

### End-to-End Test
1. Sign up as citizen
2. Upload pothole image
3. Check S3 bucket for uploaded image
4. Verify SMS notification (check phone or SNS logs)
5. Sign up as authority
6. View reports and take actions

## Cost Estimation (Free Tier)

### Free Tier Limits (12 months)
- **EC2** (EB): 750 hours/month t2.micro
- **S3**: 5GB storage, 20,000 GET requests, 2,000 PUT requests
- **CloudFront**: 50GB data transfer, 2,000,000 HTTP requests
- **SNS**: 1,000 SMS (India: ₹0.50/SMS - charges apply beyond free tier)
- **DocumentDB**: Not free (use MongoDB Atlas free tier instead)

### Expected Monthly Cost (After Free Tier)
- EB t2.micro: ~$8/month
- S3 Storage (100GB): ~$2.30/month
- Data Transfer: ~$1/month
- SMS (100 messages): ~₹50
- **Total**: ~$15-20/month (excluding SMS)

## Monitoring & Logs

### View EB Logs
```bash
eb logs
```

### CloudWatch Logs
```bash
aws logs tail /aws/elasticbeanstalk/pothole-backend-prod --follow
```

### S3 Usage
```bash
aws s3 ls s3://pothole-images-pune --recursive --summarize
```

## Troubleshooting

### Backend not starting
```bash
eb ssh
sudo docker ps
sudo docker logs <container-id>
```

### Images not uploading to S3
- Check IAM permissions
- Verify S3 bucket name in environment variables
- Check EB logs for boto3 errors

### SMS not sending
- Verify SNS permissions
- Check AWS account SMS spending limit
- Ensure phone number is in E.164 format (+918010303436)

## Security Recommendations

1. **Enable HTTPS**
   - Use AWS Certificate Manager
   - Add HTTPS listener to EB environment
   - Enforce HTTPS redirect

2. **Secure Environment Variables**
   - Use AWS Secrets Manager
   - Rotate JWT secret regularly

3. **Database Security**
   - Enable MongoDB authentication
   - Use IP whitelist
   - Enable encryption at rest

4. **API Rate Limiting**
   - Implement AWS WAF
   - Add rate limiting middleware

5. **Monitoring**
   - Set up CloudWatch alarms
   - Enable AWS CloudTrail
   - Configure SNS alerts for errors

## Backup Strategy

### MongoDB Backup
```bash
# For MongoDB Atlas: Enable automatic backups in dashboard
# Manual backup
mongodump --uri="mongodb+srv://..." --out=/backup/$(date +%Y%m%d)
```

### S3 Versioning
```bash
aws s3api put-bucket-versioning \
  --bucket pothole-images-pune \
  --versioning-configuration Status=Enabled
```

## Scaling Considerations

### Auto Scaling (EB)
```bash
eb scale 2  # Scale to 2 instances

# Configure auto-scaling
eb config
# Set:
# - MinSize: 1
# - MaxSize: 4
# - Triggers: CPUUtilization > 75%
```

### Database Scaling
- MongoDB Atlas: Upgrade cluster tier
- AWS DocumentDB: Increase instance size

## Maintenance

### Update Backend
```bash
cd backend
eb deploy
```

### Update Frontend
```bash
cd frontend
yarn build
aws s3 sync build/ s3://pothole-watch-app --delete

# Invalidate CloudFront cache
aws cloudfront create-invalidation \
  --distribution-id E1234567890ABC \
  --paths "/*"
```

### Model Update
```bash
# Replace best.pt in backend directory
# Redeploy
eb deploy
```

## Cleanup (Delete Resources)

```bash
# Delete EB environment
eb terminate pothole-backend-prod

# Delete S3 buckets
aws s3 rb s3://pothole-images-pune --force
aws s3 rb s3://pothole-watch-app --force

# Delete CloudFront distribution
aws cloudfront delete-distribution --id E1234567890ABC

# Delete SNS topic
aws sns delete-topic --topic-arn arn:aws:sns:ap-south-1:123456789:pothole-alerts
```

---

**Notes:**
- Replace placeholders (username, password, keys) with actual values
- Keep credentials secure and never commit to version control
- Enable MFA for AWS root account
- Regularly review AWS billing dashboard
