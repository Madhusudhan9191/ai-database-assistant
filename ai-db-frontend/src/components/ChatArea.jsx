import "./ChatArea.css";
import AnalyticsChart from "./AnalyticsChart";
import * as XLSX from "xlsx";
import { useEffect, useRef, useState } from "react";

const escapeCSV = (value) => {
  const str = String(value ?? "");
  if (
    str.includes(",") ||
    str.includes('"') ||
    str.includes("\n")
  ) {
    return `"${str.replace(/"/g, '""')}"`;
  }
  return str;
};

function CopyButton({ text }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <button
      className="copy-btn"
      onClick={handleCopy}
      title="Copy to clipboard"
    >
      {copied ? "✓ Copied" : "📋 Copy"}
    </button>
  );
}

const exportCSV = (data) => {
  if (!data?.length) return;

  const headers = Object.keys(data[0]);

  const rows = data.map((row) =>
    headers.map((h) => escapeCSV(row[h]))
  );

  const csv = [
    headers.map(escapeCSV).join(","),
    ...rows.map((r) => r.join(",")),
  ].join("\n");

  const blob = new Blob([csv], {
    type: "text/csv",
  });

  const url =
    window.URL.createObjectURL(blob);

  const link =
    document.createElement("a");

  link.href = url;
  link.download = "query_results.csv";
  link.click();

  window.URL.revokeObjectURL(url);
};

const exportExcel = (data) => {
  if (!data?.length) return;

  const worksheet =
    XLSX.utils.json_to_sheet(data);

  const workbook =
    XLSX.utils.book_new();

  XLSX.utils.book_append_sheet(
    workbook,
    worksheet,
    "Results"
  );

  XLSX.writeFile(
    workbook,
    "query_results.xlsx"
  );
};

