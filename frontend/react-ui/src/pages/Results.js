import React, { useEffect, useState } from 'react';
import './Results.css';

export default function Results() {
  const [internalResults, setInternalResults] = useState([]);
  const [userResults, setUserResults] = useState([]);

  const fetchResults = async (path, setter) => {
    try {
      const res = await fetch(path);
      const text = await res.text();
      const matches = [...text.matchAll(/href="(.*?\.json)"/g)].map(m => m[1]);
      setter(matches);
    } catch (err) {
      console.error(`❌ Failed to fetch ${path}:`, err);
    }
  };

  useEffect(() => {
    fetchResults('/results/internal/', setInternalResults);
    fetchResults('/results/user/', setUserResults);
  }, []);

  const renderSection = (title, files, basePath) => (
    <div className="results-card">
      <h2 className="results-title">{title}</h2>
      {files.length > 0 ? (
        <ul className="results-list">
          {files.map((file, i) => (
            <li key={i}>
              <a href={`${basePath}${file}`} target="_blank" rel="noreferrer">{file}</a>
            </li>
          ))}
        </ul>
      ) : (
        <p className="no-results">🚫 No results yet.</p>
      )}
    </div>
  );

  return (
    <div className="results-container">
      {renderSection('🧪 Internal Results', internalResults, '/results/internal/')}
      {renderSection('🧪 User Results', userResults, '/results/user/')}
    </div>
  );
}
