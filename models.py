"""
SQLAlchemy ORM models.
Tables: User, Delivery, Route, DriverLocation
"""
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, ForeignKey, Enum, Text
)
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from database import Base


class DeliveryStatus(str, enum.Enum):
    PENDING = "Pending"
    IN_PROGRESS = "In Progress"
    DELIVERED = "Delivered"


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    DRIVER = "driver"
    BUSINESS = "business"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    role = Column(Enum(UserRole), default=UserRole.BUSINESS)
    created_at = Column(DateTime, default=datetime.utcnow)

    # User has TWO FKs in Delivery (owner_id and driver_id) — must disambiguate.
    deliveries = relationship(
        "Delivery", back_populates="owner",
        foreign_keys="Delivery.owner_id",
    )
    locations = relationship("DriverLocation", back_populates="driver")


class Delivery(Base):
    __tablename__ = "deliveries"

    id = Column(Integer, primary_key=True, index=True)
    address = Column(String, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    package_weight = Column(Float, default=1.0)
    priority = Column(Integer, default=1)  # 1 = normal, 2 = high
    status = Column(Enum(DeliveryStatus), default=DeliveryStatus.PENDING)
    cluster_id = Column(Integer, nullable=True)  # set by K-Means
    eta_minutes = Column(Float, nullable=True)   # set by ETA predictor
    created_at = Column(DateTime, default=datetime.utcnow)
    delivered_at = Column(DateTime, nullable=True)

    owner_id = Column(Integer, ForeignKey("users.id"))
    driver_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    route_id = Column(Integer, ForeignKey("routes.id"), nullable=True)

    owner = relationship("User", foreign_keys=[owner_id], back_populates="deliveries")
    route = relationship("Route", back_populates="deliveries")


class Route(Base):
    __tablename__ = "routes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    driver_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    ordered_stops = Column(Text, nullable=True)  # JSON-encoded list of delivery IDs in order
    total_distance_km = Column(Float, default=0.0)
    total_eta_minutes = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    deliveries = relationship("Delivery", back_populates="route")


class DriverLocation(Base):
    __tablename__ = "driver_locations"

    id = Column(Integer, primary_key=True, index=True)
    driver_id = Column(Integer, ForeignKey("users.id"))
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    speed_kmh = Column(Float, default=0.0)
    timestamp = Column(DateTime, default=datetime.utcnow)

    driver = relationship("User", back_populates="locations")
