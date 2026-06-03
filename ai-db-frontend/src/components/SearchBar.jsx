function SearchBar({
  question,
  setQuestion,
  askAI
}) {
  return (
    <div
      style={{
        display: "flex",
        justifyContent: "center",
        gap: "10px",
        marginBottom: "20px",
      }}
    >
      <input
        type="text"
        value={question}
        onChange={(e) =>
          setQuestion(e.target.value)
        }
        onKeyDown={(e) => {
          if (e.key === "Enter") {
            askAI();
          }
        }}
        placeholder="Ask a database question..."
        style={{
          width: "600px",
          padding: "12px",
          fontSize: "16px",
        }}
      />

      <button
        onClick={askAI}
        style={{
          padding: "12px 20px",
          cursor: "pointer",
        }}
      >
        Ask
      </button>
    </div>
  );
}

export default SearchBar;