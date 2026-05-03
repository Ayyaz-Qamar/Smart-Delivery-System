import { useEffect, useState, useRef } from 'react';
import { MapContainer, TileLayer, Marker, Popup, Polyline, CircleMarker } from 'react-leaflet';
import L from 'leaflet';
import {
  listDeliveries, optimizeRoute, clusterDeliveries,
  postLiveLocation, wsURL, getMe, updateDeliveryStatus
} from '../api';

L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
});

const CLUSTER_COLORS = ['#6366f1', '#10b981', '#f59e0b', '#ef4444', '#a78bfa', '#ec4899'];
const DELIVERED_COLOR = '#10b981';   // green
const PENDING_COLOR = '#6366f1';     // purple

const truckIcon = L.divIcon({
  html: '<div style="font-size: 28px; transform: translate(-14px, -14px); filter: drop-shadow(0 2px 4px rgba(0,0,0,0.5));">🚚</div>',
  className: '',
  iconSize: [28, 28],
});

// Haversine formula — distance between two GPS points in meters
function distanceMeters(lat1, lng1, lat2, lng2) {
  const R = 6371000;
  const toRad = (x) => x * Math.PI / 180;
  const dLat = toRad(lat2 - lat1);
  const dLng = toRad(lng2 - lng1);
  const a = Math.sin(dLat / 2) ** 2 +
            Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLng / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(a));
}

const DELIVERY_RADIUS_METERS = 200;  // 200m ke andar aaye to "Delivered"

