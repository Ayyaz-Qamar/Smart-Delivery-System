/**
 * API client. Reads the JWT from localStorage and attaches it to every request.
 * Base URL can be overridden with VITE_API_URL.
 */
import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const api = axios.create({ baseURL: API_URL });

// Attach JWT to every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// 401 → kick to login
api.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('token');
      if (window.location.pathname !== '/login' && window.location.pathname !== '/signup') {
        window.location.href = '/login';
      }
    }
    return Promise.reject(err);
  }
);

// === Auth ===
export const signup = (data) => api.post('/auth/signup', data);
export const login = (email, password) => {
  const fd = new FormData();
  fd.append('username', email);
  fd.append('password', password);
  return api.post('/auth/login', fd);
};
export const getMe = () => api.get('/auth/me');

// === Deliveries ===
export const listDeliveries = () => api.get('/deliveries/');
export const createDelivery = (d) => api.post('/deliveries/', d);
export const uploadDeliveriesCSV = (file) => {
  const fd = new FormData();
  fd.append('file', file);
  return api.post('/deliveries/upload-locations', fd);
};
export const updateDeliveryStatus = (id, status) =>
  api.patch(`/deliveries/${id}/status`, { status });
export const deleteDelivery = (id) => api.delete(`/deliveries/${id}`);
export const deleteAllDeliveries = () => api.delete('/deliveries/all');
export const getAnalytics = () => api.get('/deliveries/analytics');

// === ML ===
export const predictETA = (payload) => api.post('/ml/predict-eta', payload);
export const clusterDeliveries = (delivery_ids, n_clusters) =>
  api.post('/ml/cluster-deliveries', { delivery_ids, n_clusters });
export const optimizeRoute = (payload) => api.post('/ml/optimize-route', payload);

// === Tracking ===
export const postLiveLocation = (loc) => api.post('/tracking/live-location', loc);
export const getLiveTracking = (driver_id) => api.get(`/tracking/get-live-tracking/${driver_id}`);

export const wsURL = (driverId) => {
  const base = API_URL.replace(/^http/, 'ws');
  return `${base}/tracking/ws/${driverId}`;
};

export { API_URL };