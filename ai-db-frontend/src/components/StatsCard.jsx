function StatsCard({ queryCount }) {
  return (
    <h3
      style={{
        textAlign: "center",
        marginBottom: "30px",
      }}
    >
      Total Queries Executed: {queryCount}
    </h3>
  );
}

export default StatsCard;