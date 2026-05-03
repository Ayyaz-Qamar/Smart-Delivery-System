import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { signup, login } from '../api';

export default function Signup() {
  const [form, setForm] = useState({ email: '', password: '', full_name: '', role: 'business' });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const update = (k, v) => setForm({ ...form, [k]: v });

  const submit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await signup(form);
      const res = await login(form.email, form.password);
      localStorage.setItem('token', res.data.access_token);
      navigate('/');
      window.location.reload();
    } catch (err) {
      setError(err.response?.data?.detail || 'Signup failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="card auth-card">
        <h1>Create account</h1>
        <p>Get started in under a minute.</p>
        <form onSubmit={submit}>
          <div className="field">
            <label>Full name</label>
            <input value={form.full_name} onChange={(e) => update('full_name', e.target.value)} />
          </div>
          <div className="field">
            <label>Email</label>
            <input type="email" value={form.email} onChange={(e) => update('email', e.target.value)} required />
          </div>
          <div className="field">
            <label>Password (min 8 chars)</label>
            <input type="password" minLength={8} value={form.password} onChange={(e) => update('password', e.target.value)} required />
          </div>
          <div className="field">
            <label>Role</label>
            <select value={form.role} onChange={(e) => update('role', e.target.value)}>
              <option value="business">Business</option>
              <option value="driver">Driver</option>
              <option value="admin">Admin</option>
            </select>
          </div>
          <button type="submit" className="submit" disabled={loading}>
            {loading ? 'Creating...' : 'Create account'}
          </button>
          {error && <div className="error">{error}</div>}
        </form>
        <div className="switch">
          Already have an account? <Link to="/login">Sign in</Link>
        </div>
      </div>
    </div>
  );
}
