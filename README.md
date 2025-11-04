# Smart Pothole Detection & Reporting System — Pune

## Overview

AI-powered full-stack web application for pothole detection and reporting using YOLOv8 model. Citizens can upload pothole images, get instant AI analysis with severity assessment, area calculation, and cost estimates. Authorities receive SMS notifications and can track repair progress through dedicated dashboards.

## Features

### For Citizens
- 📸 Upload pothole images with auto-location detection
- 🤖 AI-powered analysis (YOLOv8) with bounding box visualization
- 📈 Severity assessment (Minor/Moderate/Severe/Critical)
- 📍 Interactive map showing all reported potholes
- 📊 Real-time status tracking (Pending → Reported → Inspected → In Progress → Resolved)
- 💰 Automatic cost estimation and material requirements

### For Authorities
- 📩 SMS notifications for new reports
- 🔍 Filter reports by severity and status
- 📝 Full audit trail with timestamps
- ✅ Action buttons (Dispatch Drone, Mark Inspected, Schedule Repair, Mark Repaired)
- 📊 Statistics dashboard

## Tech Stack

### Backend
- FastAPI (Python 3.11)
- MongoDB (database)
- Ultralytics YOLOv8 (object detection)
- PyTorch (deep learning)
- AWS S3 (image storage)
- AWS SNS (SMS notifications)
- JWT (authentication)

### Frontend
- React 19
- React Leaflet (maps)
- Shadcn/UI (components)
- Tailwind CSS (styling)
- Axios (HTTP client)

### Infrastructure
- Docker & Docker Compose
- AWS Elastic Beanstalk / ECS (deployment)
- AWS S3 + CloudFront (frontend hosting)
- LocalStack (local AWS services mock)

## Prerequisites

- Docker & Docker Compose
- Node.js 18+ and Yarn
- Python 3.11+
- AWS Account (for production deployment)

## Local Development Setup

### 1. Clone Repository

```bash
git clone <repository-url>
cd pothole-detection
```

### 2. Backend Setup

```bash
cd backend

# Create virtual environment (optional)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Ensure best.pt model is in backend directory
ls best.pt  # Should exist

# Configure environment
cp .env.example .env  # If you have example
# Edit .env with your settings
```

**Backend .env Configuration:**

```env
MONGO_URL="mongodb://localhost:27017"
DB_NAME="pothole_detection"
CORS_ORIGINS="*"
JWT_SECRET="your-super-secret-jwt-key-change-in-production"

# AWS Configuration (for S3, SNS)
AWS_ACCESS_KEY_ID=""
AWS_SECRET_ACCESS_KEY=""
AWS_REGION="ap-south-1"
S3_BUCKET="pothole-images-bucket"

# For local development with LocalStack
AWS_ENDPOINT_URL="http://localhost:4566"

# SMS Configuration
USE_SNS="false"  # Set to true when using real AWS SNS
MOCK_SMS="true"   # Set to false in production
PHONE_AUTHORITY="+918010303436"

# Storage (true for local, false for S3)
USE_LOCAL_STORAGE="true"
```

### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
yarn install

# Frontend .env is already configured
# REACT_APP_BACKEND_URL should point to your backend
```

### 4. Run with Docker Compose (Recommended)

This starts MongoDB, LocalStack (AWS mock), and Backend:

```bash
# From project root
docker-compose up --build
```

Services:
- MongoDB: `localhost:27017`
- Backend API: `localhost:8001`
- LocalStack (AWS): `localhost:4566`

### 5. Run Frontend (Separate Terminal)

```bash
cd frontend
yarn start
```

Frontend: `http://localhost:3000`

### 6. Test the Application

1. **Sign Up**: Create a citizen account at `/auth`
2. **Upload Image**: Upload a pothole image with location
3. **View Analysis**: See AI detection results
4. **Notify Authorities**: Send SMS notification
5. **Authority Login**: Create an authority account
6. **Manage Reports**: View and update pothole status

## Model Details

### YOLO Model (`best.pt`)