function ChatArea({
  question,
  setQuestion,
  handleQuery,
  loading,
  messages,
  settings,
  onSaveReport,
  onAddFavorite,
}) {
  const [dryRun, setDryRun] = useState(false);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({
      behavior: "smooth",
    });
  }, [messages]);

  return (
    <div className="chat-area">
      <div className="messages-area">
        {messages.length === 0 && (
          <div className="empty-chat">
            <h1>AI Database Assistant</h1>
            <p>Ask anything about your database</p>
          </div>
        )}

        {messages.map((msg) => (
          <div
            key={msg.id}
            id={`message-${msg.id}`}
          >
            {msg.role === "user" && (
              <div className="user-message">
                {msg.content}
              </div>
            )}



            {msg.role === "assistant" &&
              msg.error && (
                <div className="assistant-message error-message">
                  <h3>❌ Error</h3>
                  <pre className="error-content">
                    {msg.errorText}
                  </pre>
                </div>
              )}

            {msg.role === "assistant" &&
              !msg.error && (
              <div className="assistant-message">
                {msg.query_analysis && (
                  <QueryAnalysis analysis={msg.query_analysis} />
                )}

                {msg.explanation && (
                  <div className="query-explanation">
                    💡 {msg.explanation}
                  </div>
                )}

                <div className="sql-card">
                  <div className="sql-header">
                    <h3>Generated SQL</h3>
                    <div className="sql-actions">
                      {msg.execution_time_ms && (
                        <span className="exec-time">
                          ⚡ {msg.execution_time_ms}ms
                        </span>
                      )}
                      <CopyButton
                        text={msg.generated_sql}
                      />
                      <button
                        className="save-report-btn"
                        onClick={() =>
                          onSaveReport(
                            msg.question || "Custom Report",
                            msg.generated_sql,
                            msg.chart_type || "bar"
                          )
                        }
                        title="Save report to dashboard"
                      >
                        ⭐ Save Report
                      </button>
                      <button
                        className="fav-query-btn"
                        onClick={() =>
                          onAddFavorite(
                            msg.question || "Custom Query",
                            msg.generated_sql
                          )
                        }
                        title="Add to favorites list"
                      >
                        ❤️ Favorite
                      </button>
                    </div>
                  </div>
                  <pre>{msg.generated_sql}</pre>
                </div>

                {msg.kpis &&
                  msg.kpis.length > 0 && (
                    <div className="kpi-grid">
                      {msg.kpis.map(
                        (kpi, index) => (
                          <div
                            key={index}
                            className={`kpi-card kpi-${kpi.type}`}
                          >
                            <div className="kpi-value">
                              {kpi.value}
                            </div>
                            <div className="kpi-label">
                              {kpi.label}
                            </div>
                          </div>
                        )
                      )}
                    </div>
                  )}

                <div className="results-card">
                  <div className="results-header">
                    <h3>Results</h3>

                    <div className="export-buttons">
                      <button
                        className="export-btn"
                        onClick={() =>
                          exportCSV(msg.data)
                        }
                      >
                        CSV
                      </button>

                      <button
                        className="export-btn"
                        onClick={() =>
                          exportExcel(msg.data)
                        }
                      >
                        Excel
                      </button>
                    </div>
                  </div>

                  {msg.data &&
                  msg.data.length > 0 ? (
                    <>
                      <table className="results-table">
                        <thead>
                          <tr>
                            {Object.keys(
                              msg.data[0]
                            ).map((key) => (
                              <th key={key}>
                                {key}
                              </th>
                            ))}
                          </tr>
                        </thead>

                        <tbody>
                          {msg.data
                            .slice(0, 10)
                            .map(
                              (
                                row,
                                index
                              ) => (
                                <tr
                                  key={index}
                                >
                                  {Object.values(
                                    row
                                  ).map(
                                    (
                                      value,
                                      i
                                    ) => (
                                      <td
                                        key={i}
                                      >
                                        {String(
                                          value
                                        )}
                                      </td>
                                    )
                                  )}
                                </tr>
                              )
                            )}
                        </tbody>
                      </table>

                      <p className="row-count">
                        Showing first{" "}
                        {Math.min(
                          msg.data.length,
                          10
                        )}{" "}
                        of {msg.data.length} rows
                      </p>
                    </>
                  ) : (
                    <p>
                      No records found.
                    </p>
                  )}
                </div>

                {settings.showInsights &&
                  msg.insights && (
                    <div className="insights-card">
                      <h3>🧠 AI Analysis</h3>

                      {typeof msg.insights ===
                      "object" ? (
                        <div className="insights-sections">
                          {msg.insights
                            .executive_summary && (
                            <div className="insight-section summary-section">
                              <h4>
                                📋 Executive Summary
                              </h4>
                              <p>
                                {
                                  msg.insights
                                    .executive_summary
                                }
                              </p>
                            </div>
                          )}

                          {msg.insights
                            .key_findings && (
                            <div className="insight-section findings-section">
                              <h4>
                                🔍 Key Findings
                              </h4>
                              <pre className="insight-content">
                                {
                                  msg.insights
                                    .key_findings
                                }
                              </pre>
                            </div>
                          )}

                          {msg.insights.risks && (
                            <div className="insight-section risks-section">
                              <h4>
                                ⚠️ Risks
                              </h4>
                              <pre className="insight-content">
                                {msg.insights.risks}
                              </pre>
                            </div>
                          )}

                          {msg.insights
                            .recommendations && (
                            <div className="insight-section recommendations-section">
                              <h4>
                                💡 Recommendations
                              </h4>
                              <pre className="insight-content">
                                {
                                  msg.insights
                                    .recommendations
                                }
                              </pre>
                            </div>
                          )}
                        </div>
                      ) : (
                        <p>{msg.insights}</p>
                      )}
                    </div>
                  )}

                {settings.showCharts &&
                  msg.show_chart && (
                    <div className="chart-card">
                      <AnalyticsChart
                        chartData={
                          msg.chart_data
                        }
                      />
                    </div>
                  )}
              </div>
            )}
          </div>
        ))}

        <div ref={messagesEndRef} />
      </div>

      <div className="query-card">
        <input
          type="text"
          value={question}
          onChange={(e) =>
            setQuestion(
              e.target.value
            )
          }
          placeholder={dryRun ? "🛡️ Dry-Run Mode: Test & validate SQL safety..." : "Ask your database anything..."}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              handleQuery();
            }
          }}
        />

        <button
          type="button"
          className={`dry-run-toggle ${dryRun ? "active" : ""}`}
          onClick={() => setDryRun(!dryRun)}
          title={dryRun ? "Dry-Run Active (Validation Only)" : "Switch to Dry-Run Mode"}
          style={{
            background: dryRun ? "rgba(234, 179, 8, 0.2)" : "transparent",
            color: dryRun ? "#eab308" : "#888",
            border: "1px solid " + (dryRun ? "#eab308" : "#444"),
            borderRadius: "8px",
            padding: "6px 12px",
            fontSize: "12px",
            marginRight: "8px",
            cursor: "pointer"
          }}
        >
          {dryRun ? "🛡️ Dry-Run" : "⚡ Live"}
        </button>

        <button
          onClick={() => handleQuery()}
        >
          {loading
            ? "Running..."
            : dryRun
            ? "Validate SQL"
            : "Ask AI"}
        </button>
      </div>
    </div>
  );
}

export default ChatArea;