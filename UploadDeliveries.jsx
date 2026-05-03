import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { createDelivery, uploadDeliveriesCSV } from '../api';

export default function UploadDeliveries() {
  const [form, setForm] = useState({ address: '', latitude: '', longitude: '', package_weight: 1.0, priority: 1 });
  const [csvFile, setCsvFile] = useState(null);
  const [msg, setMsg] = useState({ text: '', isError: false });
  const navigate = useNavigate();

  const update = (k, v) => setForm({ ...form, [k]: v });

  const submitSingle = async (e) => {
    e.preventDefault();
    try {
      await createDelivery({
        ...form,
        latitude: parseFloat(form.latitude),
        longitude: parseFloat(form.longitude),
        package_weight: parseFloat(form.package_weight),
        priority: parseInt(form.priority),
      });
      setMsg({ text: 'Delivery added!', isError: false });
      setForm({ address: '', latitude: '', longitude: '', package_weight: 1.0, priority: 1 });
    } catch (err) {
      setMsg({ text: err.response?.data?.detail || 'Failed', isError: true });
    }
  };

  const submitCSV = async (e) => {
    e.preventDefault();
    if (!csvFile) return;
    try {
      const res = await uploadDeliveriesCSV(csvFile);
      setMsg({ text: `Uploaded ${res.data.length} deliveries`, isError: false });
      setCsvFile(null);
      setTimeout(() => navigate('/'), 1500);
    } catch (err) {
      setMsg({ text: err.response?.data?.detail || 'Upload failed', isError: true });
    }
  };

  return (
    <div className="container">
      <h2>Upload Deliveries</h2>

      <div className="row">
        <div className="card">
          <h3>Bulk upload (CSV)</h3>
          <p style={{ fontSize: 13, color: 'var(--text-dim)', marginBottom: 16 }}>
            Required columns: <code>address, latitude, longitude</code><br />
            Optional: <code>package_weight, priority</code>
          </p>
          <form onSubmit={submitCSV}>
            <input
              type="file"
              accept=".csv"
              onChange={(e) => setCsvFile(e.target.files[0])}
              style={{ marginBottom: 12 }}
            />
            <button type="submit" disabled={!csvFile}>Upload CSV</button>
          </form>
        </div>

        <div className="card">
          <h3>Add single delivery</h3>
          <form onSubmit={submitSingle}>
            <div style={{ marginBottom: 10 }}>
              <input placeholder="Address" value={form.address} onChange={(e) => update('address', e.target.value)} required />
            </div>
            <div style={{ display: 'flex', gap: 10, marginBottom: 10 }}>
              <input placeholder="Latitude" type="number" step="any" value={form.latitude} onChange={(e) => update('latitude', e.target.value)} required />
              <input placeholder="Longitude" type="number" step="any" value={form.longitude} onChange={(e) => update('longitude', e.target.value)} required />
            </div>
            <div style={{ display: 'flex', gap: 10, marginBottom: 12 }}>
              <input placeholder="Weight (kg)" type="number" step="0.1" value={form.package_weight} onChange={(e) => update('package_weight', e.target.value)} />
              <select value={form.priority} onChange={(e) => update('priority', e.target.value)}>
                <option value={1}>Normal priority</option>
                <option value={2}>High priority</option>
              </select>
            </div>
            <button type="submit">Add delivery</button>
          </form>
        </div>
      </div>

      {msg.text && (
        <div className={msg.isError ? 'error' : 'success'} style={{ marginTop: 16 }}>
          {msg.text}
        </div>
      )}
    </div>
  );
}
