"""
QGIS CMS Pro - Advanced Web GIS Platform
Backend: FastAPI + PostgreSQL/PostGIS + SQLAlchemy
Features: Auth, RBAC, Spatial Analysis, Audit Logs, File Import/Export, Dashboard
"""
import os
import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from enum import Enum

from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, Text, Boolean, JSON, func
from sqlalchemy.orm import sessionmaker, declarative_base, relationship, Session
from passlib.context import CryptContext
from jose import JWTError, jwt
import geoalchemy2
from geoalchemy2 import Geometry
from shapely.geometry import shape, mapping
from shapely.wkb import loads as wkb_loads
from shapely.wkt import dumps as wkt_dumps
import pandas as pd
from io import StringIO

# --- Configuration ---
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASS", "password")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "qgis_cms")
SECRET_KEY = os.getenv("SECRET_KEY", "supersecretkey_change_in_prod_beget")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Database Setup ---
engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- Models ---
class UserRole(str, Enum):
    VIEWER = "viewer"
    EDITOR = "editor"
    ADMIN = "admin"

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default=UserRole.VIEWER.value)
    is_active = Column(Boolean, default=True)
    settings = Column(JSON, default={"theme": "light", "default_lat": 55.75, "default_lon": 37.61, "zoom": 10})
    created_at = Column(DateTime, default=datetime.utcnow)
    layers = relationship("Layer", back_populates="owner")
    audit_logs = relationship("AuditLog", back_populates="user")

class Layer(Base):
    __tablename__ = "layers"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    owner_id = Column(Integer, ForeignKey("users.id"))
    geometry_type = Column(String, default="GEOMETRY")
    is_public = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    owner = relationship("User", back_populates="layers")
    features = relationship("Feature", back_populates="layer", cascade="all, delete-orphan")

class Feature(Base):
    __tablename__ = "features"
    id = Column(Integer, primary_key=True, index=True)
    layer_id = Column(Integer, ForeignKey("layers.id"), nullable=False)
    geometry = Column(Geometry(geometry_type="GEOMETRY", srid=4326))
    properties = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
    layer = relationship("Layer", back_populates="features")

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    action = Column(String, nullable=False)
    resource_type = Column(String)
    resource_id = Column(Integer)
    details = Column(JSON)
    timestamp = Column(DateTime, default=datetime.utcnow)
    ip_address = Column(String)
    user = relationship("User", back_populates="audit_logs")

# --- Schemas ---
class Token(BaseModel):
    access_token: str
    token_type: str

class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    role: UserRole = UserRole.VIEWER

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    role: str
    settings: dict
    class Config: from_attributes = True

class LayerCreate(BaseModel):
    name: str
    description: Optional[str] = None
    geometry_type: str = "GEOMETRY"
    is_public: bool = False

class FeatureCreate(BaseModel):
    geometry: Dict[str, Any]
    properties: Dict[str, Any] = {}

class AuditLogResponse(BaseModel):
    id: int
    username: str
    action: str
    resource_type: str
    timestamp: datetime
    details: dict
    class Config: from_attributes = True

class DashboardStats(BaseModel):
    total_users: int
    total_layers: int
    total_features: int
    recent_activity_count: int
    storage_used_mb: float

# --- Security ---
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def verify_password(plain, hashed): return pwd_context.verify(plain, hashed)
def get_password_hash(pw): return pwd_context.hash(pw)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(lambda: SessionLocal())):
    exc = HTTPException(status_code=401, detail="Invalid credentials", headers={"WWW-Authenticate": "Bearer"})
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if not username: raise exc
    except JWTError: raise exc
    user = db.query(User).filter(User.username == username).first()
    if not user: raise exc
    return user

def log_action(db: Session, user: User, action: str, res_type: str, res_id: int = None, details: dict = None, ip: str = None):
    db.add(AuditLog(user_id=user.id, action=action, resource_type=res_type, resource_id=res_id, details=details or {}, ip_address=ip))
    db.commit()

