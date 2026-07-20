import { useState, useEffect } from "react";
import axios from "axios";
import SchemaExplorer from "./SchemaExplorer";
import { API_BASE_URL } from "../config";

function ConnectionManager({ addAssistantMessage, setActiveTab, token, onConnectionChange }) {
  const [dbType, setDbType] = useState("postgres");

  const [host, setHost] = useState("localhost");
  const [database, setDatabase] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  const getPort = () => {
    switch (dbType) {
      case "postgres":
        return "5432";
      case "mysql":
        return "3306";
      case "oracle":
        return "1521";
      default:
        return "";
    }
  };

  const [tables, setTables] = useState([]);
  const [connected, setConnected] = useState(false);

  const loadSchema = async () => {
    try {
      const schemaResponse =
        await axios.get(
          API_BASE_URL + "/schema",
          {
            headers: { "Authorization": `Bearer ${token}` }
          }
        );

      setTables(
        schemaResponse.data.tables
      );

      setConnected(true);

    } catch (error) {
      console.error(
        "Failed to load schema",
        error
      );
    }
  };

  useEffect(() => {

    const restoreConnection = async () => {

      const savedConnection =
        localStorage.getItem(
          "activeConnection"
        );

      if (!savedConnection) return;

      const conn =
        JSON.parse(savedConnection);

      setDbType(conn.dbType || "postgres");
      setHost(conn.host || "localhost");
      setDatabase(conn.database || "");
      setUsername(conn.username || "");
      setPassword(conn.password || "");

      // Read autoConnect directly from localStorage
      // to avoid depending on the settings prop
      const savedSettings =
        localStorage.getItem("app-settings");
      const parsedSettings = savedSettings
        ? JSON.parse(savedSettings)
        : {};

      if (parsedSettings?.autoConnect) {
        try {
          // Re-establish backend connection first
          await axios.post(
            API_BASE_URL + "/test-connection",
            {
              db_type: conn.dbType || "postgres",
              host: conn.host || "localhost",
              port: conn.port || "5432",
              database: conn.database || "",
              username: conn.username || "",
              password: "", // Pass empty string to trigger backend auto-reconnect
            },
            {
              headers: { "Authorization": `Bearer ${token}` }
            }
          );
          await loadSchema();
          setConnected(true);
          setMessage("✅ Auto Connected");
          if (onConnectionChange) onConnectionChange();
        } catch (error) {
          console.error("Auto-connect failed:", error);
          setMessage(
            "❌ Auto-connect failed. Please reconnect."
          );
        }
      }
    };

    restoreConnection();

    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  const testConnection = async () => {
    try {
      setLoading(true);
      setMessage("");
      setConnected(false);

      const response = await axios.post(
        API_BASE_URL + "/test-connection",
        {
          db_type: dbType,
          host,
          port: getPort(),
          database,
          username,
          password,
        },
        {
          headers: { "Authorization": `Bearer ${token}` }
        }
      );

      setMessage(`✅ ${response.data.message}`);
    } catch (error) {
      setMessage(
        `❌ ${error.response?.data?.detail ||
        "Connection failed"
        }`
      );
    } finally {
      setLoading(false);
    }
  };

  const connectDatabase = async () => {
    try {
      setLoading(true);

      await axios.post(
        API_BASE_URL + "/test-connection",
        {
          db_type: dbType,
          host,
          port: getPort(),
          database,
          username,
          password,
        },
        {
          headers: { "Authorization": `Bearer ${token}` }
        }
      );

      localStorage.setItem(
        "activeConnection",
        JSON.stringify({
          dbType,
          host,
          port: getPort(),
          database,
          username,
          // Exclude password to protect database credentials
        })
      );

      setConnected(true);

      setMessage("✅ Connected Successfully");


      await loadSchema();
      if (onConnectionChange) onConnectionChange();

    } catch (error) {

      setConnected(false);

      setMessage(
        error.response?.data?.detail ||
        "Connection failed"
      );

    } finally {
      setLoading(false);
    }
  };




  return (
    <div className="connection-manager">
      <h3>Database Connection</h3>

      {/* Database Type */}
      <div className="db-type-section">
        <label>Database Type</label>

        <select
          value={dbType}
          onChange={(e) => setDbType(e.target.value)}
        >
          <option value="postgres">
            PostgreSQL
          </option>

          <option value="oracle">
            Oracle
          </option>

          <option value="mysql">
            MySQL
          </option>
        </select>
      </div>

      {/* Connection Details */}
      <div className="connection-section">
        <h4>Connection Details</h4>

        <div className="form-row">
          <label>Host</label>

          <input
            type="text"
            value={host}
            onChange={(e) =>
              setHost(e.target.value)
            }
            placeholder="localhost"
          />
        </div>

        <div className="form-row">
          <label>
            {dbType === "oracle"
              ? "Service"
              : "Database"}
          </label>

          <input
            type="text"
            value={database}
            onChange={(e) =>
              setDatabase(e.target.value)
            }
            placeholder={
              dbType === "oracle"
                ? "ORCL"
                : "database_name"
            }
          />
        </div>

        <div className="form-row">
          <label>Port</label>

          <input
            type="text"
            value={getPort()}
            readOnly
          />
        </div>

        <div className="form-row">
          <label>Username</label>

          <input
            type="text"
            value={username}
            onChange={(e) =>
              setUsername(e.target.value)
            }
            placeholder="username"
          />
        </div>

        <div className="form-row">
          <label>Password</label>

          <input
            type="password"
            value={password}
            onChange={(e) =>
              setPassword(e.target.value)
            }
            placeholder="password"
          />
        </div>

        <div className="connection-actions">
          <button
            className="test-btn"
            onClick={testConnection}
            disabled={loading}
          >
            {loading ? "Testing..." : "Test"}
          </button>

          <button
            className="connect-btn"
            onClick={connectDatabase}
          >
            Connect
          </button>
        </div>

        {connected && (
          <div className="connection-status">
            🟢 Connected
          </div>
        )}

        {message && (
          <div className="connection-message">
            {message}
          </div>
        )}

        <SchemaExplorer
          tables={tables}
          addAssistantMessage={addAssistantMessage}
          setActiveTab={setActiveTab}
          token={token}
        />

      </div>
    </div>
  );
}

export default ConnectionManager;