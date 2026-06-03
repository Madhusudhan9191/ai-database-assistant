import ResultsTable from "./ResultsTable";

function QueryResult({ response }) {

  if (!response) return null;

  return (
    <div>

      <h2>Generated SQL</h2>

      <pre
        style={{
          padding: "15px",
          borderRadius: "8px",
          overflowX: "auto",
        }}
      >
        {response.generated_sql}
      </pre>

      <h2>
        Execution Time:
        {" "}
        {response.execution_time_ms}
        ms
      </h2>

      <h2>Results</h2>

      <ResultsTable
        data={response.data}
      />

    </div>
  );
}

export default QueryResult;