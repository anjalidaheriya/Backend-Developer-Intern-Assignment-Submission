import React, { useState, useEffect, createContext, useContext } from 'react';
import axios from 'axios';
import './App.css';

const API_URL = process.env.REACT_APP_BACKEND_URL;

// Configure axios defaults
axios.defaults.withCredentials = true;

// Auth Context
const AuthContext = createContext(null);

function formatApiError(detail) {
  if (detail == null) return "Something went wrong. Please try again.";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail))
    return detail.map((e) => (e && typeof e.msg === "string" ? e.msg : JSON.stringify(e))).filter(Boolean).join(" ");
  if (detail && typeof detail.msg === "string") return detail.msg;
  return String(detail);
}

// Auth Provider
function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    checkAuth();
  }, []);

  const checkAuth = async () => {
    try {
      const { data } = await axios.get(`${API_URL}/api/auth/me`);
      setUser(data);
    } catch (e) {
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  const login = async (email, password) => {
    const { data } = await axios.post(`${API_URL}/api/auth/login`, { email, password });
    setUser(data.user);
    return data;
  };

  const logout = async () => {
    await axios.post(`${API_URL}/api/auth/logout`);
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, checkAuth }}>
      {children}
    </AuthContext.Provider>
  );
}

const useAuth = () => useContext(AuthContext);

// Login Form
function LoginForm() {
  const [email, setEmail] = useState('admin@example.com');
  const [password, setPassword] = useState('admin123');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const { login } = useAuth();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSubmitting(true);
    try {
      await login(email, password);
    } catch (err) {
      setError(formatApiError(err.response?.data?.detail));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="login-container" data-testid="login-container">
      <div className="login-card">
        <h1>Finance API</h1>
        <p className="subtitle">Login to access the dashboard</p>
        
        <form onSubmit={handleSubmit} data-testid="login-form">
          <div className="form-group">
            <label>Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              data-testid="email-input"
              required
            />
          </div>
          <div className="form-group">
            <label>Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              data-testid="password-input"
              required
            />
          </div>
          {error && <div className="error" data-testid="login-error">{error}</div>}
          <button type="submit" disabled={submitting} data-testid="login-submit">
            {submitting ? 'Logging in...' : 'Login'}
          </button>
        </form>
        
        <div className="api-docs-link">
          <a href={`${API_URL}/api/docs`} target="_blank" rel="noopener noreferrer">
            View API Documentation (Swagger)
          </a>
        </div>
      </div>
    </div>
  );
}

// Dashboard
function Dashboard() {
  const { user, logout } = useAuth();
  const [activeTab, setActiveTab] = useState('overview');
  const [summary, setSummary] = useState(null);
  const [records, setRecords] = useState([]);
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    fetchData();
  }, [activeTab]);

  const fetchData = async () => {
    setLoading(true);
    setError('');
    try {
      if (activeTab === 'overview') {
        const { data } = await axios.get(`${API_URL}/api/dashboard/summary`);
        setSummary(data);
      } else if (activeTab === 'records') {
        const { data } = await axios.get(`${API_URL}/api/records`);
        setRecords(data.records);
      } else if (activeTab === 'users' && user?.role === 'admin') {
        const { data } = await axios.get(`${API_URL}/api/users`);
        setUsers(data.users);
      }
    } catch (err) {
      setError(formatApiError(err.response?.data?.detail));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="dashboard" data-testid="dashboard">
      <header className="header">
        <h1>Finance Dashboard</h1>
        <div className="user-info">
          <span className="user-badge" data-testid="user-role">{user?.role?.toUpperCase()}</span>
          <span data-testid="user-name">{user?.name}</span>
          <button onClick={logout} className="logout-btn" data-testid="logout-btn">Logout</button>
        </div>
      </header>

      <nav className="tabs">
        <button 
          className={activeTab === 'overview' ? 'active' : ''} 
          onClick={() => setActiveTab('overview')}
          data-testid="tab-overview"
        >
          Overview
        </button>
        <button 
          className={activeTab === 'records' ? 'active' : ''} 
          onClick={() => setActiveTab('records')}
          data-testid="tab-records"
        >
          Records
        </button>
        {user?.role === 'admin' && (
          <button 
            className={activeTab === 'users' ? 'active' : ''} 
            onClick={() => setActiveTab('users')}
            data-testid="tab-users"
          >
            Users
          </button>
        )}
        <button 
          className={activeTab === 'api' ? 'active' : ''} 
          onClick={() => setActiveTab('api')}
          data-testid="tab-api"
        >
          API Info
        </button>
      </nav>

      <main className="content">
        {error && <div className="error-banner">{error}</div>}
        
        {activeTab === 'overview' && (
          <OverviewTab summary={summary} loading={loading} onRefresh={fetchData} />
        )}
        {activeTab === 'records' && (
          <RecordsTab records={records} loading={loading} onRefresh={fetchData} userRole={user?.role} />
        )}
        {activeTab === 'users' && user?.role === 'admin' && (
          <UsersTab users={users} loading={loading} onRefresh={fetchData} />
        )}
        {activeTab === 'api' && <APIInfoTab />}
      </main>
    </div>
  );
}

