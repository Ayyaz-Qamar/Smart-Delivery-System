"""
Delivery endpoints: list, create, update status, and bulk upload (CSV/JSON).
"""
import csv
import io
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from database import get_db
from models import Delivery, User, DeliveryStatus
from schemas import DeliveryCreate, DeliveryOut, DeliveryStatusUpdate, AnalyticsResponse
from auth import get_current_user

router = APIRouter(prefix="/deliveries", tags=["deliveries"])


@router.get("/", response_model=List[DeliveryOut])
def list_deliveries(db: Session = Depends(get_db),
                    current_user: User = Depends(get_current_user)):
    return db.query(Delivery).filter(Delivery.owner_id == current_user.id).all()


@router.post("/", response_model=DeliveryOut, status_code=201)
def create_delivery(d: DeliveryCreate, db: Session = Depends(get_db),
                    current_user: User = Depends(get_current_user)):
    delivery = Delivery(**d.model_dump(), owner_id=current_user.id)
    db.add(delivery)
    db.commit()
    db.refresh(delivery)
    return delivery


@router.post("/upload-locations", response_model=List[DeliveryOut])
async def upload_locations(file: UploadFile = File(...),
                            db: Session = Depends(get_db),
                            current_user: User = Depends(get_current_user)):
    """
    Bulk-upload deliveries from a CSV file.
    Required columns: address, latitude, longitude
    Optional columns: package_weight, priority
    """
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Please upload a CSV file")

    content = (await file.read()).decode("utf-8")
    reader = csv.DictReader(io.StringIO(content))

    created = []
    for row in reader:
        try:
            delivery = Delivery(
                address=row["address"],
                latitude=float(row["latitude"]),
                longitude=float(row["longitude"]),
                package_weight=float(row.get("package_weight", 1.0)),
                priority=int(row.get("priority", 1)),
                owner_id=current_user.id,
            )
            db.add(delivery)
            created.append(delivery)
        except (KeyError, ValueError) as e:
            raise HTTPException(status_code=400, detail=f"Bad row: {row} ({e})")

    db.commit()
    for d in created:
        db.refresh(d)
    return created


@router.patch("/{delivery_id}/status", response_model=DeliveryOut)
def update_status(delivery_id: int, update: DeliveryStatusUpdate,
                  db: Session = Depends(get_db),
                  current_user: User = Depends(get_current_user)):
    delivery = db.query(Delivery).filter(
        Delivery.id == delivery_id, Delivery.owner_id == current_user.id
    ).first()
    if not delivery:
        raise HTTPException(status_code=404, detail="Delivery not found")

    delivery.status = update.status
    if update.status == DeliveryStatus.DELIVERED:
        delivery.delivered_at = datetime.utcnow()
    db.commit()
    db.refresh(delivery)
    return delivery

@router.delete("/all", status_code=204)
def delete_all_deliveries(db: Session = Depends(get_db),
                          current_user: User = Depends(get_current_user)):
    """Delete ALL deliveries belonging to the current user. Use carefully!"""
    db.query(Delivery).filter(Delivery.owner_id == current_user.id).delete()
    db.commit()
@router.delete("/{delivery_id}", status_code=204)
def delete_delivery(delivery_id: int, db: Session = Depends(get_db),
                    current_user: User = Depends(get_current_user)):
    delivery = db.query(Delivery).filter(
        Delivery.id == delivery_id, Delivery.owner_id == current_user.id
    ).first()
    if not delivery:
        raise HTTPException(status_code=404, detail="Delivery not found")
    db.delete(delivery)
    db.commit()


@router.get("/analytics", response_model=AnalyticsResponse)
def analytics(db: Session = Depends(get_db),
              current_user: User = Depends(get_current_user)):
    """Compute KPI metrics for the current user's deliveries."""
    deliveries = db.query(Delivery).filter(Delivery.owner_id == current_user.id).all()
    total = len(deliveries)
    pending = sum(1 for d in deliveries if d.status == DeliveryStatus.PENDING)
    in_progress = sum(1 for d in deliveries if d.status == DeliveryStatus.IN_PROGRESS)
    delivered_list = [d for d in deliveries if d.status == DeliveryStatus.DELIVERED]
    delivered = len(delivered_list)

    # Average actual delivery time (created_at -> delivered_at) in minutes
    times = []
    for d in delivered_list:
        if d.delivered_at and d.created_at:
            times.append((d.delivered_at - d.created_at).total_seconds() / 60.0)
    avg_time = sum(times) / len(times) if times else 0.0

    # Efficiency = % of deliveries completed
    efficiency = (delivered / total * 100) if total else 0.0

    return AnalyticsResponse(
        total_deliveries=total,
        pending=pending,
        in_progress=in_progress,
        delivered=delivered,
        avg_delivery_time_minutes=round(avg_time, 2),
        efficiency_percent=round(efficiency, 2),
    )
