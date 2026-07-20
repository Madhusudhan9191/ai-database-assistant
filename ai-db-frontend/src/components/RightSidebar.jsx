import { useState } from "react";
import "./RightSidebar.css";

function RightSidebar({
  open,
  toggle,
  queryHistory,
  runPastQuery,
  clearHistory,
  onDeleteQuery,
  onDeleteBulkQueries,
}) {
  const [selectedIds, setSelectedIds] = useState([]);

  // Deduplicate queries by question text, keeping the most recent
  const uniqueQueries = [];
  const seen = new Set();

  for (const query of queryHistory || []) {
    const key = query.question?.toLowerCase().trim();
    if (key && !seen.has(key)) {
      seen.add(key);
      uniqueQueries.push(query);
    }
  }

  const handleCheckboxChange = (e, id) => {
    e.stopPropagation();
    if (e.target.checked) {
      setSelectedIds((prev) => [...prev, id]);
    } else {
      setSelectedIds((prev) => prev.filter((x) => x !== id));
    }
  };

  const handleDeleteSelected = (e) => {
    e.stopPropagation();
    if (selectedIds.length > 0 && onDeleteBulkQueries) {
      onDeleteBulkQueries(selectedIds);
      setSelectedIds([]);
    }
  };

  const handleDeleteOne = (e, id) => {
    e.stopPropagation();
    if (onDeleteQuery) {
      onDeleteQuery(id);
      setSelectedIds((prev) => prev.filter((x) => x !== id));
    }
  };

  return (
    <div className={`right-sidebar ${open ? "" : "closed"}`}>
      <button className="toggle-btn" onClick={toggle}>
        {open ? "→" : "←"}
      </button>

      {open && (
        <>
          <div className="sidebar-header">
            <h3>Past Queries</h3>
            {uniqueQueries.length > 0 && (
              <button
                className="clear-history-btn"
                onClick={clearHistory}
                title="Clear all past queries"
              >
                🗑️ Clear All
              </button>
            )}
          </div>

          {selectedIds.length > 0 && (
            <div className="bulk-actions-bar">
              <button className="bulk-delete-btn" onClick={handleDeleteSelected}>
                🗑️ Delete Selected ({selectedIds.length})
              </button>
            </div>
          )}

          {uniqueQueries.length > 0 ? (
            <div className="history-list">
              {uniqueQueries.map((query) => {
                const isChecked = selectedIds.includes(query.id);
                return (
                  <div
                    key={query.id}
                    className={`chat-history-item ${isChecked ? "selected" : ""}`}
                    onClick={() => runPastQuery(query.question)}
                    title={query.question}
                  >
                    <div className="history-item-left">
                      <input
                        type="checkbox"
                        checked={isChecked}
                        onChange={(e) => handleCheckboxChange(e, query.id)}
                        onClick={(e) => e.stopPropagation()}
                        className="history-checkbox"
                      />
                      <span className="history-text">
                        🔍 {query.question.length > 28
                          ? query.question.slice(0, 28) + "..."
                          : query.question}
                      </span>
                    </div>
                    <button
                      className="delete-item-btn"
                      onClick={(e) => handleDeleteOne(e, query.id)}
                      title="Delete query log"
                    >
                      &times;
                    </button>
                  </div>
                );
              })}
            </div>
          ) : (
            <p className="empty-history-text">No queries yet</p>
          )}
        </>
      )}
    </div>
  );
}

export default RightSidebar;