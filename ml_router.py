"""
ML endpoints: ETA prediction, clustering, and route optimization.
"""
import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Delivery, Route, User
from schemas import (
    ETARequest, ETAResponse,
    ClusterRequest, ClusterResponse,
    OptimizeRouteRequest, OptimizeRouteResponse,
)
from auth import get_current_user
from ml.eta_predictor import predict_eta
from ml.clustering import assign_clusters_to_drivers
from ml.route_optimizer import optimize_route

router = APIRouter(prefix="/ml", tags=["machine learning"])


@router.post("/predict-eta", response_model=ETAResponse)
def predict_eta_endpoint(req: ETARequest):
    """Supervised model: predict ETA in minutes."""
    eta = predict_eta(
        distance_km=req.distance_km,
        hour_of_day=req.hour_of_day,
        traffic_level=req.traffic_level,
        package_weight=req.package_weight,
    )
    return ETAResponse(eta_minutes=round(eta, 2))


@router.post("/cluster-deliveries", response_model=ClusterResponse)
def cluster_deliveries_endpoint(req: ClusterRequest, db: Session = Depends(get_db),
                                 current_user: User = Depends(get_current_user)):
    """Unsupervised model: K-Means cluster the given deliveries."""
    deliveries = db.query(Delivery).filter(
        Delivery.id.in_(req.delivery_ids),
        Delivery.owner_id == current_user.id,
    ).all()
    if not deliveries:
        raise HTTPException(status_code=404, detail="No matching deliveries")

    coords = [(d.latitude, d.longitude) for d in deliveries]
    ids = [d.id for d in deliveries]
    assignments = assign_clusters_to_drivers(ids, coords, n_drivers=req.n_clusters)

    # Persist cluster assignments
    for d in deliveries:
        d.cluster_id = assignments.get(d.id)
    db.commit()

    return ClusterResponse(assignments=assignments)


@router.post("/optimize-route", response_model=OptimizeRouteResponse)
def optimize_route_endpoint(req: OptimizeRouteRequest, db: Session = Depends(get_db),
                             current_user: User = Depends(get_current_user)):
    """
    Compute the optimal visiting order for a set of deliveries.
    Uses RL (Q-learning) if `use_rl=True`, otherwise nearest-neighbor / OSRM.
    Also predicts ETA for each leg using the supervised model.
    """
    deliveries = db.query(Delivery).filter(
        Delivery.id.in_(req.delivery_ids),
        Delivery.owner_id == current_user.id,
    ).all()
    if not deliveries:
        raise HTTPException(status_code=404, detail="No matching deliveries")

    # Preserve the request's order so we can map indices back to delivery IDs
    id_to_delivery = {d.id: d for d in deliveries}
    ordered_inputs = [id_to_delivery[did] for did in req.delivery_ids if did in id_to_delivery]
    stops = [(d.latitude, d.longitude) for d in ordered_inputs]

    order_indices, total_distance_km = optimize_route(
        start=(req.start_lat, req.start_lng),
        stops=stops,
        use_rl=req.use_rl,
    )
    ordered_ids = [ordered_inputs[i].id for i in order_indices]

    # Predict ETA for each stop using current hour and assumed medium traffic
    hour = datetime.utcnow().hour
    traffic_level = 2
    total_eta = 0.0
    prev = (req.start_lat, req.start_lng)
    for idx in order_indices:
        d = ordered_inputs[idx]
        # Compute leg distance for ETA prediction
        from ml.rl_optimizer import haversine_km
        leg_dist = haversine_km(*prev, d.latitude, d.longitude)
        leg_eta = predict_eta(leg_dist, hour, traffic_level, d.package_weight)
        total_eta += leg_eta
        d.eta_minutes = round(total_eta, 2)  # cumulative ETA from start
        prev = (d.latitude, d.longitude)

    # Persist a Route row
    route = Route(
        name=f"Route {datetime.utcnow().isoformat(timespec='seconds')}",
        driver_id=req.driver_id,
        ordered_stops=json.dumps(ordered_ids),
        total_distance_km=round(total_distance_km, 2),
        total_eta_minutes=round(total_eta, 2),
    )
    db.add(route)
    db.flush()  # need route.id

    # Link deliveries to this route
    for d in ordered_inputs:
        d.route_id = route.id
    db.commit()

    return OptimizeRouteResponse(
        ordered_delivery_ids=ordered_ids,
        total_distance_km=round(total_distance_km, 2),
        total_eta_minutes=round(total_eta, 2),
        route_id=route.id,
    )
