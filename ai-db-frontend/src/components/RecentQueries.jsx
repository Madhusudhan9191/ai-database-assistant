function RecentQueries({
  recentQueries,
  runRecentQuery
}) {
  return (
    <div
      style={{
        marginTop: "50px",
      }}
    >
      <h2
        style={{
          textAlign: "center",
        }}
      >
        Recent Queries
      </h2>

      <div
        style={{
          display: "flex",
          flexDirection: "column",
          gap: "10px",
          maxWidth: "700px",
          margin: "0 auto",
        }}
      >
        {recentQueries.map(
          (item, index) => (
            <div
              key={index}
              onClick={() =>
                runRecentQuery(
                  item.question
                )
              }
              style={{
                padding: "12px",
                border: "1px solid #444",
                borderRadius: "8px",
                cursor: "pointer",
                textAlign: "left",
              }}
            >
              {item.question}
            </div>
          )
        )}
      </div>
    </div>
  );
}

export default RecentQueries;