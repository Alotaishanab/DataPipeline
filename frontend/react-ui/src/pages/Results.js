import React, { useEffect, useState } from 'react';
import './Results.css';

export default function Results() {
  const [internalResults, setInternalResults] = useState([]);
  const [userResults, setUserResults] = useState([]);

  const fetchResults = async (path, setter, basePath) => {
    try {
      const res = await fetch(path);
      const text = await res.text();
      const matches = [...text.matchAll(/href="(.*?\.json)"/g)].map(m => {
        const relative = m[1];
        return `${basePath}${relative.split('/').pop()}`; 
      });
      setter(matches);
    } catch (err) {
      console.error(`❌ Failed to fetch ${path}:`, err);
    }
  };

  useEffect(() => {
    fetchResults('/results/internal/', setInternalResults, '/results/internal/');
    fetchResults('/results/user/', setUserResults, '/results/user/');
  }, []);

  const renderSection = (title, files) => (
    <div className="results-card">
      <h2 className="results-title">{title}</h2>
      {files.length > 0 ? (
        <ul className="results-list">
          {files.map((file, i) => (
            <li key={i}>
              <a href={file} target="_blank" rel="noreferrer">
                {file.split('/').pop()}
              </a>
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
      {renderSection('🧪 Internal Results', internalResults)}
      {renderSection('🧪 User Results', userResults)}
    </div>
  );
}
