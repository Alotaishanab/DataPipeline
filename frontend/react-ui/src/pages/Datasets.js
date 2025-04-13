import React, { useEffect, useState } from 'react';
import './Results.css';

export default function Datasets() {
  const [files, setFiles] = useState([]);

  useEffect(() => {
    const fetchDatasets = async () => {
      try {
        const res = await fetch('/api/datasets');
        const data = await res.json();
        if (data.datasets) {
          setFiles(data.datasets);
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
                <a
                  href={`/datasets/${file.type}/${file.name}`}
                  target="_blank"
                  rel="noreferrer"
                >
                  {file.name} ({file.type})
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
