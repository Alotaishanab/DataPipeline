import React, { useEffect, useState } from 'react';
import './Panels.css';

export default function Datasets() {
  const [files, setFiles] = useState([]);
  const [query, setQuery] = useState('');

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

  const filteredFiles = files.filter(file =>
    file.name.toLowerCase().includes(query.toLowerCase())
  );

  return (
    <div className="results-container">
      <div className="results-header">
        <h1 className="results-main-title">📦 Available Datasets</h1>
        <p className="results-description">
          These are the uploaded and internal dataset chunks, ready for processing or already split.
        </p>

        <input
          type="text"
          placeholder="🔍 Search dataset by name..."
          className="results-search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
      </div>

      <div className="results-card">
        {filteredFiles.length > 0 ? (
          <ul className="results-list">
            {filteredFiles.map((file, i) => (
              <li key={i}>
                <a
                  className="results-link"
                  href={`/datasets/${file.type}/${file.name}`}
                  target="_blank"
                  rel="noreferrer"
                >
                  📄 {file.name} <span style={{ fontSize: '0.85rem', color: '#888' }}>({file.type})</span>
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
