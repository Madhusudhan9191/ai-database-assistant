import "./TopNavbar.css";

function TopNavbar({ activeTab, setActiveTab, user }) {
  return (
    <div className="top-navbar">
      <h2>AI Database Assistant</h2>
      <div className="navbar-tabs">
        <button
          className={`nav-tab ${activeTab === "chat" ? "active" : ""}`}
          onClick={() => setActiveTab("chat")}
        >
          💬 Chat
        </button>
        <button
          className={`nav-tab ${activeTab === "dashboard" ? "active" : ""}`}
          onClick={() => setActiveTab("dashboard")}
        >
          📊 Dashboard
        </button>
        {user?.is_admin && (
          <button
            className={`nav-tab ${activeTab === "admin" ? "active" : ""}`}
            onClick={() => setActiveTab("admin")}
          >
            ⚙️ Admin Panel
          </button>
        )}
      </div>
    </div>
  );
}

export default TopNavbar;