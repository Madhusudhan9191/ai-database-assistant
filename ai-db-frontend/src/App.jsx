import { useState, useEffect } from "react";
import "./App.css";
import { API_BASE_URL } from "./config";

import LeftSidebar from "./components/LeftSidebar";
import RightSidebar from "./components/RightSidebar";
import TopNavbar from "./components/TopNavbar";
import ChatArea from "./components/ChatArea";
import Dashboard from "./components/Dashboard";
import SaveReportModal from "./components/SaveReportModal";
import AuthPage from "./components/AuthPage";
import AdminDashboard from "./components/AdminDashboard";

function App() {
  const [user, setUser] = useState(() => {
    const saved = localStorage.getItem("auth-user");
    return saved ? JSON.parse(saved) : null;
  });
  const [token, setToken] = useState(() => {
    return localStorage.getItem("auth-token") || null;
  });

  const [leftOpen, setLeftOpen] = useState(true);
  const [rightOpen, setRightOpen] = useState(true);
  const [activeTab, setActiveTab] = useState("chat");

  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);

  const [queryHistory, setQueryHistory] = useState([]);
  const [favorites, setFavorites] = useState([]);
  const [saveModalOpen, setSaveModalOpen] = useState(false);
  const [pendingReportData, setPendingReportData] = useState(null);

  const [selectedQuery, setSelectedQuery] =
   useState(null);

  const [dbConnectionVersion, setDbConnectionVersion] = useState(0);
  const handleConnectionChange = () => {
    setDbConnectionVersion((v) => v + 1);
  };

  const [conversations, setConversations] = useState(() => [
    {
      id: Date.now(),
      title: "New Chat",
      messages: [],
    },
  ]);
  const [activeConversationId, setActiveConversationId] =
