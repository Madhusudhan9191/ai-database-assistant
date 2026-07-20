import "./LeftSidebar.css";
import ConnectionManager from "./ConnectionManager";
import Settings from "./Settings";

const QUERY_TEMPLATES = [
  {
    name: "Monthly Revenue",
    question: "Show the total rent payment amount collected in each month of 2025 to see the monthly trend",
    category: "Finance",
    icon: "📈"
  },
  {
    name: "Occupancy Analysis",
    question: "Show the count of properties by property type (Men, Women, Co-Living) to see their proportion",
    category: "Operations",
    icon: "🏠"
  },
  {
    name: "Expense Breakdown",
    question: "what is the totel expences in each catagery? show amounts",
    category: "Finance",
    icon: "💰"
  },
  {
    name: "Maintenance Summary",
    question: "Show the count of maintenance requests in each status (Open, Resolved, In Progress, Closed)",
    category: "Maintenance",
    icon: "⚠️"
  }
];

function LeftSidebar({
  open,
  toggle,
  addAssistantMessage,
  settings,
  setSettings,
  favorites = [],
  onRemoveFavorite,
  onSelectQuery,
  setActiveTab,
  user,
  onLogout,
  token,
  onConnectionChange
}) {

  const handleQueryClick = (questionText) => {
    if (setActiveTab) setActiveTab("chat");
    if (onSelectQuery) onSelectQuery(questionText);
  };

  return (
    <div className={`left-sidebar ${open ? "" : "closed"}`}>
      <button className="toggle-btn" onClick={toggle}>
        ☰
      </button>

      {open && (
        <div className="sidebar-scrollable-content">
          <h2>AI DB Assistant</h2>

          <div className="user-profile-section">
            <div className="user-avatar">
              {user?.username ? user.username.charAt(0).toUpperCase() : "U"}
            </div>
            <div className="user-details">
              <div className="user-name">
                {user?.username || "Guest"}
                {user?.is_admin && <span className="admin-badge" title="Administrator">👑 Admin</span>}
              </div>
              <div className="user-email">{user?.email || ""}</div>
            </div>
            <button className="logout-btn" onClick={onLogout} title="Log Out">
              🚪 Logout
            </button>
          </div>

          <ConnectionManager
            addAssistantMessage={addAssistantMessage}
            setActiveTab={setActiveTab}
            token={token}
            onConnectionChange={onConnectionChange}
          />

          {/* Favorites Section */}
          <div className="sidebar-section">
            <h3>⭐ Favorite Queries</h3>
            {favorites.length > 0 ? (
              <div className="favorites-list">
                {favorites.map((fav) => (
                  <div key={fav.id} className="sidebar-item fav-item">
                    <span
                      className="item-text"
                      onClick={() => handleQueryClick(fav.question)}
                      title={fav.question}
                    >
                      ❤️ {fav.question.length > 28 ? fav.question.slice(0, 28) + "..." : fav.question}
                    </span>
                    <button
                      className="delete-fav-btn"
                      onClick={() => onRemoveFavorite(fav.id)}
                      title="Remove from favorites"
                    >
                      &times;
                    </button>
                  </div>
                ))}
              </div>
            ) : (
              <p className="empty-text">No favorites added yet.</p>
            )}
          </div>

          {/* Templates Section */}
          <div className="sidebar-section">
            <h3>📋 Example Templates</h3>
            <div className="templates-list">
              {QUERY_TEMPLATES.map((tpl, i) => (
                <div
                  key={i}
                  className="sidebar-item template-item"
                  onClick={() => handleQueryClick(tpl.question)}
                  title={tpl.question}
                >
                  <span className="template-icon">{tpl.icon}</span>
                  <div className="template-info">
                    <span className="template-name">{tpl.name}</span>
                    <span className="template-category">{tpl.category}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
          
          <Settings
            settings={settings}
            setSettings={setSettings}
          />
        </div>
      )}
    </div>
  );
}

export default LeftSidebar;