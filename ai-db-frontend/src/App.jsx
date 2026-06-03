import { useState, useEffect } from "react";
import axios from "./api";

import SearchBar from "./components/SearchBar";
import StatsCard from "./components/StatsCard";
import QueryResult from "./components/QueryResult";
import RecentQueries from "./components/RecentQueries";

function App() {

  const [question, setQuestion] = useState("");
  const [response, setResponse] = useState(null);
  const [loading, setLoading] = useState(false);
  const [recentQueries, setRecentQueries] = useState([]);
  const [queryCount, setQueryCount] = useState(0);
  const [error, setError] = useState("");

  useEffect(() => {
    loadHistory();
    loadQueryCount();
  }, []);

  const loadHistory = async () => {
    try {

      const res = await axios.get(
        "/history/latest"
      );

      setRecentQueries(res.data);

    } catch (error) {

      console.error(error);

    }
  };

  const loadQueryCount = async () => {
    try {

      const res = await axios.get(
        "/history/count"
      );

      setQueryCount(
        res.data.total_queries
      );

    } catch (error) {

      console.error(error);

    }
  };

  const askAI = async () => {

    if (!question.trim()) {

      setError(
        "Please enter a question."
      );

      return;
    }

    try {

      setError("");

      setLoading(true);

      const res = await axios.post(
        "/ask",
        {
          question,
        }
      );

      setResponse(res.data);

      loadHistory();
      loadQueryCount();

    } catch (error) {

      console.error(error);

      if (error.response) {

        setError(
          error.response.data.detail ||
          "Something went wrong."
        );

      } else {

        setError(
          "Unable to connect to server."
        );

      }

    } finally {

      setLoading(false);

    }
  };

  const runRecentQuery = async (query) => {

    setQuestion(query);

    try {

      setError("");

      setLoading(true);

      const res = await axios.post(
        "/ask",
        {
          question: query,
        }
      );

      setResponse(res.data);

      loadHistory();
      loadQueryCount();

    } catch (error) {

      console.error(error);

      if (error.response) {

        setError(
          error.response.data.detail ||
          "Something went wrong."
        );

      } else {

        setError(
          "Unable to connect to server."
        );

      }

    } finally {

      setLoading(false);

    }
  };

  return (
    <div
      style={{
        padding: "30px",
        maxWidth: "1200px",
        margin: "0 auto",
      }}
    >
      <h1
        style={{
          textAlign: "center",
        }}
      >
        AI Database Assistant
      </h1>

      <StatsCard
        queryCount={queryCount}
      />

      <SearchBar
        question={question}
        setQuestion={setQuestion}
        askAI={askAI}
      />

      {error && (
        <div
          style={{
            color: "red",
            textAlign: "center",
            marginBottom: "20px",
            fontWeight: "bold",
          }}
        >
          {error}
        </div>
      )}

      {loading && (
        <h3
          style={{
            textAlign: "center",
          }}
        >
          Thinking...
        </h3>
      )}

      <QueryResult
        response={response}
      />

      <RecentQueries
        recentQueries={recentQueries}
        runRecentQuery={runRecentQuery}
      />
    </div>
  );
}

export default App;