import { useEffect, useState } from 'react';
import {
  listDeliveries, getAnalytics, updateDeliveryStatus,
  deleteDelivery, deleteAllDeliveries
} from '../api';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';

const STATUSES = ['Pending', 'In Progress', 'Delivered'];

export default function Dashboard() {
  const [deliveries, setDeliveries] = useState([]);
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(true);

  const refresh = async () => {
    setLoading(true);
    try {
      const [d, a] = await Promise.all([listDeliveries(), getAnalytics()]);
      setDeliveries(d.data);
      setAnalytics(a.data);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { refresh(); }, []);

  const onStatusChange = async (id, status) => {
    await updateDeliveryStatus(id, status);
    refresh();
  };

  const onDelete = async (id) => {
    if (!confirm('Delete this delivery?')) return;
    await deleteDelivery(id);
    refresh();
  };

  const onDeleteAll = async () => {
    if (deliveries.length === 0) return;
    if (!confirm(`Delete ALL ${deliveries.length} deliveries? This cannot be undone.`)) return;
    try {
      await deleteAllDeliveries();
      refresh();
    } catch (err) {
      alert('Failed to delete: ' + (err.response?.data?.detail || err.message));
    }
  };

  const chartData = analytics ? [
    { name: 'Pending', value: analytics.pending },
    { name: 'In Progress', value: analytics.in_progress },
    { name: 'Delivered', value: analytics.delivered },
  ] : [];

  if (loading) return <div className="container">Loading...</div>;

  return (
    <div className="container">
      <h2>Dashboard</h2>

      {analytics && (
        <div className="kpi-grid">
          <div className="card kpi">
            <div className="label">Total Deliveries</div>
            <div className="value">{analytics.total_deliveries}</div>
          </div>
          <div className="card kpi">
            <div className="label">Avg Delivery Time</div>
            <div className="value">{analytics.avg_delivery_time_minutes} min</div>
          </div>
          <div className="card kpi">
            <div className="label">Efficiency</div>
            <div className="value">{analytics.efficiency_percent}%</div>
          </div>
          <div className="card kpi">
            <div className="label">In Progress</div>
            <div className="value">{analytics.in_progress}</div>
          </div>
        </div>
      )}

      <div className="row" style={{ marginBottom: 24 }}>
        <div className="card" style={{ flex: 1 }}>
          <h3>Delivery Status</h3>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#2d3744" />
              <XAxis dataKey="name" stroke="#8a95a5" />
              <YAxis stroke="#8a95a5" />
              <Tooltip contentStyle={{ background: '#1a2028', border: '1px solid #2d3744' }} />
              <Bar dataKey="value" fill="#4f9eff" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
          <h3 style={{ margin: 0 }}>All Deliveries</h3>
          {deliveries.length > 0 && (
            <button
              onClick={onDeleteAll}
              style={{ background: '#f87171', padding: '8px 14px', fontSize: 13 }}
            >
              🗑 Delete All ({deliveries.length})
            </button>
          )}
        </div>
        {deliveries.length === 0 ? (
          <p style={{ color: 'var(--text-dim)' }}>
            No deliveries yet. <a href="/upload">Upload some</a> to get started.
          </p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>ID</th><th>Address</th><th>Coords</th>
                <th>ETA</th><th>Cluster</th><th>Status</th><th></th>
              </tr>
            </thead>
            <tbody>
              {deliveries.map(d => (
                <tr key={d.id}>
                  <td>#{d.id}</td>
                  <td>{d.address}</td>
                  <td>{d.latitude.toFixed(4)}, {d.longitude.toFixed(4)}</td>
                  <td>{d.eta_minutes ? `${d.eta_minutes} min` : '—'}</td>
                  <td>{d.cluster_id !== null && d.cluster_id !== undefined ? `#${d.cluster_id}` : '—'}</td>
                  <td>
                    <select
                      value={d.status}
                      onChange={(e) => onStatusChange(d.id, e.target.value)}
                      style={{ width: 'auto', padding: '4px 8px', fontSize: 12 }}
                    >
                      {STATUSES.map(s => <option key={s} value={s}>{s}</option>)}
                    </select>
                  </td>
                  <td>
                    <button className="secondary" onClick={() => onDelete(d.id)} style={{ padding: '4px 10px', fontSize: 12 }}>
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}