- **Model**: YOLOv8 trained for pothole detection
- **Input**: Images (any resolution)
- **Output**: Bounding boxes with confidence scores
- **Processing**: 
  - Detects all potholes in image
  - Calculates pixel area for each detection
  - Converts to real-world area (m²) using heuristic
  - Aggregates total area and count

### Area Calculation Heuristic

```python
# Assumes camera at ~1.5m height capturing ~3.5m wide lane
LANE_WIDTH_M = 3.5
meters_per_pixel = LANE_WIDTH_M / image_width_pixels

area_m2 = bbox_width_px * bbox_height_px * (meters_per_pixel ** 2)
```

### Severity Thresholds

- **Minor**: < 0.2 m²
- **Moderate**: 0.2 - 0.5 m²
- **Severe**: 0.5 - 1.0 m²
- **Critical**: > 1.0 m²

### Material & Cost Estimation

| Severity | Material | Cost/Bag (₹) | Coverage (m²/bag) |
|----------|----------|-------------|-------------------|
| Minor | Cold Patch Asphalt | 350 | 0.15 |
| Moderate | Cold Mix Asphalt | 480 | 0.12 |
| Severe | Hot Mix Asphalt | 650 | 0.10 |
| Critical | Premium Hot Mix | 850 | 0.08 |

## API Endpoints

### Authentication

```bash
# Sign Up
POST /api/auth/signup
Body: { "name": "John", "email": "john@example.com", "password": "pass123", "role": "citizen" }

# Login
POST /api/auth/login
Body: { "email": "john@example.com", "password": "pass123" }
Returns: { "user": {...}, "token": "jwt-token" }
```

### Pothole Operations

```bash
# Analyze Pothole
POST /api/potholes/analyze
Headers: Authorization: Bearer <token>
Form-data:
  - image: <file>
  - location: "FC Road, Pune"
  - coordinates: {"lat": 18.5204, "lng": 73.8567}

# Get All Potholes
GET /api/potholes?status=Pending&severity=Critical
Headers: Authorization: Bearer <token>

# Get Pothole by ID
GET /api/potholes/{id}
Headers: Authorization: Bearer <token>

# Notify Authorities
POST /api/potholes/{id}/notify
Headers: Authorization: Bearer <token>

# Authority Action
POST /api/potholes/{id}/action
Headers: Authorization: Bearer <token>
Body: { "action": "schedule_repair", "notes": "Repair scheduled for tomorrow" }

# Get User Reports
GET /api/users/{userId}/reports
Headers: Authorization: Bearer <token>

# Get Notifications (Authority only)
GET /api/notifications
Headers: Authorization: Bearer <token>
```

## AWS Deployment Guide

### Prerequisites

1. AWS Account with Free Tier
2. AWS CLI installed and configured
3. Docker installed locally

### Step 1: Create S3 Bucket for Images

```bash
# Create bucket
aws s3 mb s3://pothole-images-pune --region ap-south-1

# Enable CORS
aws s3api put-bucket-cors --bucket pothole-images-pune --cors-configuration file://cors.json
```

**cors.json:**
```json
{
  "CORSRules": [
    {
      "AllowedOrigins": ["*"],
      "AllowedMethods": ["GET", "POST", "PUT"],
      "AllowedHeaders": ["*"]
    }
  ]
}
```

### Step 2: Setup MongoDB Atlas (Managed MongoDB)

1. Go to https://www.mongodb.com/cloud/atlas
2. Create free cluster
3. Get connection string: `mongodb+srv://username:password@cluster.mongodb.net/pothole_detection`

### Step 3: Configure AWS SNS for SMS

```bash
# Create SNS topic
aws sns create-topic --name pothole-alerts --region ap-south-1

# Note the TopicArn
```

### Step 4: Deploy Backend to Elastic Beanstalk

```bash
# Initialize EB
cd backend
eb init -p docker pothole-backend --region ap-south-1

# Create environment
eb create pothole-backend-env

# Set environment variables
eb setenv \
  MONGO_URL="mongodb+srv://..." \
  DB_NAME="pothole_detection" \
  JWT_SECRET="your-production-secret" \
  AWS_ACCESS_KEY_ID="<your-key>" \
  AWS_SECRET_ACCESS_KEY="<your-secret>" \
  AWS_REGION="ap-south-1" \
  S3_BUCKET="pothole-images-pune" \
  USE_SNS="true" \
  MOCK_SMS="false" \
  USE_LOCAL_STORAGE="false" \
  PHONE_AUTHORITY="+918010303436"

# Deploy
eb deploy

# Get URL
eb status
```