# --- App ---
app = FastAPI(title="QGIS CMS Pro", version="2.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.on_event("startup")
async def startup():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

def require_role(required: UserRole):
    def checker(current: User = Depends(get_current_user)):
        order = {UserRole.VIEWER: 1, UserRole.EDITOR: 2, UserRole.ADMIN: 3}
        if order.get(UserRole(current.role), 0) < order.get(required, 0):
            raise HTTPException(403, "Insufficient permissions")
        return current
    return checker

# --- Auth Endpoints ---
@app.post("/register", response_model=UserResponse)
async def register(user: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == user.username).first():
        raise HTTPException(400, "Username exists")
    db_user = User(username=user.username, email=user.email, hashed_password=get_password_hash(user.password), role=user.role.value)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    log_action(db, db_user, "REGISTER", "USER", db_user.id)
    return db_user

@app.post("/token", response_model=Token)
async def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db), request: Request = None):
    user = db.query(User).filter(User.username == form.username).first()
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(401, "Invalid credentials")
    token = create_access_token({"sub": user.username})
    log_action(db, user, "LOGIN", "USER", user.id, {"ip": request.client.host if request else "unknown"})
    return {"access_token": token, "token_type": "bearer"}

@app.get("/users/me", response_model=UserResponse)
async def me(current: User = Depends(get_current_user)): return current

