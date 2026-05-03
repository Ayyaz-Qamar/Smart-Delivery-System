"""
Real-time driver tracking.

- POST /tracking/live-location  → driver pushes a GPS update (REST)
- GET  /tracking/get-live-tracking/{driver_id} → latest location for a driver
- WS   /tracking/ws/{driver_id} → WebSocket stream of live updates

The WebSocketManager broadcasts each new location to every connected client
listening to that driver_id (e.g. the frontend map view).
"""
from typing import Dict, List
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, HTTPException
from sqlalchemy.orm import Session

from database import get_db, SessionLocal
from models import DriverLocation, User
from schemas import LiveLocationIn, LiveLocationOut
from auth import get_current_user

router = APIRouter(prefix="/tracking", tags=["tracking"])


class WebSocketManager:
    """Tracks active websocket connections per driver_id and broadcasts updates."""

    def __init__(self):
        self.active: Dict[int, List[WebSocket]] = {}

    async def connect(self, driver_id: int, ws: WebSocket):
        await ws.accept()
        self.active.setdefault(driver_id, []).append(ws)

    def disconnect(self, driver_id: int, ws: WebSocket):
        if driver_id in self.active and ws in self.active[driver_id]:
            self.active[driver_id].remove(ws)
            if not self.active[driver_id]:
                del self.active[driver_id]

    async def broadcast(self, driver_id: int, message: dict):
        for ws in self.active.get(driver_id, []):
            try:
                await ws.send_json(message)
            except Exception:
                # Dead connection — drop it
                self.disconnect(driver_id, ws)


manager = WebSocketManager()


@router.post("/live-location", response_model=LiveLocationOut)
async def post_live_location(loc: LiveLocationIn, db: Session = Depends(get_db),
                             current_user: User = Depends(get_current_user)):
    """Driver pushes their current GPS coordinates."""
    record = DriverLocation(
        driver_id=current_user.id,
        latitude=loc.latitude,
        longitude=loc.longitude,
        speed_kmh=loc.speed_kmh or 0.0,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    # Push to any websocket subscribers
    await manager.broadcast(current_user.id, {
        "driver_id": current_user.id,
        "latitude": record.latitude,
        "longitude": record.longitude,
        "speed_kmh": record.speed_kmh,
        "timestamp": record.timestamp.isoformat(),
    })
    return record


@router.get("/get-live-tracking/{driver_id}", response_model=LiveLocationOut)
def get_live_tracking(driver_id: int, db: Session = Depends(get_db),
                      current_user: User = Depends(get_current_user)):
    """Latest known location for a driver."""
    record = (db.query(DriverLocation)
              .filter(DriverLocation.driver_id == driver_id)
              .order_by(DriverLocation.timestamp.desc())
              .first())
    if not record:
        raise HTTPException(status_code=404, detail="No location recorded for this driver")
    return record


@router.websocket("/ws/{driver_id}")
async def websocket_endpoint(websocket: WebSocket, driver_id: int):
    """
    Frontend connects here to receive live driver location updates.
    No JWT here for simplicity — wrap with a query-param token check in production.
    """
    await manager.connect(driver_id, websocket)
    try:
        # Send the latest known position immediately so the map isn't blank
        db = SessionLocal()
        try:
            latest = (db.query(DriverLocation)
                      .filter(DriverLocation.driver_id == driver_id)
                      .order_by(DriverLocation.timestamp.desc())
                      .first())
            if latest:
                await websocket.send_json({
                    "driver_id": driver_id,
                    "latitude": latest.latitude,
                    "longitude": latest.longitude,
                    "speed_kmh": latest.speed_kmh,
                    "timestamp": latest.timestamp.isoformat(),
                })
        finally:
            db.close()

        # Keep the connection alive; broadcasts come from post_live_location
        while True:
            await websocket.receive_text()  # client may send pings
    except WebSocketDisconnect:
        manager.disconnect(driver_id, websocket)
