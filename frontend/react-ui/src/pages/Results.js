import React, { useEffect, useState } from 'react';
import './Panels.css';

export default function Results() {
  const [internalResults, setInternalResults] = useState([]);
  const [userResults, setUserResults] = useState([]);
  const [query, setQuery] = useState('');

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

  const filterResults = (files) => {
    if (!query.trim()) return files;
    return files.filter(f => f.toLowerCase().includes(query.toLowerCase()));
  };

  const renderSection = (title, files) => {
    const filtered = filterResults(files);
    return (
      <div className="results-card">
        <h2 className="results-title">{title}</h2>
        {filtered.length > 0 ? (
          <ul className="results-list">
            {filtered.map((file, i) => (
              <li key={i}>
                <a href={file} target="_blank" rel="noreferrer" className="results-link">
                  📄 {file.split('/').pop()}
                </a>
              </li>
            ))}
          </ul>
        ) : (
          <p className="no-results">🚫 No matching results.</p>
        )}
      </div>
    );
  };

  return (
    <div className="results-container">
      <div className="results-header">
        <h1 className="results-main-title">📊 Processed Dataset Chunks</h1>
        <p className="results-description">
          Uploaded datasets are automatically <strong>split into smaller chunks</strong> for distributed processing.
          Each file listed below is a processed chunk output (in JSON format).
        </p>

        <input
          type="text"
          placeholder="🔍 Search by filename or job ID..."
          className="results-search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
      </div>

      <div className="results-grid">
        {renderSection('⚙️ Internal Results', internalResults)}
        {renderSection('🧑‍💻 User Results', userResults)}
      </div>
    </div>
  );
}