@app.put("/users/me/settings")
async def update_settings(settings: dict, current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    current.settings = settings
    db.commit()
    log_action(db, current, "UPDATE_SETTINGS", "USER", current.id)
    return {"status": "ok"}

# --- Layer Endpoints ---
@app.get("/layers")
async def list_layers(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    q = db.query(Layer)
    if current.role != UserRole.ADMIN.value:
        q = q.filter((Layer.is_public == True) | (Layer.owner_id == current.id))
    return q.offset(skip).limit(limit).all()

@app.post("/layers")
async def create_layer(layer: LayerCreate, db: Session = Depends(get_db), current: User = Depends(require_role(UserRole.EDITOR))):
    new_layer = Layer(**layer.dict(), owner_id=current.id)
    db.add(new_layer)
    db.commit()
    db.refresh(new_layer)
    log_action(db, current, "CREATE", "LAYER", new_layer.id)
    return new_layer

@app.delete("/layers/{lid}")
async def delete_layer(lid: int, db: Session = Depends(get_db), current: User = Depends(require_role(UserRole.ADMIN))):
    layer = db.query(Layer).filter(Layer.id == lid).first()
    if not layer: raise HTTPException(404, "Not found")
    db.delete(layer)
    db.commit()
    log_action(db, current, "DELETE", "LAYER", lid)
    return {"status": "deleted"}

# --- Feature Endpoints ---
@app.get("/layers/{lid}/features")
async def get_features(lid: int, db: Session = Depends(get_db)):
    feats = db.query(Feature).filter(Feature.layer_id == lid).all()
    fc = []
    for f in feats:
        if f.geometry:
            geom = wkb_loads(bytes(f.geometry.data), hex=True)
            fc.append({"type": "Feature", "id": f.id, "geometry": mapping(geom), "properties": f.properties})
    return {"type": "FeatureCollection", "features": fc}

@app.post("/layers/{lid}/features")
async def create_feature(lid: int, feat: FeatureCreate, db: Session = Depends(get_db), current: User = Depends(require_role(UserRole.EDITOR))):
    layer = db.query(Layer).filter(Layer.id == lid).first()
    if not layer: raise HTTPException(404, "Layer not found")
    geom = shape(feat.geometry)
    wkt = wkt_dumps(geom, srid=4326)
    new_feat = Feature(layer_id=lid, geometry=wkt, properties=feat.properties)
    db.add(new_feat)
    db.commit()
    db.refresh(new_feat)
    log_action(db, current, "CREATE", "FEATURE", new_feat.id)
    return new_feat

@app.put("/features/{fid}")
async def update_feature(fid: int, feat: FeatureCreate, db: Session = Depends(get_db), current: User = Depends(require_role(UserRole.EDITOR))):
    f = db.query(Feature).filter(Feature.id == fid).first()
    if not f: raise HTTPException(404, "Not found")
    f.geometry = wkt_dumps(shape(feat.geometry), srid=4326)
    f.properties = feat.properties
    db.commit()
    log_action(db, current, "UPDATE", "FEATURE", fid)
    return f

@app.delete("/features/{fid}")
async def delete_feature(fid: int, db: Session = Depends(get_db), current: User = Depends(require_role(UserRole.EDITOR))):
    f = db.query(Feature).filter(Feature.id == fid).first()
    if not f: raise HTTPException(404, "Not found")
    db.delete(f)
    db.commit()
    log_action(db, current, "DELETE", "FEATURE", fid)
    return {"status": "deleted"}

# --- Analytics & Tools ---
@app.get("/dashboard/stats", response_model=DashboardStats)
async def dashboard(db: Session = Depends(get_db), current: User = Depends(require_role(UserRole.ADMIN))):
    return DashboardStats(
        total_users=db.query(User).count(),
        total_layers=db.query(Layer).count(),
        total_features=db.query(Feature).count(),
        recent_activity_count=db.query(AuditLog).filter(AuditLog.timestamp > datetime.utcnow() - timedelta(days=7)).count(),
        storage_used_mb=0.0
    )

@app.get("/audit/logs")
async def audit_logs(skip: int = 0, limit: int = 50, db: Session = Depends(get_db), current: User = Depends(require_role(UserRole.ADMIN))):
    logs = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).offset(skip).limit(limit).all()
    result = []
    for l in logs:
        u = db.query(User).filter(User.id == l.user_id).first()
        result.append({"id": l.id, "username": u.username if u else "unknown", "action": l.action, "resource_type": l.resource_type, "timestamp": l.timestamp, "details": l.details})
    return result

@app.post("/import/geojson/{lid}")
async def import_geojson(lid: int, file: UploadFile = File(...), db: Session = Depends(get_db), current: User = Depends(require_role(UserRole.EDITOR))):
    data = json.loads(await file.read())
    if data.get("type") != "FeatureCollection": raise HTTPException(400, "Invalid GeoJSON")
    count = 0
    for f in data.get("features", []):
        if not f.get("geometry"): continue
        geom = shape(f["geometry"])
        feat = Feature(layer_id=lid, geometry=wkt_dumps(geom, srid=4326), properties=f.get("properties", {}))
        db.add(feat)
        count += 1
    db.commit()
    log_action(db, current, "IMPORT", "LAYER", lid, {"count": count})
    return {"imported": count}

@app.get("/export/csv/{lid}")
async def export_csv(lid: int, db: Session = Depends(get_db)):
    feats = db.query(Feature).filter(Feature.layer_id == lid).all()
    if not feats: raise HTTPException(404, "No features")
    rows = []
    for f in feats:
        row = {"id": f.id, "geometry_wkt": wkt_dumps(wkb_loads(bytes(f.geometry.data), hex=True))}
        row.update(f.properties)
        rows.append(row)
    df = pd.DataFrame(rows)
    stream = StringIO()
    df.to_csv(stream, index=False)
    resp = StreamingResponse(iter([stream.getvalue()]), media_type="text/csv")
    resp.headers["Content-Disposition"] = f"attachment; filename=layer_{lid}.csv"
    return resp

@app.post("/analysis/buffer/{lid}")
async def analyze_buffer(lid: int, distance: float, db: Session = Depends(get_db)):
    results = db.query(Feature.id, func.ST_AsGeoJSON(func.ST_Buffer(Feature.geometry, distance / 111320)).label("buf")).filter(Feature.layer_id == lid).all()
    feats = [{"type": "Feature", "geometry": json.loads(r.buf), "properties": {"original_id": r.id}} for r in results]
    return {"type": "FeatureCollection", "features": feats}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
