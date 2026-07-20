import { useState, useEffect } from "react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend
} from "recharts";
import "./AdminDashboard.css";
import { API_BASE_URL } from "../config";

function AdminDashboard({ token, onLogout }) {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [systemInfo, setSystemInfo] = useState(null);

  const fetchStatsAndInfo = async () => {
    setLoading(true);
    setError(null);
    try {
      const headers = { Authorization: `Bearer ${token}` };
      
      // Fetch stats
      const statsRes = await fetch(API_BASE_URL + "/admin/stats", { headers });
      if (statsRes.status === 401) {
        onLogout();
        return;
      }
      if (!statsRes.ok) {
        const errData = await statsRes.json();
        throw new Error(errData.detail || "Failed to fetch admin statistics");
      }
      const statsData = await statsRes.json();
      setStats(statsData);

      // Fetch version and uptime
      const versionRes = await fetch(API_BASE_URL + "/api/version", { headers });
      if (versionRes.ok) {
        const versionData = await versionRes.json();
        setSystemInfo(versionData);
      }
    } catch (err) {
      console.error(err);
      setError(err.message || "An error occurred while loading dashboard metrics.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStatsAndInfo();
  }, [token]);

  const formatUptime = (seconds) => {
    if (seconds === undefined || seconds === null) return "N/A";
    const d = Math.floor(seconds / (3600 * 24));
    const h = Math.floor((seconds % (3600 * 24)) / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = seconds % 60;
    
    const parts = [];
    if (d > 0) parts.push(`${d}d`);
    if (h > 0) parts.push(`${h}h`);
    if (m > 0) parts.push(`${m}m`);
    parts.push(`${s}s`);
    return parts.join(" ");
  };

  if (loading) {
    return (
      <div className="admin-loading-container">
        <div className="admin-spinner"></div>
        <p>Gathering system telemetry and dashboard metrics...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="admin-error-container">
        <div className="error-card">
          <h3>⚠️ Access Control Alert</h3>
          <p>{error}</p>
          <button className="retry-btn" onClick={fetchStatsAndInfo}>Retry Connection</button>
        </div>
      </div>
    );
  }

  const successRate = stats ? (stats.total_queries > 0 ? ((stats.success_queries / stats.total_queries) * 100).toFixed(1) : "0.0") : "0.0";

  return (
    <div className="admin-dashboard-container">
      <div className="admin-header-row">
        <div>
          <h1>⚙️ Platform Admin Panel</h1>
          <p className="subtitle">Real-time system telemetry and platform usage metrics</p>
        </div>
        <div className="header-actions">
          <button className="refresh-btn" onClick={fetchStatsAndInfo}>
            🔄 Refresh Analytics
          </button>
        </div>
      </div>

      {/* System Telemetry Row */}
      {systemInfo && (
        <div className="system-telemetry-banner">
          <div className="telemetry-item">
            <span className="telemetry-label">Uptime:</span>
            <span className="telemetry-value highlight">{formatUptime(systemInfo.uptime_seconds)}</span>
          </div>
          <div className="telemetry-item">
            <span className="telemetry-label">Version:</span>
            <span className="telemetry-value">v{systemInfo.version}</span>
          </div>
          <div className="telemetry-item">
            <span className="telemetry-label">Environment:</span>
            <span className="telemetry-value env-badge">{systemInfo.environment}</span>
          </div>
        </div>
      )}

      {/* KPI Cards Grid */}
      <div className="kpi-grid">
        <div className="kpi-card glassmorphic">
          <div className="kpi-icon users-icon">👥</div>
          <div className="kpi-content">
            <h3>Total Users</h3>
            <div className="kpi-val">{stats?.total_users ?? 0}</div>
            <p className="kpi-desc">Registered profiles</p>
          </div>
        </div>

        <div className="kpi-card glassmorphic">
          <div className="kpi-icon queries-icon">⚡</div>
          <div className="kpi-content">
            <h3>Total Queries</h3>
            <div className="kpi-val">{stats?.total_queries ?? 0}</div>
            <p className="kpi-desc">Executed globally</p>
          </div>
        </div>

        <div className="kpi-card glassmorphic">
          <div className="kpi-icon reports-icon">📊</div>
          <div className="kpi-content">
            <h3>Saved Reports</h3>
            <div className="kpi-val">{stats?.total_reports ?? 0}</div>
            <p className="kpi-desc">Active dashboards</p>
          </div>
        </div>

        <div className="kpi-card glassmorphic">
          <div className="kpi-icon favs-icon">⭐</div>
          <div className="kpi-content">
            <h3>Favorites</h3>
            <div className="kpi-val">{stats?.total_favorites ?? 0}</div>
            <p className="kpi-desc">Bookmarked queries</p>
          </div>
        </div>

        <div className="kpi-card glassmorphic">
          <div className="kpi-icon success-icon">✅</div>
          <div className="kpi-content">
            <h3>Query Success Rate</h3>
            <div className="kpi-val">{successRate}%</div>
            <p className="kpi-desc">{stats?.success_queries ?? 0} successful / {stats?.failed_queries ?? 0} failed</p>
          </div>
        </div>

        <div className="kpi-card glassmorphic">
          <div className="kpi-icon repair-icon">🔧</div>
          <div className="kpi-content">
            <h3>SQL Repair Success</h3>
            <div className="kpi-val">{stats?.repair_success_rate ?? 0.0}%</div>
            <p className="kpi-desc">{stats?.repair_successes ?? 0} solved / {stats?.repair_attempts ?? 0} attempts</p>
          </div>
        </div>
      </div>

      {/* Analytics Visualization Panel */}
      <div className="chart-panel glassmorphic">
        <h3>📈 Daily Executions & Telemetry Trends</h3>
        {stats?.daily_metrics && stats.daily_metrics.length > 0 ? (
          <div className="admin-chart-wrapper">
            <ResponsiveContainer width="100%" height={320}>
              <LineChart data={stats.daily_metrics} margin={{ top: 20, right: 30, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                <XAxis dataKey="date" stroke="rgba(255,255,255,0.4)" fontSize={12} tickLine={false} />
                <YAxis stroke="rgba(255,255,255,0.4)" fontSize={12} tickLine={false} />
                <Tooltip
                  contentStyle={{
                    background: "rgba(15, 23, 42, 0.9)",
                    border: "1px solid rgba(255,255,255,0.12)",
                    borderRadius: "8px",
                    color: "#f8fafc"
                  }}
                />
                <Legend wrapperStyle={{ paddingTop: "10px" }} />
                <Line
                  type="monotone"
                  dataKey="total"
                  name="Total Queries"
                  stroke="#3b82f6"
                  strokeWidth={3}
                  activeDot={{ r: 8 }}
                  dot={{ stroke: '#3b82f6', strokeWidth: 2, r: 4 }}
                />
                <Line
                  type="monotone"
                  dataKey="success"
                  name="Successful"
                  stroke="#10b981"
                  strokeWidth={2}
                  dot={{ r: 2 }}
                />
                <Line
                  type="monotone"
                  dataKey="failed"
                  name="Failed"
                  stroke="#ef4444"
                  strokeWidth={2}
                  dot={{ r: 2 }}
                />
                <Line
                  type="monotone"
                  dataKey="repair_attempts"
                  name="Repair Attempts"
                  stroke="#f59e0b"
                  strokeWidth={2}
                  strokeDasharray="5 5"
                  dot={{ r: 2 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <div className="no-chart-data">
            <p>No historical query execution data logged yet. Executed queries will trend here.</p>
          </div>
        )}
      </div>
    </div>
  );
}

export default AdminDashboard;