useState(() =>
  conversations.length > 0
    ? conversations[0].id
    : null
);

  useEffect(() => {
    if (conversations.length > 0) {
      const exists = conversations.some(
        (c) => c.id === activeConversationId
      );
      if (!exists) {
        setActiveConversationId(conversations[0].id);
      }
    } else {
      setActiveConversationId(null);
    }
  }, [conversations, activeConversationId]);

  const [settings, setSettings] = useState(() => {
    const saved = localStorage.getItem("app-settings");
    return saved
      ? JSON.parse(saved)
      : {
          darkMode: true,
          showCharts: true,
          showInsights: true,
          autoConnect: true,
        };
  });

  const activeConversation =
  conversations.find(
    (conversation) =>
      conversation.id === activeConversationId
  ) || {
    messages: []
  };

  const handleLoginSuccess = (userData, userToken) => {
    setUser(userData);
    setToken(userToken);
  };

  const handleLogout = () => {
    localStorage.removeItem("auth-token");
    localStorage.removeItem("auth-user");
    setUser(null);
    setToken(null);
    setQueryHistory([]);
    setFavorites([]);
    const nextChatId = Date.now();
    setConversations([
      {
        id: nextChatId,
        title: "New Chat",
        messages: [],
      },
    ]);
    setActiveConversationId(nextChatId);
  };

  const syncMetadata = async () => {
    if (!token) return;
    try {
      const headers = { "Authorization": `Bearer ${token}` };
      const histRes = await fetch(API_BASE_URL + "/history", { headers });
      if (histRes.status === 401) {
        handleLogout();
        return;
      }
      if (histRes.ok) {
        const histData = await histRes.json();
        setQueryHistory(histData);
      }
      const favsRes = await fetch(API_BASE_URL + "/favorites", { headers });
      if (favsRes.status === 401) {
        handleLogout();
        return;
      }
      if (favsRes.ok) {
        const favsData = await favsRes.json();
        setFavorites(favsData);
      }
    } catch (err) {
      console.warn("Failed to sync query history and favorites:", err);
    }
  };

  useEffect(() => {
    if (token) {
      syncMetadata();
    }
  }, [token]);

  const handleDeleteQuery = async (id) => {
    try {
      const res = await fetch(`${API_BASE_URL}/history/${id}`, {
        method: "DELETE",
        headers: { "Authorization": `Bearer ${token}` }
      });
      if (res.status === 401) {
        handleLogout();
        return;
      }
      if (res.ok) {
        setQueryHistory((prev) => prev.filter((q) => q.id !== id));
      }
    } catch (err) {
      console.error("Failed to delete query:", err);
    }
  };

  const handleDeleteBulkQueries = async (ids) => {
    try {
      const res = await fetch(API_BASE_URL + "/history/bulk-delete", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({ ids }),
      });
      if (res.status === 401) {
        handleLogout();
        return;
      }
      if (res.ok) {
        setQueryHistory((prev) => prev.filter((q) => !ids.includes(q.id)));
      }
    } catch (err) {
      console.error("Failed to delete queries:", err);
    }
  };

  const handleClearHistory = async () => {
    try {
      const res = await fetch(API_BASE_URL + "/history", {
        method: "DELETE",
        headers: { "Authorization": `Bearer ${token}` }
      });
      if (res.status === 401) {
        handleLogout();
        return;
      }
      if (res.ok) {
        setQueryHistory([]);
      }
    } catch (err) {
      console.error("Failed to clear history:", err);
    }
  };

  const handleAddFavorite = async (question, generated_sql) => {
    try {
      const res = await fetch(API_BASE_URL + "/favorites", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({ question, generated_sql }),
      });
      if (res.status === 401) {
        handleLogout();
        return;
      }
      if (res.ok) {
        const favsRes = await fetch(API_BASE_URL + "/favorites", {
          headers: { "Authorization": `Bearer ${token}` }
        });
        if (favsRes.ok) {
          const data = await favsRes.json();
          setFavorites(data);
        }
      }
    } catch (err) {
      console.error("Failed to add favorite:", err);
    }
  };

  const handleRemoveFavorite = async (id) => {
    try {
      const res = await fetch(`${API_BASE_URL}/favorites/${id}`, {
        method: "DELETE",
        headers: { "Authorization": `Bearer ${token}` }
      });
      if (res.status === 401) {
        handleLogout();
        return;
      }
      if (res.ok) {
        setFavorites((prev) => prev.filter((f) => f.id !== id));
      }
    } catch (err) {
      console.error("Failed to remove favorite:", err);
    }
  };

  const handleSaveReportClick = (question, generated_sql, chart_type) => {
    setPendingReportData({ question, generated_sql, chart_type });
    setSaveModalOpen(true);
  };

  const handleSaveReportConfirm = async (reportName) => {
    if (!pendingReportData) return;
    try {
      const res = await fetch(API_BASE_URL + "/saved-reports", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({
          report_name: reportName,
          question: pendingReportData.question,
          generated_sql: pendingReportData.generated_sql,
          chart_type: pendingReportData.chart_type,
        }),
      });
      if (res.status === 401) {
        handleLogout();
      }
    } catch (err) {
      console.error("Failed to save report:", err);
    }
  };

  useEffect(() => {
  localStorage.setItem(
    "app-settings",
    JSON.stringify(settings)
  );
}, [settings]);

  useEffect(() => {
  localStorage.setItem(
    "query-history",
    JSON.stringify(queryHistory)
  );
}, [queryHistory]);





  const addAssistantMessage = (message) => {
  setConversations((prev) =>
    prev.map((conversation) => {
      if (
        conversation.id !==
        activeConversationId
      ) {
        return conversation;
      }

      return {
        ...conversation,
        messages: [
          ...conversation.messages,
          message,
        ],
      };
    })
  );
};


  const handleQuery = async (queryText) => {
    const q = queryText || question;
    if (!q.trim()) return;

    try {
      setLoading(true);

      const res = await fetch(
        API_BASE_URL + "/ask",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`
          },
          body: JSON.stringify({
            question: q,
          }),
        }
      );

      if (res.status === 401) {
        handleLogout();
        return;
      }

      const data = await res.json();

      // Handle API errors (show in chat)
      if (!res.ok) {
        const errorMsg = data.detail || "Something went wrong.";

        const userMessage = {
          id: Date.now(),
          role: "user",
          content: q,
        };

        const errorMessage = {
          id: Date.now() + 1,
          role: "assistant",
          error: true,
          errorText: errorMsg,
        };

        setConversations((prev) =>
          prev.map((conversation) => {
            if (
              conversation.id !==
              activeConversationId
            ) {
              return conversation;
            }

            return {
              ...conversation,
              messages: [
                ...conversation.messages,
                userMessage,
                errorMessage,
              ],
            };
          })
        );

        setQuestion("");
        setLoading(false);
        return;
      }

      const userMessage = {
        id: Date.now(),
        role: "user",
        content: q,
        generated_sql: data.generated_sql,
        data: data.data,
        insights: data.insights,
        kpis: data.kpis,
        chart_data: data.chart_data,
        show_chart: data.show_chart,
        execution_time_ms: data.execution_time_ms,
      };

      const queryRecord = {
        id: Date.now(),
        question: q,
        generated_sql: data.generated_sql,
        data: data.data,
        insights: data.insights,
        kpis: data.kpis,
        chart_data: data.chart_data,
        show_chart: data.show_chart,
        execution_time_ms: data.execution_time_ms,
      };

      const aiMessage = {
        id: Date.now() + 1,
        role: "assistant",
        generated_sql: data.generated_sql,
        data: data.data,
        insights: data.insights,
        kpis: data.kpis,
        chart_data: data.chart_data,
        show_chart: data.show_chart,
        execution_time_ms: data.execution_time_ms,
        explanation: data.explanation,
        question: q,
        chart_type: data.chart_type,
      };

      setConversations((prev) =>
        prev.map((conversation) => {
          if (
            conversation.id !==
            activeConversationId
          ) {
            return conversation;
          }

          return {
            ...conversation,

            title:
              conversation.title ===
              "New Chat"
                ? q
                    .split(" ")
                    .slice(0, 4)
                    .join(" ")
                : conversation.title,

            messages: [
              ...conversation.messages,
              userMessage,
              aiMessage,
            ],
          };
        })
      );

      // Sync logs from metadata DB
      syncMetadata();

      setQueryHistory((prev) => [
        queryRecord,
        ...prev,
      ]);

      setSelectedQuery(queryRecord);

      setQuestion("");
    } catch (error) {
      // Network error (server down, etc)
      const userMessage = {
        id: Date.now(),
        role: "user",
        content: q,
      };

      const errorMessage = {
        id: Date.now() + 1,
        role: "assistant",
        error: true,
        errorText:
          "Could not connect to the server. " +
          "Please check that the backend is running.",
      };

      setConversations((prev) =>
        prev.map((conversation) => {
          if (
            conversation.id !==
            activeConversationId
          ) {
            return conversation;
          }
          return {
            ...conversation,
            messages: [
              ...conversation.messages,
              userMessage,
              errorMessage,
            ],
          };
        })
      );

      setQuestion("");
    } finally {
      setLoading(false);
    }
  };

  const runPastQuery = (queryText) => {
    setQuestion(queryText);
    handleQuery(queryText);
  };

  if (!token) {
    return <AuthPage onLoginSuccess={handleLoginSuccess} />;
  }

  return (
  <div
    className={`app-layout ${
      settings.darkMode
        ? "dark-theme"
        : "light-theme"
    }`}
  >
      <LeftSidebar
        open={leftOpen}
        toggle={() =>
          setLeftOpen(!leftOpen)
        }
        addAssistantMessage={
          addAssistantMessage
        }
        settings={settings}
        setSettings={setSettings}
        favorites={favorites}
        onRemoveFavorite={handleRemoveFavorite}
        onSelectQuery={runPastQuery}
        setActiveTab={setActiveTab}
        user={user}
        onLogout={handleLogout}
        token={token}
        onConnectionChange={handleConnectionChange}
      />

      <div className="center-section">
        <TopNavbar activeTab={activeTab} setActiveTab={setActiveTab} user={user} />

        {activeTab === "chat" && (
          <ChatArea
            question={question}
            setQuestion={setQuestion}
            handleQuery={handleQuery}
            loading={loading}
            messages={
              activeConversation?.messages ||
              []
            }
            settings={settings}
            onSaveReport={handleSaveReportClick}
            onAddFavorite={handleAddFavorite}
          />
        )}
        {activeTab === "dashboard" && (
           <Dashboard
            token={token}
            onLogout={handleLogout}
            dbConnectionVersion={dbConnectionVersion}
          />
        )}
        {activeTab === "admin" && (
          <AdminDashboard token={token} onLogout={handleLogout} />
        )}
      </div>

      <RightSidebar
        open={rightOpen}
        toggle={() =>
          setRightOpen(!rightOpen)
        }
        queryHistory={queryHistory}
        runPastQuery={runPastQuery}
        clearHistory={handleClearHistory}
        onDeleteQuery={handleDeleteQuery}
        onDeleteBulkQueries={handleDeleteBulkQueries}
      />

      <SaveReportModal
        isOpen={saveModalOpen}
        onClose={() => setSaveModalOpen(false)}
        onSave={handleSaveReportConfirm}
        defaultName={pendingReportData?.question}
      />
    </div>
  );
}

export default App;