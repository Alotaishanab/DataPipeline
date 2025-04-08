import React, { useEffect, useState } from 'react';
import './Results.css'; // Use the same styling

export default function Datasets() {
  const [files, setFiles] = useState([]);

  useEffect(() => {
    const fetchDatasets = async () => {
      try {
        const res = await fetch('/api/datasets');
        const data = await res.json();
        if (data.files) {
          setFiles(data.files);
        } else {
          setFiles([]);
        }
      } catch (err) {
        console.error(err);
        setFiles([]);
      }
    };

    fetchDatasets();
  }, []);

  return (
    <div className="results-container">
      <div className="results-card">
        <h1 className="results-title">📦 Available Datasets</h1>
        {files.length > 0 ? (
          <ul className="results-list">
            {files.map((file, i) => (
              <li key={i}>
                <a href={`/datasets/${file}`} target="_blank" rel="noreferrer">
                  {file}
                </a>
              </li>
            ))}
          </ul>
        ) : (
          <p className="no-results">🚫 No datasets found yet.</p>
        )}
      </div>
    </div>
  );
}
