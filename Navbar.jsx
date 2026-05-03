import { NavLink, useNavigate } from 'react-router-dom';

export default function Navbar() {
  const navigate = useNavigate();
  const logout = () => {
    localStorage.removeItem('token');
    navigate('/login');
  };

  return (
    <nav className="navbar">
      <div className="brand">🚚 Smart Delivery</div>
      <div className="links">
        <NavLink to="/" end>Dashboard</NavLink>
        <NavLink to="/upload">Upload</NavLink>
        <NavLink to="/map">Live Map</NavLink>
        <button className="secondary" onClick={logout}>Logout</button>
      </div>
    </nav>
  );
}
