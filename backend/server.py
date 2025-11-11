from fastapi import FastAPI, APIRouter, File, UploadFile, Form, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, ConfigDict, EmailStr
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, timedelta
from passlib.context import CryptContext
import boto3
from botocore.config import Config
import cv2
import numpy as np
import json

# Load environment variables
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Constants
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

# Create FastAPI app
app = FastAPI()
api_router = APIRouter(prefix="/api")

# Ensure uploads directory exists
UPLOADS_DIR = ROOT_DIR / 'uploads'
UPLOADS_DIR.mkdir(exist_ok=True)

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
    """Send SMS via Twilio or fallback to mock logging"""
    notification_id = str(uuid.uuid4())

    use_twilio = os.getenv("USE_TWILIO", "false").lower() == "true"
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    from_number = os.getenv("TWILIO_PHONE_NUMBER")

    if use_twilio:
        try:
            from twilio.rest import Client
            client = Client(account_sid, auth_token)

            response = client.messages.create(
                body=message,
                from_=from_number,
                to=phone_number
            )

            notification = {
                "id": notification_id,
                "phone_number": phone_number,
                "message": message,
                "status": "sent",
                "message_sid": response.sid,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }

            logger.info(f"✅ SMS sent to {phone_number}: {message}")

        except Exception as e:
            logger.error(f"❌ Twilio send error: {e}")
            notification = {
                "id": notification_id,
                "phone_number": phone_number,
                "message": message,
                "status": "failed",
                "error": str(e),
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
    else:
        logger.info(f"[MOCK SMS] → {phone_number}: {message}")
        notification = {
            "id": notification_id,
            "phone_number": phone_number,
            "message": message,
            "status": "mocked",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    await db.notifications.insert_one(notification)
    return notification


def process_detections(image_path: str, distance_factor: float = 1.0) -> dict:
    """
    Run inference using Roboflow (only), aggregate all potholes, compute total area, count, and confidence.
    Applies a distance factor to adjust perceived area scaling.
    """
    use_roboflow = True  # Always use Roboflow
    from inference_sdk import InferenceHTTPClient

    rf_api_key = os.environ.get("ROBOFLOW_API_KEY")
    rf_model_id = os.environ.get("ROBOFLOW_MODEL_ID")

    client = InferenceHTTPClient(
        api_url="https://serverless.roboflow.com",
        api_key=rf_api_key
    )

    try:
        result = client.infer(image_path, model_id=rf_model_id)
        predictions = result.get("predictions", [])

        if not predictions:
            return {
                "pothole_count": 0,
                "total_area_m2": 0.0,
                "confidence": 0.0,
                "detections": []
            }

        img = cv2.imread(image_path)
        h, w = img.shape[:2]

        # Base assumption: lane width ≈ 3.5 m
        LANE_WIDTH_M = 3.5
        meters_per_pixel = (LANE_WIDTH_M / w) * distance_factor

        detections = []
        total_area_m2 = 0.0
        confidence_sum = 0.0

        for det in predictions:
            x, y, box_w, box_h = det["x"], det["y"], det["width"], det["height"]
            conf = float(det["confidence"])

            # Convert bbox corners
            x1, y1 = int(x - box_w / 2), int(y - box_h / 2)
            x2, y2 = int(x + box_w / 2), int(y + box_h / 2)

            # Convert area from pixels to meters²
            area_m2 = (box_w * meters_per_pixel) * (box_h * meters_per_pixel)

            detections.append({
                "bbox": [x1, y1, x2, y2],
                "confidence": round(conf * 100, 2),
                "area_m2": round(area_m2, 4)
            })

            total_area_m2 += area_m2
            confidence_sum += conf

            # Draw detection
            cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(img, f"{conf:.2f}", (x1, y1 - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

        processed_path = Path(image_path).parent / f"processed_{Path(image_path).name}"
        cv2.imwrite(str(processed_path), img)

        avg_conf = confidence_sum / len(detections)

        return {
            "pothole_count": len(detections),
            "total_area_m2": round(total_area_m2, 3),
            "confidence": round(avg_conf * 100, 1),
            "detections": detections,
            "processed_image_path": str(processed_path)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Roboflow error: {str(e)}")


# API Endpoints
@api_router.get("/")
async def root():
    return {"message": "Pothole Detection API", "status": "operational"}

# Signup endpoint (no JWT)
@api_router.post("/auth/signup")
async def signup(user_data: UserCreate):
    # Check if user exists
    existing_user = await db.users.find_one({'email': user_data.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    # Hash password
    hashed_pwd = pwd_context.hash(user_data.password)
    user_doc = {
        'id': str(uuid.uuid4()),
        'name': user_data.name,
        'email': user_data.email,
        'password': hashed_pwd,
        'role': user_data.role,
        'created_at': datetime.now(timezone.utc).isoformat()
    }
    await db.users.insert_one(user_doc)
    return {"message": "User registered successfully"}

# Login endpoint (no JWT)
@api_router.post("/auth/login")
async def login(credentials: UserLogin):
    user = await db.users.find_one({'email': credentials.email})
    if not user or not pwd_context.verify(credentials.password, user['password']):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {
        "message": "Login successful",
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "role": user["role"]
        }
    }

@api_router.post("/potholes/analyze")
async def analyze_pothole(
    image: UploadFile = File(...),
    location: str = Form(...),
    coordinates: str = Form(...),
    distance_factor: float = Form(1.0)
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
        
        # Process with Roboflow
        detection_result = process_detections(str(file_path), distance_factor)
        
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
            'user_id': None,
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
                'actor_id': None,
                'actor_role': None,
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
    severity: Optional[str] = None
):
    query = {}
    if status:
        query['status'] = status
    if severity:
        query['severity'] = severity
    potholes = await db.potholes.find(query, {'_id': 0}).sort('created_at', -1).to_list(1000)
    # Ensure drone_status is present in every pothole
    for p in potholes:
        if 'drone_status' not in p:
            if p.get('status') == 'Pending':
                p['drone_status'] = 'unassigned'
            elif p.get('status') == 'In Progress':
                p['drone_status'] = 'in_progress'
            elif p.get('status') == 'Resolved':
                p['drone_status'] = 'completed'
            else:
                p['drone_status'] = 'unassigned'
    return potholes

@api_router.get("/potholes/{pothole_id}")
async def get_pothole(pothole_id: str):
    pothole = await db.potholes.find_one({'id': pothole_id}, {'_id': 0})
    if not pothole:
        raise HTTPException(status_code=404, detail="Pothole not found")
    return pothole

@api_router.post("/potholes/{pothole_id}/notify")
async def notify_authorities(pothole_id: str):
    pothole = await db.potholes.find_one({'id': pothole_id})
    if not pothole:
        raise HTTPException(status_code=404, detail="Pothole not found")
    
    # Send SMS
    message = f"New pothole reported at {pothole['location']}. Severity: {pothole['severity']}, Area: {pothole['total_area_m2']}m², Cost: ₹{pothole['estimated_cost_inr']}. ID: {pothole_id}"
    notification = await send_sms(PHONE_AUTHORITY, message)
    
    # Update status and audit
    audit_entry = {
        'action': 'reported_to_authority',
        'actor_id': None,
        'actor_role': None,
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
    action_data: PotholeAction
):
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
        'actor_id': None,
        'actor_role': None,
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
    
    return {'message': 'Action recorded', 'new_status': new_status}

@api_router.post("/potholes/{pothole_id}/assign-drone")
async def assign_drone(pothole_id: str):
    pothole = await db.potholes.find_one({'id': pothole_id})
    if not pothole:
        raise HTTPException(status_code=404, detail="Pothole not found")

    # Update status and drone_status
    update_fields = {
        'status': 'in_progress',
        'drone_status': 'in_progress',
        'updated_at': datetime.now(timezone.utc).isoformat()
    }
    await db.potholes.update_one(
        {'id': pothole_id},
        {'$set': update_fields}
    )
    updated_pothole = await db.potholes.find_one({'id': pothole_id}, {'_id': 0})
    return updated_pothole

@api_router.get("/users/{user_id}/reports")
async def get_user_reports(user_id: str):
    reports = await db.potholes.find({'user_id': user_id}, {'_id': 0}).sort('created_at', -1).to_list(1000)
    return reports

@api_router.get("/notifications")
async def get_notifications():
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
    logger.info("Application started")

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