// Overview Tab
function OverviewTab({ summary, loading, onRefresh }) {
  if (loading) return <div className="loading">Loading dashboard...</div>;
  
  return (
    <div className="overview" data-testid="overview-tab">
      <div className="stats-grid">
        <div className="stat-card income" data-testid="total-income">
          <h3>Total Income</h3>
          <p className="value">${summary?.total_income?.toLocaleString() || 0}</p>
        </div>
        <div className="stat-card expense" data-testid="total-expenses">
          <h3>Total Expenses</h3>
          <p className="value">${summary?.total_expenses?.toLocaleString() || 0}</p>
        </div>
        <div className="stat-card balance" data-testid="net-balance">
          <h3>Net Balance</h3>
          <p className={`value ${(summary?.net_balance || 0) >= 0 ? 'positive' : 'negative'}`}>
            ${summary?.net_balance?.toLocaleString() || 0}
          </p>
        </div>
        <div className="stat-card records" data-testid="record-count">
          <h3>Total Records</h3>
          <p className="value">{summary?.record_count || 0}</p>
        </div>
      </div>

      <div className="charts-row">
        <div className="chart-card">
          <h3>Income by Category</h3>
          {summary?.income_by_category?.length > 0 ? (
            <ul className="category-list">
              {summary.income_by_category.map((cat, i) => (
                <li key={i}>
                  <span className="cat-name">{cat.category}</span>
                  <span className="cat-value">${cat.total.toLocaleString()}</span>
                </li>
              ))}
            </ul>
          ) : <p className="no-data">No income data</p>}
        </div>
        <div className="chart-card">
          <h3>Expenses by Category</h3>
          {summary?.expenses_by_category?.length > 0 ? (
            <ul className="category-list">
              {summary.expenses_by_category.map((cat, i) => (
                <li key={i}>
                  <span className="cat-name">{cat.category}</span>
                  <span className="cat-value">${cat.total.toLocaleString()}</span>
                </li>
              ))}
            </ul>
          ) : <p className="no-data">No expense data</p>}
        </div>
      </div>

      <div className="recent-section">
        <h3>Recent Activity</h3>
        {summary?.recent_records?.length > 0 ? (
          <table className="data-table" data-testid="recent-records-table">
            <thead>
              <tr>
                <th>Date</th>
                <th>Type</th>
                <th>Category</th>
                <th>Amount</th>
                <th>Description</th>
              </tr>
            </thead>
            <tbody>
              {summary.recent_records.slice(0, 5).map((record) => (
                <tr key={record.id}>
                  <td>{record.date}</td>
                  <td className={record.type}>{record.type}</td>
                  <td>{record.category}</td>
                  <td className={record.type}>${record.amount.toLocaleString()}</td>
                  <td>{record.description || '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : <p className="no-data">No records yet</p>}
      </div>
    </div>
  );
}

// Records Tab
function RecordsTab({ records, loading, onRefresh, userRole }) {
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({
    amount: '', type: 'expense', category: 'other', date: new Date().toISOString().split('T')[0], description: ''
  });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  const canCreate = userRole === 'admin' || userRole === 'analyst';

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setError('');
    try {
      await axios.post(`${API_URL}/api/records`, {
        ...formData,
        amount: parseFloat(formData.amount)
      });
      setShowForm(false);
      setFormData({ amount: '', type: 'expense', category: 'other', date: new Date().toISOString().split('T')[0], description: '' });
      onRefresh();
    } catch (err) {
      setError(formatApiError(err.response?.data?.detail));
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this record?')) return;
    try {
      await axios.delete(`${API_URL}/api/records/${id}`);
      onRefresh();
    } catch (err) {
      alert(formatApiError(err.response?.data?.detail));
    }
  };

  if (loading) return <div className="loading">Loading records...</div>;

  const categories = ['salary', 'investment', 'freelance', 'rent', 'utilities', 'groceries', 'transportation', 'entertainment', 'healthcare', 'education', 'shopping', 'travel', 'food', 'subscriptions', 'other'];

  return (
    <div className="records-tab" data-testid="records-tab">
      <div className="tab-header">
        <h2>Financial Records</h2>
        {canCreate && (
          <button onClick={() => setShowForm(!showForm)} data-testid="add-record-btn">
            {showForm ? 'Cancel' : '+ Add Record'}
          </button>
        )}
      </div>

      {showForm && canCreate && (
        <form onSubmit={handleSubmit} className="record-form" data-testid="record-form">
          <div className="form-row">
            <div className="form-group">
              <label>Amount</label>
              <input type="number" step="0.01" min="0.01" value={formData.amount} 
                onChange={(e) => setFormData({...formData, amount: e.target.value})} 
                data-testid="record-amount" required />
            </div>
            <div className="form-group">
              <label>Type</label>
              <select value={formData.type} onChange={(e) => setFormData({...formData, type: e.target.value})} data-testid="record-type">
                <option value="income">Income</option>
                <option value="expense">Expense</option>
              </select>
            </div>
            <div className="form-group">
              <label>Category</label>
              <select value={formData.category} onChange={(e) => setFormData({...formData, category: e.target.value})} data-testid="record-category">
                {categories.map(c => <option key={c} value={c}>{c}</option>)}
              </select>
            </div>
            <div className="form-group">
              <label>Date</label>
              <input type="date" value={formData.date} onChange={(e) => setFormData({...formData, date: e.target.value})} data-testid="record-date" required />
            </div>
          </div>
          <div className="form-group">
            <label>Description</label>
            <input type="text" value={formData.description} onChange={(e) => setFormData({...formData, description: e.target.value})} data-testid="record-description" />
          </div>
          {error && <div className="error">{error}</div>}
          <button type="submit" disabled={submitting} data-testid="record-submit">
            {submitting ? 'Creating...' : 'Create Record'}
          </button>
        </form>
      )}

      {records.length > 0 ? (
        <table className="data-table" data-testid="records-table">
          <thead>
            <tr>
              <th>Date</th>
              <th>Type</th>
              <th>Category</th>
              <th>Amount</th>
              <th>Description</th>
              {canCreate && <th>Actions</th>}
            </tr>
          </thead>
          <tbody>
            {records.map((record) => (
              <tr key={record.id}>
                <td>{record.date}</td>
                <td className={record.type}>{record.type}</td>
                <td>{record.category}</td>
                <td className={record.type}>${record.amount.toLocaleString()}</td>
                <td>{record.description || '-'}</td>
                {canCreate && (
                  <td>
                    <button className="delete-btn" onClick={() => handleDelete(record.id)} data-testid={`delete-record-${record.id}`}>Delete</button>
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      ) : <p className="no-data">No records found. {canCreate ? 'Add your first record!' : ''}</p>}
    </div>
  );
}

// Users Tab (Admin only)
function UsersTab({ users, loading, onRefresh }) {
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({ email: '', password: '', name: '', role: 'viewer' });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setError('');
    try {
      await axios.post(`${API_URL}/api/users`, formData);
      setShowForm(false);
      setFormData({ email: '', password: '', name: '', role: 'viewer' });
      onRefresh();
    } catch (err) {
      setError(formatApiError(err.response?.data?.detail));
    } finally {
      setSubmitting(false);
    }
  };

  const handleStatusChange = async (userId, newStatus) => {
    try {
      await axios.put(`${API_URL}/api/users/${userId}`, { status: newStatus });
      onRefresh();
    } catch (err) {
      alert(formatApiError(err.response?.data?.detail));
    }
  };

  if (loading) return <div className="loading">Loading users...</div>;

  return (
    <div className="users-tab" data-testid="users-tab">
      <div className="tab-header">
        <h2>User Management</h2>
        <button onClick={() => setShowForm(!showForm)} data-testid="add-user-btn">
          {showForm ? 'Cancel' : '+ Add User'}
        </button>
      </div>

      {showForm && (
        <form onSubmit={handleSubmit} className="user-form" data-testid="user-form">
          <div className="form-row">
            <div className="form-group">
              <label>Email</label>
              <input type="email" value={formData.email} onChange={(e) => setFormData({...formData, email: e.target.value})} data-testid="user-email" required />
            </div>
            <div className="form-group">
              <label>Password</label>
              <input type="password" value={formData.password} onChange={(e) => setFormData({...formData, password: e.target.value})} data-testid="user-password" required minLength={6} />
            </div>
            <div className="form-group">
              <label>Name</label>
              <input type="text" value={formData.name} onChange={(e) => setFormData({...formData, name: e.target.value})} data-testid="user-name" required minLength={2} />
            </div>
            <div className="form-group">
              <label>Role</label>
              <select value={formData.role} onChange={(e) => setFormData({...formData, role: e.target.value})} data-testid="user-role">
                <option value="viewer">Viewer</option>
                <option value="analyst">Analyst</option>
                <option value="admin">Admin</option>
              </select>
            </div>
          </div>
          {error && <div className="error">{error}</div>}
          <button type="submit" disabled={submitting} data-testid="user-submit">
            {submitting ? 'Creating...' : 'Create User'}
          </button>
        </form>
      )}

      <table className="data-table" data-testid="users-table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Email</th>
            <th>Role</th>
            <th>Status</th>
            <th>Created</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {users.map((u) => (
            <tr key={u.id}>
              <td>{u.name}</td>
              <td>{u.email}</td>
              <td><span className={`role-badge ${u.role}`}>{u.role}</span></td>
              <td><span className={`status-badge ${u.status}`}>{u.status}</span></td>
              <td>{new Date(u.created_at).toLocaleDateString()}</td>
              <td>
                {u.status === 'active' ? (
                  <button className="deactivate-btn" onClick={() => handleStatusChange(u.id, 'inactive')} data-testid={`deactivate-${u.id}`}>Deactivate</button>
                ) : (
                  <button className="activate-btn" onClick={() => handleStatusChange(u.id, 'active')} data-testid={`activate-${u.id}`}>Activate</button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// API Info Tab
function APIInfoTab() {
  const [info, setInfo] = useState(null);

  useEffect(() => {
    axios.get(`${API_URL}/api/info`).then(({ data }) => setInfo(data));
  }, []);

  return (
    <div className="api-info-tab" data-testid="api-info-tab">
      <div className="tab-header">
        <h2>API Documentation</h2>
        <a href={`${API_URL}/api/docs`} target="_blank" rel="noopener noreferrer" className="swagger-link">
          Open Swagger UI
        </a>
      </div>

      <div className="api-overview">
        <p>{info?.description}</p>
      </div>

      <div className="roles-section">
        <h3>User Roles & Permissions</h3>
        <table className="roles-table">
          <thead>
            <tr>
              <th>Role</th>
              <th>Description</th>
            </tr>
          </thead>
          <tbody>
            <tr><td><span className="role-badge viewer">viewer</span></td><td>Can view dashboard and records</td></tr>
            <tr><td><span className="role-badge analyst">analyst</span></td><td>Can view + manage records</td></tr>
            <tr><td><span className="role-badge admin">admin</span></td><td>Full access including user management</td></tr>
          </tbody>
        </table>
      </div>

      {info?.endpoints && Object.entries(info.endpoints).map(([category, endpoints]) => (
        <div className="endpoint-section" key={category}>
          <h3>{category.charAt(0).toUpperCase() + category.slice(1)}</h3>
          <ul className="endpoint-list">
            {Object.entries(endpoints).map(([path, desc]) => (
              <li key={path}>
                <code>{path}</code>
                <span>{desc}</span>
              </li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
}

// Main App
function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}

function AppContent() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="loading-screen">
        <div className="spinner"></div>
        <p>Loading...</p>
      </div>
    );
  }

  return user ? <Dashboard /> : <LoginForm />;
}

export default App;
