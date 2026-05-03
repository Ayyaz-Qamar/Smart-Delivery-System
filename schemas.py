"""
Pydantic schemas for request validation and response serialization.
"""
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime
from models import DeliveryStatus, UserRole


# ============ Auth Schemas ============
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    role: UserRole = UserRole.BUSINESS


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    email: str
    full_name: Optional[str]
    role: UserRole

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ============ Delivery Schemas ============
class DeliveryCreate(BaseModel):
    address: str
    latitude: float
    longitude: float
    package_weight: Optional[float] = 1.0
    priority: Optional[int] = 1


class DeliveryOut(BaseModel):
    id: int
    address: str
    latitude: float
    longitude: float
    package_weight: float
    priority: int
    status: DeliveryStatus
    cluster_id: Optional[int]
    eta_minutes: Optional[float]
    created_at: datetime
    delivered_at: Optional[datetime]

    class Config:
        from_attributes = True


class DeliveryStatusUpdate(BaseModel):
    status: DeliveryStatus


# ============ Route / ML Schemas ============
class OptimizeRouteRequest(BaseModel):
    delivery_ids: List[int]
    start_lat: float
    start_lng: float
    driver_id: Optional[int] = None
    use_rl: Optional[bool] = False  # whether to use Q-learning agent


class OptimizeRouteResponse(BaseModel):
    ordered_delivery_ids: List[int]
    total_distance_km: float
    total_eta_minutes: float
    route_id: int


class ETARequest(BaseModel):
    distance_km: float
    hour_of_day: int  # 0-23
    traffic_level: int  # 1=low, 2=medium, 3=high
    package_weight: Optional[float] = 1.0


class ETAResponse(BaseModel):
    eta_minutes: float


class ClusterRequest(BaseModel):
    delivery_ids: List[int]
    n_clusters: int = 3


class ClusterResponse(BaseModel):
    assignments: dict  # {delivery_id: cluster_id}


# ============ Tracking Schemas ============
class LiveLocationIn(BaseModel):
    latitude: float
    longitude: float
    speed_kmh: Optional[float] = 0.0


class LiveLocationOut(BaseModel):
    driver_id: int
    latitude: float
    longitude: float
    speed_kmh: float
    timestamp: datetime

    class Config:
        from_attributes = True


# ============ Analytics ============
class AnalyticsResponse(BaseModel):
    total_deliveries: int
    pending: int
    in_progress: int
    delivered: int
    avg_delivery_time_minutes: float
    efficiency_percent: float
