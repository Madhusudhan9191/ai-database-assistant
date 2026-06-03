function ResultsTable({ data }) {

  if (!data || data.length === 0) {
    return <p>No Data Found</p>;
  }

  return (
    <table
      border="1"
      style={{
        width: "100%",
        borderCollapse: "collapse",
        marginTop: "20px",
      }}
    >
      <thead>
        <tr>
          {Object.keys(data[0]).map((key) => (
            <th
              key={key}
              style={{
                padding: "10px",
              }}
            >
              {key}
            </th>
          ))}
        </tr>
      </thead>

      <tbody>
        {data.map((row, index) => (
          <tr key={index}>
            {Object.values(row).map((value, i) => (
              <td
                key={i}
                style={{
                  padding: "10px",
                  textAlign: "center",
                }}
              >
                {value}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export default ResultsTable;