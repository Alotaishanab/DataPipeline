import React, { useEffect, useState } from 'react';
import './Panels.css';

export default function Datasets() {
  const [internalFiles, setInternalFiles] = useState([]);
  const [userFiles, setUserFiles] = useState([]);
  const [query, setQuery] = useState('');

  useEffect(() => {
    const fetchDatasets = async () => {
      try {
        const res = await fetch('/api/datasets');
        const data = await res.json();
        if (data.datasets) {
          const internal = data.datasets.filter(d => d.type === 'internal');
          const user = data.datasets.filter(d => d.type === 'user');
          setInternalFiles(internal);
          setUserFiles(user);
        }
      } catch (err) {
        console.error(err);
        setInternalFiles([]);
        setUserFiles([]);
      }
    };

    fetchDatasets();
  }, []);

  const filter = (files) =>
    files.filter(f =>
      f.name.toLowerCase().includes(query.toLowerCase()) ||
      (f.job_id && f.job_id.toLowerCase().includes(query.toLowerCase()))
    );

  const renderSection = (title, files) => (
    <div className="results-card">
      <h2 className="results-title">{title}</h2>
      {files.length > 0 ? (
        <ul className="results-list">
          {files.map((file, i) => {
            const link =
              file.type === 'user'
                ? `/datasets/user/${file.job_id}/${file.name}`
                : `/datasets/internal/${file.name}`;
            return (
              <li key={i}>
                <a
                  className="results-link"
                  href={link}
                  target="_blank"
                  rel="noreferrer"
                >
                  📄 {file.name}{' '}
                  <span style={{ fontSize: '0.85rem', color: '#888' }}>
                    ({file.type}{file.job_id ? ` - ${file.job_id}` : ''})
                  </span>
                </a>
              </li>
            );
          })}
        </ul>
      ) : (
        <p className="no-results">🚫 No datasets found yet.</p>
      )}
    </div>
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
          placeholder="🔍 Search dataset by name or job ID..."
          className="results-search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
      </div>

      <div className="results-grid">
        {renderSection('⚙️ Internal Datasets', filter(internalFiles))}
        {renderSection('🧑‍💻 User Datasets', filter(userFiles))}
      </div>
    </div>
  );
}
