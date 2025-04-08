import React, { useEffect, useState } from 'react';

// 🛠 FIXED: removed unused escape characters & unused imports
export default function Results() {
  const [files, setFiles] = useState([]);

  useEffect(() => {
    const fetchResults = async () => {
      try {
        const res = await fetch('/results/');
        const text = await res.text();

        const matches = [...text.matchAll(/href="(.*?\.json)"/g)].map(m => m[1]);
        setFiles(matches);
      } catch (err) {
        console.error(err);
      }
    };

    fetchResults();
  }, []);

  return (
    <div className="results-container">
      <div className="results-card">
        <h1 className="results-title">🧪 Processed Results</h1>
        {files.length > 0 ? (
          <ul className="results-list">
            {files.map((file, i) => (
              <li key={i}>
                <a href={`/results/${file}`} target="_blank" rel="noreferrer">
                  {file}
                </a>
              </li>
            ))}
          </ul>
        ) : (
          <p className="no-results">🚫 No results found yet.</p>
        )}
      </div>
    </div>
  );
}
