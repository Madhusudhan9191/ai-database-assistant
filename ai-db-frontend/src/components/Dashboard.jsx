import { useState, useEffect, useCallback } from "react";
import "./Dashboard.css";
import AnalyticsChart from "./AnalyticsChart";
import { API_BASE_URL } from "../config";

function Dashboard({ token, onLogout, dbConnectionVersion }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchDashboardData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await fetch(API_BASE_URL + "/dashboard/summary", {
        headers: { "Authorization": `Bearer ${token}` }
      });
      if (res.status === 401) {
        if (onLogout) onLogout();
        return;
      }
      if (!res.ok) {
        throw new Error("Failed to fetch dashboard summary from backend.");
      }
      const json = await res.json();
      setData(json);
    } catch (err) {
      setError(err.message || "Could not connect to backend.");
    } finally {
      setLoading(false);
    }
  }, [token, onLogout]);

  useEffect(() => {
    if (token) {
      fetchDashboardData();
    }
  }, [token, fetchDashboardData, dbConnectionVersion]);

  if (loading) {
    return (
      <div className="dashboard-loading">
        <div className="spinner"></div>
        <p>Analyzing database & building portfolio summary...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="dashboard-error">
        <h3>⚠️ Dashboard Loading Error</h3>
        <p>{error}</p>
        <button onClick={fetchDashboardData} className="retry-btn">
          Retry Connection
        </button>
      </div>
    );
  }

  const { kpis, charts, saved_reports = [], last_updated } = data;

  const handleDeleteReport = async (id) => {
    try {
      const res = await fetch(`${API_BASE_URL}/saved-reports/${id}`, {
        method: "DELETE",
        headers: { "Authorization": `Bearer ${token}` }
      });
      if (res.status === 401) {
        if (onLogout) onLogout();
        return;
      }
      if (res.ok) {
        setData((prev) => ({
          ...prev,
          saved_reports: prev.saved_reports.filter((r) => r.id !== id)
        }));
      }
    } catch (err) {
      console.error("Failed to delete report:", err);
    }
  };

  const formatCurrency = (val) => {
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      maximumFractionDigits: 0,
    }).format(val);
  };

  return (
    <div className="dashboard-container">
      <div className="dashboard-header">
        <div>
          <h1>Portfolio Analytics</h1>
          <p className="subtitle">Real-time business performance metrics</p>
        </div>
        <div className="update-status">
          <span>Last Updated: {last_updated}</span>
          <button onClick={fetchDashboardData} className="refresh-btn" title="Refresh Dashboard">
            🔄
          </button>
        </div>
      </div>

      {/* KPI Cards Grid */}
      <div className="dashboard-kpi-grid">
        <div className="db-kpi-card kpi-revenue">
          <div className="kpi-icon">💰</div>
          <div className="kpi-details">
            <span className="kpi-title">Total Revenue</span>
            <span className="kpi-value">{formatCurrency(kpis.total_revenue)}</span>
          </div>
        </div>

        <div className="db-kpi-card kpi-occupancy">
          <div className="kpi-icon">🏢</div>
          <div className="kpi-details">
            <span className="kpi-title">Occupancy Rate</span>
            <span className="kpi-value">{kpis.occupancy_rate}%</span>
          </div>
        </div>

        <div className="db-kpi-card kpi-tenants">
          <div className="kpi-icon">👥</div>
          <div className="kpi-details">
            <span className="kpi-title">Active Tenants</span>
            <span className="kpi-value">{kpis.active_tenants}</span>
          </div>
        </div>

        <div className="db-kpi-card kpi-issues">
          <div className="kpi-icon">🛠️</div>
          <div className="kpi-details">
            <span className="kpi-title">Open Maintenance Issues</span>
            <span className="kpi-value">{kpis.open_issues}</span>
          </div>
        </div>
      </div>

      {/* Visual Analytics Chart Grid */}
      <div className="dashboard-charts-grid">
        <div className="db-chart-container">
          <h3>📈 Revenue Growth Monthly Trend</h3>
          <div className="chart-wrapper">
            {charts.monthly_trend?.data?.length > 0 ? (
              <AnalyticsChart chartData={charts.monthly_trend} />
            ) : (
              <div className="no-chart-data">No revenue data available.</div>
            )}
          </div>
        </div>

        <div className="db-chart-container">
          <h3>💸 Operations Expenses by Category</h3>
          <div className="chart-wrapper">
            {charts.category_expenses?.data?.length > 0 ? (
              <AnalyticsChart chartData={charts.category_expenses} />
            ) : (
              <div className="no-chart-data">No expense data available.</div>
            )}
          </div>
        </div>

        <div className="db-chart-container">
          <h3>🏘️ Property Occupancy Rate (%)</h3>
          <div className="chart-wrapper">
            {charts.property_occupancy?.data?.length > 0 ? (
              <AnalyticsChart chartData={charts.property_occupancy} />
            ) : (
              <div className="no-chart-data">No occupancy data available.</div>
            )}
          </div>
        </div>

        <div className="db-chart-container">
          <h3>⚠️ Maintenance Requests by Priority</h3>
          <div className="chart-wrapper">
            {charts.maintenance_priorities?.data?.length > 0 ? (
              <AnalyticsChart chartData={charts.maintenance_priorities} />
            ) : (
              <div className="no-chart-data">No maintenance request data available.</div>
            )}
          </div>
        </div>
      </div>

      {/* Dynamic Saved Reports Grid */}
      {saved_reports.length > 0 && (
        <div className="saved-reports-section" style={{ marginTop: "40px" }}>
          <h2 style={{ fontSize: "20px", fontWeight: "700", marginBottom: "20px", color: "#60a5fa" }}>
            ⭐ Saved Reports
          </h2>
          <div className="dashboard-charts-grid">
            {saved_reports.map((report) => (
              <div key={report.id} className="db-chart-container saved-report-card">
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
                  <h3 style={{ margin: 0, fontSize: "15px", fontWeight: "600" }}>⭐ {report.report_name}</h3>
                  <button
                    onClick={() => handleDeleteReport(report.id)}
                    style={{
                      background: "rgba(239, 68, 68, 0.1)",
                      border: "1px solid rgba(239, 68, 68, 0.2)",
                      color: "#ef4444",
                      padding: "4px 8px",
                      borderRadius: "6px",
                      fontSize: "11px",
                      cursor: "pointer",
                      fontWeight: "600"
                    }}
                    title="Delete saved report"
                  >
                    🗑️ Delete
                  </button>
                </div>
                <p style={{ margin: "0 0 16px 0", fontSize: "12.5px", color: "var(--text-secondary)", fontStyle: "italic" }}>
                  Question: "{report.question}"
                </p>
                <div className="chart-wrapper">
                  {report.chart_data?.data?.length > 0 ? (
                    <AnalyticsChart chartData={report.chart_data} />
                  ) : (
                    <div className="no-chart-data">
                      {report.chart_data?.error ? `Error: ${report.chart_data.error}` : "No data retrieved."}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default Dashboard;
