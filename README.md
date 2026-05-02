# 🚚 Smart Delivery Route Optimization System

A full-stack SaaS platform that lets businesses upload deliveries, optimize routes with machine learning, and track drivers live on a map.

## Features

| Area | What's included |
|---|---|
| **Supervised ML** | ETA predictor (Linear Regression + XGBoost). Inputs: distance, time of day, traffic, package weight. |
| **Unsupervised ML** | K-Means clustering of delivery locations into geographic zones for driver assignment. |
| **Reinforcement Learning** | Q-learning agent that learns better routes over many episodes. Falls back to nearest-neighbor for >12 stops. |
| **Route Optimization** | OSRM (real road network) or pure-Python nearest-neighbor heuristic. |
| **Real-time Tracking** | WebSocket-based live driver location streaming. |
| **Auth** | JWT with bcrypt password hashing. |
| **Frontend** | React + Vite + Leaflet, with KPI dashboard and live map. |
| **Database** | PostgreSQL (production) or SQLite (local dev). |

## Project Structure

```
smart_delivery/
├── backend/              # FastAPI app
│   ├── main.py           # entry point
│   ├── auth.py           # JWT + bcrypt
│   ├── database.py       # SQLAlchemy setup
│   ├── models.py         # ORM models
│   ├── schemas.py        # Pydantic schemas
│   ├── routers/          # API routers (auth, deliveries, ml, tracking)
│   ├── ml/               # ML modules
│   │   ├── eta_predictor.py     # Supervised — ETA
│   │   ├── clustering.py        # Unsupervised — K-Means
│   │   ├── rl_optimizer.py      # RL — Q-learning
│   │   └── route_optimizer.py   # OSRM + nearest-neighbor
│   ├── requirements.txt
│   └── .env.example
│
├── frontend/             # React + Vite + Leaflet
│   ├── src/
│   │   ├── pages/        # Login, Signup, Dashboard, Upload, MapView
│   │   ├── components/
│   │   ├── api.js        # axios + WebSocket helpers
│   │   └── main.jsx
│   ├── package.json
│   └── .env.example
│
├── ml_models/            # Standalone training scripts
│   ├── train_eta.py
│   ├── train_clustering.py
│   ├── train_rl.py
│   └── saved/            # Persisted models (created on first run)
│
├── database/
│   └── schema.sql        # PostgreSQL schema reference
│
├── sample_data/
│   └── sample_deliveries.csv
│
├── docs/
│   ├── API.md
│   ├── DEPLOYMENT.md
│   └── postman_collection.json
│
└── README.md             # this file
```

---

## Quick Start (Local Development)

### Prerequisites
- Python **3.10+**
- Node.js **18+**
- (Optional) PostgreSQL — SQLite is used by default for local dev

### 1. Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env              # edit if you want PostgreSQL
uvicorn main:app --reload --port 8000
```

The API is now at `http://localhost:8000`. Swagger docs at `http://localhost:8000/docs`.

The ETA model auto-trains itself on first request (~3 seconds).

### 2. Frontend

```bash
cd frontend
npm install
cp .env.example .env              # default points at localhost:8000
npm run dev
```

Open `http://localhost:5173`.

### 3. End-to-end smoke test

1. Create an account at `/signup`.
2. Go to **Upload** → upload `sample_data/sample_deliveries.csv`.
3. Go to **Live Map**.
4. Click **Optimize Route**. (Toggle "Use RL" to compare Q-learning vs nearest-neighbor.)
5. Click **K-Means Cluster** — markers recolor by cluster.
6. Click **▶ Simulate driver** — a 🚚 marker walks the route in real time over WebSocket.

---

## Run the ML Scripts Standalone

From the project root:

```bash
# Train and save the ETA model
python ml_models/train_eta.py

# Cluster the sample CSV into 3 zones
python ml_models/train_clustering.py

# Compare Q-learning vs nearest-neighbor on the sample CSV
python ml_models/train_rl.py
```

---

## API Testing with Postman

1. Import `docs/postman_collection.json` into Postman.
2. Run **Auth - Signup** then **Auth - Login** — the login response auto-saves the JWT into the `token` collection variable.
3. All other requests reuse `{{token}}` automatically.

Or use the auto-generated Swagger UI at `http://localhost:8000/docs`.

---

## ML Architecture Notes

### Supervised — ETA Predictor (`backend/ml/eta_predictor.py`)
We train on 5,000 synthetic samples that simulate realistic effects: traffic level reduces effective speed; rush-hour windows (7–9 AM, 5–7 PM) inflate ETA; package weight adds a tiny penalty. Both a Linear Regression baseline and XGBoost are trained, MAE-evaluated, and the better one is persisted with `joblib`. At inference time we lazy-load the saved bundle.

### Unsupervised — K-Means Clustering (`backend/ml/clustering.py`)
Cluster delivery `(lat, lng)` into K zones. K defaults to `n_drivers` so each driver gets one geographic blob instead of crisscrossing the city. The centroid is also returned, useful for assigning a depot per cluster.

### Reinforcement Learning — Q-Learning (`backend/ml/rl_optimizer.py`)
We treat route optimization as a TSP and let an agent discover good orderings:
- **State**: `(current_stop, frozenset(visited_stops))`
- **Action**: pick the next stop to visit
- **Reward**: `−distance` (so maximizing reward = minimizing distance)
- **Updates**: standard Q-learning (`Q ← Q + α(r + γ·max Q' − Q)`) with ε-greedy exploration

For ≤12 stops it converges to a near-optimal tour in ~400 episodes (a few hundred ms). For more stops, training-time Q-learning becomes slow and noisy, so we transparently fall back to nearest-neighbor.

### Route Optimization (`backend/ml/route_optimizer.py`)
Top-level dispatcher. By default uses pure-Python nearest-neighbor (no network). Set `ROUTING_BACKEND=osrm` in the `.env` to use the real OSM road network via the public OSRM trip service. The frontend `Use RL` checkbox forces the Q-learning path.

---

## Deployment

See **[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)** for full deployment guides:
- **Backend** → Render (or AWS EC2)
- **Frontend** → Vercel
- **Database** → Supabase (or RDS)

---

## Tech Stack

**Backend:** FastAPI · SQLAlchemy · Pydantic · python-jose · bcrypt · scikit-learn · XGBoost · pandas · numpy · WebSockets

**Frontend:** React 18 · Vite · React Router · Leaflet · React-Leaflet · axios · Recharts

**Infrastructure:** PostgreSQL · OSRM · WebSocket (RFC 6455)

---

## License

MIT — feel free to use this as the foundation for your own delivery platform.