export default function MapView() {
  const [deliveries, setDeliveries] = useState([]);
  const [route, setRoute] = useState(null);
  const [clusters, setClusters] = useState({});
  const [driverLoc, setDriverLoc] = useState(null);
  const [me, setMe] = useState(null);
  const [start, setStart] = useState({ lat: 28.42, lng: 70.30 });
  const [useRL, setUseRL] = useState(false);
  const [loading, setLoading] = useState(false);
  const [simRunning, setSimRunning] = useState(false);
  const [deliveredCount, setDeliveredCount] = useState(0);
  const wsRef = useRef(null);
  const simTimerRef = useRef(null);
  const deliveriesRef = useRef([]);  // current snapshot for use inside intervals

  // Keep ref in sync with state — needed inside the WebSocket callback
  useEffect(() => { deliveriesRef.current = deliveries; }, [deliveries]);

  const refreshDeliveries = async () => {
    const r = await listDeliveries();
    setDeliveries(r.data);
    setDeliveredCount(r.data.filter(d => d.status === 'Delivered').length);
  };

  useEffect(() => {
    refreshDeliveries();
    getMe().then((r) => setMe(r.data));
  }, []);

  // WebSocket — listen for live driver location
  useEffect(() => {
    if (!me) return;
    const ws = new WebSocket(wsURL(me.id));
    ws.onmessage = async (event) => {
      const data = JSON.parse(event.data);
      const newLoc = { lat: data.latitude, lng: data.longitude, speed: data.speed_kmh };
      setDriverLoc(newLoc);

      // 🎯 Auto-mark as Delivered when truck reaches a stop
      const currentDeliveries = deliveriesRef.current;
      for (const d of currentDeliveries) {
        if (d.status === 'Delivered') continue;
        const dist = distanceMeters(newLoc.lat, newLoc.lng, d.latitude, d.longitude);
        if (dist <= DELIVERY_RADIUS_METERS) {
          try {
            await updateDeliveryStatus(d.id, 'Delivered');
            // Update local state immediately so we don't double-mark
            setDeliveries(prev => prev.map(x =>
              x.id === d.id ? { ...x, status: 'Delivered' } : x
            ));
            setDeliveredCount(prev => prev + 1);
          } catch (e) { /* ignore — try again next tick */ }
        }
      }
    };
    ws.onerror = () => console.log('WebSocket error — backend chal raha hai?');
    wsRef.current = ws;
    return () => ws.close();
  }, [me]);

  const onOptimize = async () => {
    if (deliveries.length === 0) return alert('Pehle deliveries upload karo');
    setLoading(true);
    try {
      // Pehle saari deliveries ka status "Pending" reset karo (taake dobara simulate kar sakein)
      const pendingIds = deliveries.filter(d => d.status === 'Delivered').map(d => d.id);
      for (const id of pendingIds) {
        await updateDeliveryStatus(id, 'Pending');
      }

      const res = await optimizeRoute({
        delivery_ids: deliveries.map(d => d.id),
        start_lat: start.lat,
        start_lng: start.lng,
        use_rl: useRL,
      });
      setRoute(res.data);
      await refreshDeliveries();
    } catch (e) {
      alert('Optimization failed: ' + (e.response?.data?.detail || e.message));
    } finally {
      setLoading(false);
    }
  };

  const onCluster = async () => {
    if (deliveries.length === 0) return;
    setLoading(true);
    try {
      const n = Math.min(3, deliveries.length);
      const res = await clusterDeliveries(deliveries.map(d => d.id), n);
      const fixed = {};
      Object.entries(res.data.assignments).forEach(([k, v]) => { fixed[parseInt(k)] = v; });
      setClusters(fixed);
    } finally {
      setLoading(false);
    }
  };

  const startSimulation = () => {
    if (!route || simRunning) return;
    setSimRunning(true);
    setDeliveredCount(0);

    const orderedDeliveries = route.ordered_delivery_ids
      .map(id => deliveries.find(d => d.id === id))
      .filter(Boolean);
    const path = [
      [start.lat, start.lng],
      ...orderedDeliveries.map(d => [d.latitude, d.longitude]),
    ];

    let segIdx = 0, t = 0;
    const stepsPerSegment = 30;

    simTimerRef.current = setInterval(async () => {
      if (segIdx >= path.length - 1) {
        clearInterval(simTimerRef.current);
        setSimRunning(false);
        return;
      }
      const [lat1, lng1] = path[segIdx];
      const [lat2, lng2] = path[segIdx + 1];
      const f = t / stepsPerSegment;
      const lat = lat1 + (lat2 - lat1) * f;
      const lng = lng1 + (lng2 - lng1) * f;

      try {
        await postLiveLocation({ latitude: lat, longitude: lng, speed_kmh: 35 });
      } catch (e) { /* ignore */ }

      t++;
      if (t > stepsPerSegment) { t = 0; segIdx++; }
    }, 500);
  };

  const stopSimulation = () => {
    if (simTimerRef.current) clearInterval(simTimerRef.current);
    setSimRunning(false);
  };

  useEffect(() => () => stopSimulation(), []);

  const routePath = route ? [
    [start.lat, start.lng],
    ...route.ordered_delivery_ids
      .map(id => deliveries.find(d => d.id === id))
      .filter(Boolean)
      .map(d => [d.latitude, d.longitude]),
  ] : null;

  const center = deliveries.length > 0
    ? [deliveries[0].latitude, deliveries[0].longitude]
    : [start.lat, start.lng];

  const totalCount = deliveries.length;

  return (
    <div className="container">
      <h2>Map & Route Optimization</h2>

      <div className="card" style={{ marginBottom: 16 }}>
        <div className="toolbar">
          <input
            type="number" step="any"
            placeholder="Start latitude"
            value={start.lat}
            onChange={(e) => setStart({ ...start, lat: parseFloat(e.target.value) || 0 })}
            style={{ maxWidth: 180 }}
          />
          <input
            type="number" step="any"
            placeholder="Start longitude"
            value={start.lng}
            onChange={(e) => setStart({ ...start, lng: parseFloat(e.target.value) || 0 })}
            style={{ maxWidth: 180 }}
          />
          <label style={{ display: 'flex', alignItems: 'center', gap: 6, color: 'var(--text-dim)', fontSize: 13 }}>
            <input type="checkbox" checked={useRL} onChange={(e) => setUseRL(e.target.checked)} style={{ width: 'auto' }} />
            Use RL (Q-learning)
          </label>
          <button onClick={onOptimize} disabled={loading}>Optimize Route</button>
          <button onClick={onCluster} disabled={loading} className="secondary">K-Means Cluster</button>
          {!simRunning ? (
            <button onClick={startSimulation} disabled={!route}>▶ Simulate driver</button>
          ) : (
            <button onClick={stopSimulation} className="secondary">⏸ Stop simulation</button>
          )}
        </div>

        {route && (
          <div style={{ fontSize: 13, color: 'var(--text-dim)', marginTop: 8 }}>
            Total distance: <b style={{ color: 'var(--text)' }}>{route.total_distance_km} km</b> &nbsp;·&nbsp;
            Total ETA: <b style={{ color: 'var(--text)' }}>{route.total_eta_minutes} min</b> &nbsp;·&nbsp;
            Stops: {route.ordered_delivery_ids.length} &nbsp;·&nbsp;
            Delivered: <b style={{ color: 'var(--success)' }}>{deliveredCount} / {totalCount}</b>
          </div>
        )}
      </div>

      <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
        <div className="map-container">
          <MapContainer center={center} zoom={11} style={{ height: '100%', width: '100%' }}>
            <TileLayer
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              attribution='&copy; OpenStreetMap contributors'
            />

            <CircleMarker
              center={[start.lat, start.lng]}
              radius={10}
              pathOptions={{ color: '#10b981', fillColor: '#10b981', fillOpacity: 0.8 }}
            >
              <Popup>Start / Depot</Popup>
            </CircleMarker>

            {deliveries.map(d => {
              // Color logic: Delivered = green, otherwise cluster color or default
              let color;
              if (d.status === 'Delivered') {
                color = DELIVERED_COLOR;
              } else if (clusters[d.id] !== undefined) {
                color = CLUSTER_COLORS[clusters[d.id] % CLUSTER_COLORS.length];
              } else {
                color = PENDING_COLOR;
              }

              return (
                <CircleMarker
                  key={d.id}
                  center={[d.latitude, d.longitude]}
                  radius={d.status === 'Delivered' ? 10 : 8}
                  pathOptions={{
                    color,
                    fillColor: color,
                    fillOpacity: d.status === 'Delivered' ? 0.9 : 0.7,
                    weight: d.status === 'Delivered' ? 3 : 2,
                  }}
                >
                  <Popup>
                    <b>#{d.id} — {d.address}</b><br />
                    Status: <b style={{ color: d.status === 'Delivered' ? '#10b981' : '#f59e0b' }}>
                      {d.status === 'Delivered' ? '✓ Delivered' : d.status}
                    </b><br />
                    {d.eta_minutes ? `ETA: ${d.eta_minutes} min` : ''}<br />
                    {clusters[d.id] !== undefined ? `Cluster #${clusters[d.id]}` : ''}
                  </Popup>
                </CircleMarker>
              );
            })}

            {routePath && (
              <Polyline positions={routePath} pathOptions={{ color: '#6366f1', weight: 3, opacity: 0.7 }} />
            )}

            {driverLoc && (
              <Marker position={[driverLoc.lat, driverLoc.lng]} icon={truckIcon}>
                <Popup>
                  Driver live<br />
                  Speed: {driverLoc.speed?.toFixed(1)} km/h
                </Popup>
              </Marker>
            )}
          </MapContainer>
        </div>
      </div>
    </div>
  );
}