### Step 5: Deploy Frontend to S3 + CloudFront

```bash
cd frontend

# Update REACT_APP_BACKEND_URL in .env to your EB URL
REACT_APP_BACKEND_URL=http://pothole-backend-env.ap-south-1.elasticbeanstalk.com

# Build
yarn build

# Create S3 bucket for frontend
aws s3 mb s3://pothole-watch-frontend --region ap-south-1

# Enable static website hosting
aws s3 website s3://pothole-watch-frontend --index-document index.html

# Upload build
aws s3 sync build/ s3://pothole-watch-frontend --acl public-read

# Create CloudFront distribution (optional)
aws cloudfront create-distribution --origin-domain-name pothole-watch-frontend.s3.ap-south-1.amazonaws.com
```

### Step 6: IAM Permissions

Create IAM role for EB with these policies:
- `AmazonS3FullAccess`
- `AmazonSNSFullAccess`
- `CloudWatchLogsFullAccess`

### Cost Estimate (Free Tier)

- **S3**: 5GB free (enough for ~5000 images)
- **Elastic Beanstalk**: 1 t2.micro instance free (750 hours/month)
- **CloudFront**: 50GB free data transfer
- **MongoDB Atlas**: 512MB free
- **SNS SMS**: ₹0.50/SMS (charges apply)

## Testing

### Backend Tests

```bash
cd backend
pytest tests/
```

### Frontend Tests

```bash
cd frontend
yarn test
```

### Manual Testing

```bash
# Test pothole analysis
curl -X POST http://localhost:8001/api/potholes/analyze \
  -H "Authorization: Bearer <token>" \
  -F "image=@test_pothole.jpg" \
  -F "location=Test Road" \
  -F 'coordinates={"lat":18.5204,"lng":73.8567}'
```

## Troubleshooting

### Model not loading

```bash
# Check if best.pt exists
ls backend/best.pt

# Check logs
docker-compose logs backend
```

### MongoDB connection issues

```bash
# Check MongoDB is running
docker-compose ps mongo

# Connect to MongoDB shell
docker exec -it pothole_mongo mongosh
```

### Frontend can't reach backend

- Verify `REACT_APP_BACKEND_URL` in frontend/.env
- Check CORS settings in backend
- Ensure backend is running on correct port

## Project Structure

```
pothole-detection/
├── backend/
│   ├── server.py           # FastAPI app
│   ├── best.pt             # YOLO model
│   ├── requirements.txt    # Python dependencies
│   ├── Dockerfile          # Backend container
│   ├── .env                # Environment variables
│   └── uploads/            # Uploaded images
├── frontend/
│   ├── src/
│   │   ├── pages/          # React pages
│   │   ├── components/     # UI components
│   │   ├── services/       # API client
│   │   ├── App.js          # Main component
│   │   └── App.css         # Styles
│   ├── package.json        # Node dependencies
│   └── .env                # Frontend env vars
├── docker-compose.yml      # Local dev setup
└── README.md               # This file
```

## Security Notes

1. **Change JWT Secret**: Update `JWT_SECRET` in production
2. **Use HTTPS**: Deploy with SSL/TLS certificates
3. **Secure AWS Keys**: Use AWS Secrets Manager or IAM roles
4. **Input Validation**: All user inputs are validated
5. **Rate Limiting**: Consider adding rate limiting in production

## Future Enhancements

- [ ] Real-time drone video analysis
- [ ] Mobile app (React Native)
- [ ] Public dashboard with analytics
- [ ] Email notifications
- [ ] Multi-language support
- [ ] Export reports as PDF
- [ ] Integration with municipal systems

## License

MIT License

## Contributors

Developed for Smart City Initiative - Pune

## Support

For issues and questions:
- GitHub Issues: <repository-url>/issues
- Email: support@potholewatch.in

---

**Made with ❤️ for safer roads**
