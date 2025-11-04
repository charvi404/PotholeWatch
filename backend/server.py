from fastapi import FastAPI, APIRouter, File, UploadFile, Form, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, timedelta
from passlib.context import CryptContext
import jwt
import boto3
from botocore.config import Config
from ultralytics import YOLO
import cv2
import numpy as np
from PIL import Image
import io
import json

# Load environment variables
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Constants
JWT_SECRET = os.environ.get('JWT_SECRET', 'your-secret-key-change-in-production')
JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_HOURS = 24

# AWS Configuration
AWS_REGION = os.environ.get('AWS_REGION', 'ap-south-1')
S3_BUCKET = os.environ.get('S3_BUCKET', 'pothole-images-bucket')
USE_SNS = os.environ.get('USE_SNS', 'false').lower() == 'true'
MOCK_SMS = os.environ.get('MOCK_SMS', 'true').lower() == 'true'
PHONE_AUTHORITY = os.environ.get('PHONE_AUTHORITY', '+918010303436')
LOCAL_STORAGE = os.environ.get('USE_LOCAL_STORAGE', 'true').lower() == 'true'

# Setup AWS clients
if not LOCAL_STORAGE:
    aws_config = Config(region_name=AWS_REGION)
    s3_client = boto3.client('s3', config=aws_config,
                            endpoint_url=os.environ.get('AWS_ENDPOINT_URL'),
                            aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
                            aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'))
    if USE_SNS:
        sns_client = boto3.client('sns', config=aws_config,
                                 endpoint_url=os.environ.get('AWS_ENDPOINT_URL'),
                                 aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
                                 aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'))

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Security
security = HTTPBearer()

# Create FastAPI app
app = FastAPI()
api_router = APIRouter(prefix="/api")

# Ensure uploads directory exists
UPLOADS_DIR = ROOT_DIR / 'uploads'
UPLOADS_DIR.mkdir(exist_ok=True)

# Load YOLO model at startup
MODEL_PATH = ROOT_DIR / 'best.pt'
model = None

def load_model():
    global model
    try:
        if MODEL_PATH.exists():
            model = YOLO(str(MODEL_PATH))
            logger.info("YOLO model loaded successfully")
        else:
            logger.warning(f"Model file not found at {MODEL_PATH}")
    except Exception as e:
        logger.error(f"Error loading model: {e}")

# Pricing table
MATERIAL_PRICING = {
    'Minor': {'material': 'Cold Patch Asphalt', 'cost_per_bag': 350, 'coverage_m2': 0.15},
    'Moderate': {'material': 'Cold Mix Asphalt', 'cost_per_bag': 480, 'coverage_m2': 0.12},
    'Severe': {'material': 'Hot Mix Asphalt', 'cost_per_bag': 650, 'coverage_m2': 0.10},
    'Critical': {'material': 'Premium Hot Mix Asphalt', 'cost_per_bag': 850, 'coverage_m2': 0.08}
}

# Pydantic Models
class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: str = 'citizen'  # 'citizen' or 'authority'

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class User(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    name: str
    email: str
    role: str
    created_at: str

class AuditEntry(BaseModel):
    action: str
    actor_id: Optional[str] = None
    actor_role: Optional[str] = None
    notes: Optional[str] = None
    timestamp: str

class Pothole(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    user_id: str
    image_url: str
    s3_url: Optional[str] = None
    processed_image_url: Optional[str] = None
    location: str
    coordinates: Dict[str, float]
    pothole_count: int
    total_area_m2: float
    severity: str
    material: str
    bags_required: int
    estimated_cost_inr: float
    confidence: float
    status: str = 'Pending'
    audit: List[Dict[str, Any]]
    created_at: str
    updated_at: str

class PotholeAction(BaseModel):
    action: str
    notes: Optional[str] = None

class Notification(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    pothole_id: str
    message: str
    phone_number: str
    status: str
    created_at: str

# Helper Functions
def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(user_id: str, email: str, role: str) -> str:
    payload = {
        'user_id': user_id,
        'email': email,
        'role': role,
        'exp': datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    try:
        token = credentials.credentials
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

def calculate_severity(total_area_m2: float) -> str:
    """Determine severity based on total pothole area"""
    if total_area_m2 < 0.2:
        return 'Minor'
    elif total_area_m2 < 0.5:
        return 'Moderate'
    elif total_area_m2 < 1.0:
        return 'Severe'
    else:
        return 'Critical'

def estimate_cost(severity: str, total_area_m2: float) -> tuple:
    """Estimate repair material and cost"""
    pricing = MATERIAL_PRICING[severity]
    bags_required = max(1, int(np.ceil(total_area_m2 / pricing['coverage_m2'])))
    estimated_cost = bags_required * pricing['cost_per_bag']
    return pricing['material'], bags_required, estimated_cost

async def upload_to_s3(file_path: Path, key: str) -> str:
    """Upload file to S3 and return URL"""
    if LOCAL_STORAGE:
        return f"/uploads/{key}"
    try:
        s3_client.upload_file(str(file_path), S3_BUCKET, key)
        return f"https://{S3_BUCKET}.s3.{AWS_REGION}.amazonaws.com/{key}"
    except Exception as e:
        logger.error(f"S3 upload error: {e}")
        return f"/uploads/{key}"

async def send_sms(phone_number: str, message: str) -> dict:
    """Send SMS via SNS or log if in mock mode"""
    notification_id = str(uuid.uuid4())
    
    if MOCK_SMS:
        logger.info(f"[MOCK SMS] To: {phone_number}, Message: {message}")
        notification = {
            'id': notification_id,
            'phone_number': phone_number,
            'message': message,
            'status': 'mocked',
            'created_at': datetime.now(timezone.utc).isoformat()
        }
    else:
        try:
            response = sns_client.publish(
                PhoneNumber=phone_number,
                Message=message
            )
            notification = {
                'id': notification_id,
                'phone_number': phone_number,
                'message': message,
                'status': 'sent',
                'message_id': response.get('MessageId'),
                'created_at': datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            logger.error(f"SMS send error: {e}")
            notification = {
                'id': notification_id,
                'phone_number': phone_number,
                'message': message,
                'status': 'failed',
                'error': str(e),
                'created_at': datetime.now(timezone.utc).isoformat()
            }
    
    await db.notifications.insert_one(notification)
    return notification

def process_detections(image_path: str) -> dict:
    """Run YOLO inference and calculate aggregated metrics"""
    if model is None:
        raise HTTPException(status_code=500, detail="Model not loaded")
    
    # Run inference
    results = model.predict(source=image_path, conf=0.25)
    result = results[0]
    
    if len(result.boxes) == 0:
        return {
            'pothole_count': 0,
            'total_area_m2': 0.0,
            'confidence': 0.0,
            'detections': []
        }
    
    # Load image to get dimensions
    img = cv2.imread(image_path)
    img_height, img_width = img.shape[:2]
    
    # Heuristic: Assume camera at ~1.5m height capturing ~3.5m wide lane
    # meters_per_pixel = lane_width_m / image_width_px
    LANE_WIDTH_M = 3.5
    meters_per_pixel_x = LANE_WIDTH_M / img_width
    meters_per_pixel_y = meters_per_pixel_x  # Assuming square pixels
    
    detections = []
    total_area_px = 0
    confidence_sum = 0
    
    # Process all detections
    for box in result.boxes:
        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
        conf = float(box.conf[0].cpu().numpy())
        
        # Calculate pixel area
        width_px = x2 - x1
        height_px = y2 - y1
        area_px = width_px * height_px
        
        # Convert to real-world area (m²)
        width_m = width_px * meters_per_pixel_x
        height_m = height_px * meters_per_pixel_y
        area_m2 = width_m * height_m
        
        detections.append({
            'bbox': [float(x1), float(y1), float(x2), float(y2)],
            'confidence': conf,
            'area_px': float(area_px),
            'area_m2': float(area_m2)
        })
        
        total_area_px += area_px
        confidence_sum += conf
    
    pothole_count = len(detections)
    avg_confidence = confidence_sum / pothole_count if pothole_count > 0 else 0
    total_area_m2 = sum(d['area_m2'] for d in detections)
    
    # Draw bounding boxes on image
    for det in detections:
        x1, y1, x2, y2 = det['bbox']
        cv2.rectangle(img, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
        cv2.putText(img, f"{det['confidence']:.2f}", (int(x1), int(y1)-5),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
    
    # Save processed image
    processed_path = Path(image_path).parent / f"processed_{Path(image_path).name}"
    cv2.imwrite(str(processed_path), img)
    
    return {
        'pothole_count': pothole_count,
        'total_area_m2': round(total_area_m2, 2),
        'confidence': round(avg_confidence * 100, 1),
        'detections': detections,
        'processed_image_path': str(processed_path)
    }

# API Endpoints
@api_router.get("/")
async def root():
    return {"message": "Pothole Detection API", "status": "operational"}

@api_router.post("/auth/signup")
async def signup(user_data: UserCreate):
    # Check if user exists
    existing_user = await db.users.find_one({'email': user_data.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create user
    user_id = str(uuid.uuid4())
    hashed_pwd = hash_password(user_data.password)
    
    user_doc = {
        'id': user_id,
        'name': user_data.name,
        'email': user_data.email,
        'password': hashed_pwd,
        'role': user_data.role,
        'created_at': datetime.now(timezone.utc).isoformat()
    }
    
    await db.users.insert_one(user_doc)
    
    # Generate token
    token = create_access_token(user_id, user_data.email, user_data.role)
    
    return {
        'user': {
            'id': user_id,
            'name': user_data.name,
            'email': user_data.email,
            'role': user_data.role
        },
        'token': token
    }

@api_router.post("/auth/login")
async def login(credentials: UserLogin):
    user = await db.users.find_one({'email': credentials.email})
    if not user or not verify_password(credentials.password, user['password']):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = create_access_token(user['id'], user['email'], user['role'])
    
    return {
        'user': {
            'id': user['id'],
            'name': user['name'],
            'email': user['email'],
            'role': user['role']
        },
        'token': token
    }

@api_router.post("/potholes/analyze")
async def analyze_pothole(
    image: UploadFile = File(...),
    location: str = Form(...),
    coordinates: str = Form(...),
    current_user: dict = Depends(get_current_user)
):
    try:
        # Parse coordinates
        coords = json.loads(coordinates)
        
        # Save uploaded image
        image_id = str(uuid.uuid4())
        file_ext = Path(image.filename).suffix
        filename = f"{image_id}{file_ext}"
        file_path = UPLOADS_DIR / filename
        
        with open(file_path, 'wb') as f:
            content = await image.read()
            f.write(content)
        
        # Process with YOLO
        detection_result = process_detections(str(file_path))
        
        # Calculate severity and cost
        severity = calculate_severity(detection_result['total_area_m2'])
        material, bags_required, estimated_cost = estimate_cost(severity, detection_result['total_area_m2'])
        
        # Upload to S3
        image_url = await upload_to_s3(file_path, filename)
        
        processed_filename = f"processed_{filename}"
        processed_image_url = None
        if detection_result.get('processed_image_path'):
            processed_image_url = await upload_to_s3(
                Path(detection_result['processed_image_path']),
                processed_filename
            )
        
        # Create pothole record
        pothole_id = str(uuid.uuid4())
        pothole_doc = {
            'id': pothole_id,
            'user_id': current_user['user_id'],
            'image_url': image_url,
            's3_url': image_url if not LOCAL_STORAGE else None,
            'processed_image_url': processed_image_url,
            'location': location,
            'coordinates': coords,
            'pothole_count': detection_result['pothole_count'],
            'total_area_m2': detection_result['total_area_m2'],
            'severity': severity,
            'material': material,
            'bags_required': bags_required,
            'estimated_cost_inr': estimated_cost,
            'confidence': detection_result['confidence'],
            'status': 'Pending',
            'audit': [{
                'action': 'uploaded',
                'actor_id': current_user['user_id'],
                'actor_role': current_user['role'],
                'timestamp': datetime.now(timezone.utc).isoformat()
            }],
            'created_at': datetime.now(timezone.utc).isoformat(),
            'updated_at': datetime.now(timezone.utc).isoformat()
        }
        
        await db.potholes.insert_one(pothole_doc)
        
        return {
            'id': pothole_id,
            'severity': severity,
            'total_area_m2': detection_result['total_area_m2'],
            'pothole_count': detection_result['pothole_count'],
            'material': material,
            'bags_required': bags_required,
            'estimated_cost_inr': estimated_cost,
            'confidence': detection_result['confidence'],
            'image_url': image_url,
            'processed_image_url': processed_image_url,
            'location': location,
            'coordinates': coords,
            'created_at': pothole_doc['created_at']
        }
        
    except Exception as e:
        logger.error(f"Analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/potholes")
async def get_potholes(
    status: Optional[str] = None,
    severity: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    query = {}
    if status:
        query['status'] = status
    if severity:
        query['severity'] = severity
    
    potholes = await db.potholes.find(query, {'_id': 0}).sort('created_at', -1).to_list(1000)
    return potholes

@api_router.get("/potholes/{pothole_id}")
async def get_pothole(pothole_id: str, current_user: dict = Depends(get_current_user)):
    pothole = await db.potholes.find_one({'id': pothole_id}, {'_id': 0})
    if not pothole:
        raise HTTPException(status_code=404, detail="Pothole not found")
    return pothole

@api_router.post("/potholes/{pothole_id}/notify")
async def notify_authorities(pothole_id: str, current_user: dict = Depends(get_current_user)):
    pothole = await db.potholes.find_one({'id': pothole_id})
    if not pothole:
        raise HTTPException(status_code=404, detail="Pothole not found")
    
    # Send SMS
    message = f"New pothole reported at {pothole['location']}. Severity: {pothole['severity']}, Area: {pothole['total_area_m2']}m², Cost: ₹{pothole['estimated_cost_inr']}. ID: {pothole_id}"
    notification = await send_sms(PHONE_AUTHORITY, message)
    
    # Update status and audit
    audit_entry = {
        'action': 'reported_to_authority',
        'actor_id': current_user['user_id'],
        'actor_role': current_user['role'],
        'timestamp': datetime.now(timezone.utc).isoformat()
    }
    
    await db.potholes.update_one(
        {'id': pothole_id},
        {
            '$set': {'status': 'Reported', 'updated_at': datetime.now(timezone.utc).isoformat()},
            '$push': {'audit': audit_entry}
        }
    )
    
    # Store notification reference
    notification['pothole_id'] = pothole_id
    await db.notifications.update_one(
        {'id': notification['id']},
        {'$set': {'pothole_id': pothole_id}}
    )
    
    return {'message': 'Authorities notified', 'notification_id': notification['id']}

@api_router.post("/potholes/{pothole_id}/action")
async def pothole_action(
    pothole_id: str,
    action_data: PotholeAction,
    current_user: dict = Depends(get_current_user)
):
    # Check authority role
    if current_user['role'] != 'authority':
        raise HTTPException(status_code=403, detail="Only authorities can perform actions")
    
    pothole = await db.potholes.find_one({'id': pothole_id})
    if not pothole:
        raise HTTPException(status_code=404, detail="Pothole not found")
    
    # Map actions to status updates
    action_status_map = {
        'dispatch_drone': 'Inspected',
        'inspection_done': 'Inspected',
        'schedule_repair': 'In Progress',
        'repair_done': 'Resolved',
        'notify_citizen': pothole['status']  # Keep current status
    }
    
    new_status = action_status_map.get(action_data.action, pothole['status'])
    
    # Create audit entry
    audit_entry = {
        'action': action_data.action,
        'actor_id': current_user['user_id'],
        'actor_role': current_user['role'],
        'notes': action_data.notes,
        'timestamp': datetime.now(timezone.utc).isoformat()
    }
    
    # Update pothole
    await db.potholes.update_one(
        {'id': pothole_id},
        {
            '$set': {'status': new_status, 'updated_at': datetime.now(timezone.utc).isoformat()},
            '$push': {'audit': audit_entry}
        }
    )
    
    # Send SMS if notify_citizen action
    if action_data.action == 'notify_citizen':
        user = await db.users.find_one({'id': pothole['user_id']})
        if user:
            message = f"Update on your pothole report at {pothole['location']}: {action_data.notes or 'Status updated to ' + new_status}"
            await send_sms(user.get('phone', PHONE_AUTHORITY), message)
    
    return {'message': 'Action recorded', 'new_status': new_status}

@api_router.get("/users/{user_id}/reports")
async def get_user_reports(user_id: str, current_user: dict = Depends(get_current_user)):
    # Users can only see their own reports unless they're authority
    if current_user['user_id'] != user_id and current_user['role'] != 'authority':
        raise HTTPException(status_code=403, detail="Access denied")
    
    reports = await db.potholes.find({'user_id': user_id}, {'_id': 0}).sort('created_at', -1).to_list(1000)
    return reports

@api_router.get("/notifications")
async def get_notifications(current_user: dict = Depends(get_current_user)):
    if current_user['role'] != 'authority':
        raise HTTPException(status_code=403, detail="Only authorities can view notifications")
    
    notifications = await db.notifications.find({}, {'_id': 0}).sort('created_at', -1).to_list(100)
    return notifications

# Include router
app.include_router(api_router)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Startup event
@app.on_event("startup")
async def startup_event():
    load_model()
    logger.info("Application started")

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
