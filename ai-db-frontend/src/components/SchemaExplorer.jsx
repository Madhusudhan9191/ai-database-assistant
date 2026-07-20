import { useState, useEffect } from "react";
import axios from "axios";
import { API_BASE_URL } from "../config";

function SchemaExplorer({ tables, addAssistantMessage, setActiveTab, token }) {
  const [expandedTable, setExpandedTable] = useState(null);
  const [columns, setColumns] = useState({});
  const [counts, setCounts] = useState({});
  const [searchTerm, setSearchTerm] = useState("");

  useEffect(() => {
    const loadCounts = async () => {
      if (!token) return;
      try {
        const response = await axios.get(
          API_BASE_URL + "/table-counts",
          {
            headers: { "Authorization": `Bearer ${token}` }
          }
        );
        setCounts(response.data);
      } catch (error) {
        console.error("Failed to load counts", error);
      }
    };

    loadCounts();
  }, [token]);

  const loadColumns = async (table) => {
    if (expandedTable === table) {
      setExpandedTable(null);
      return;
    }

    try {
      if (!columns[table]) {
        const response = await axios.get(
          `${API_BASE_URL}/table-columns/${table}`,
          {
            headers: { "Authorization": `Bearer ${token}` }
          }
        );

        setColumns((prev) => ({
          ...prev,
          [table]: response.data.columns
        }));
      }

      setExpandedTable(table);
    } catch (error) {
      console.error("Failed to load columns", error);
    }
  };

  const loadSampleData = async (table) => {
    try {
      if (setActiveTab) {
        setActiveTab("chat");
      }

      const response = await axios.get(
        `${API_BASE_URL}/table-data/${table}`,
        {
          headers: { "Authorization": `Bearer ${token}` }
        }
      );

      addAssistantMessage({
        id: Date.now(),
        role: "assistant",
        generated_sql: `SELECT * FROM ${table} LIMIT 10`,
        data: response.data.data,
        insights: `Showing sample data from ${table}.`,
        show_chart: false,
      });
    } catch (error) {
      console.error(error);
    }
  };

  return (
    <div className=" schema-section">
      <h4>📂 Schema Explorer</h4>

      <input
        type="text"
        className="table-search"
        placeholder="Search tables..."
        value={searchTerm}
        onChange={(e) => setSearchTerm(e.target.value)}
      />

      <div className="table-list">
        {tables
          .filter((table) =>
            table.toLowerCase().includes(searchTerm.toLowerCase())
          )
          .map((table) => (
            <div key={table}>
              <div
                className="table-item"
                onClick={() => loadColumns(table)}
              >
                <span>
                  {expandedTable === table ? "▼" : "▶"}
                </span>

                <span className="table-icon">📄</span>

                <span className="table-name">{table}</span>

                <span className="table-count">
                  {counts[table] || 0}
                </span>
              </div>

              {expandedTable === table && columns[table] && (
                <div className="column-list">
                  {columns[table].map((column) => (
                    <div
                      key={column}
                      className="column-item"
                    >
                      <span className="column-icon">▸</span>
                      <span>{column}</span>
                    </div>
                  ))}

                  <button
                    className="sample-btn"
                    onClick={() => loadSampleData(table)}
                  >
                    View Sample Data
                  </button>
                </div>
              )}
            </div>
          ))}
      </div>
    </div>
  );
}

export default SchemaExplorer;