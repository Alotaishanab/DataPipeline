import React, { useEffect, useState } from 'react';
import './Panels.css';

export default function Datasets() {
  const [internalFiles, setInternalFiles] = useState([]);
  const [userFolders, setUserFolders] = useState([]);
  const [folderFiles, setFolderFiles] = useState([]);
  const [activeFolder, setActiveFolder] = useState(null);
  const [query, setQuery] = useState('');

  // Initial fetch
  useEffect(() => {
    const fetchDatasets = async () => {
      try {
        const res = await fetch('/api/datasets');
        const data = await res.json();

        if (data.datasets) {
          const internal = data.datasets.filter(d => d.type === 'internal');
          const folders = data.datasets.filter(d => d.type === 'user_folder');
          setInternalFiles(internal);
          setUserFolders(folders);
        }
      } catch (err) {
        console.error(err);
        setInternalFiles([]);
        setUserFolders([]);
      }
    };

    fetchDatasets();
  }, []);

  const handleFolderClick = async (jobId) => {
    try {
      const res = await fetch(`/api/datasets/user/${jobId}`);
      const data = await res.json();
      if (data.files) {
        setFolderFiles(data.files);
        setActiveFolder(jobId);
      }
    } catch (err) {
      console.error(err);
      setFolderFiles([]);
      setActiveFolder(null);
    }
  };

  const filter = (items) =>
    items.filter(item =>
      item.name.toLowerCase().includes(query.toLowerCase()) ||
      (item.job_id && item.job_id.toLowerCase().includes(query.toLowerCase()))
    );

  const renderSection = (title, items, type) => (
    <div className="results-card">
      <h2 className="results-title">{title}</h2>
      {items.length > 0 ? (
        <ul className="results-list">
          {items.map((item, i) => {
            if (type === 'internal') {
              return (
                <li key={i}>
                  <a
                    className="results-link"
                    href={`/datasets/internal/${item.name}`}
                    target="_blank"
                    rel="noreferrer"
                  >
                    📄 {item.name} <span style={{ fontSize: '0.85rem', color: '#888' }}>({item.type})</span>
                  </a>
                </li>
              );
            } else {
              return (
                <li key={i}>
                  <button
                    className="results-link"
                    onClick={() => handleFolderClick(item.name)}
                  >
                    📁 {item.name}
                  </button>
                </li>
              );
            }
          })}
        </ul>
      ) : (
        <p className="no-results">🚫 No items found.</p>
      )}
    </div>
  );

  const renderFolderContents = () => (
    <div className="results-card">
      <h2 className="results-title">📂 Files in {activeFolder}</h2>
      <button onClick={() => { setActiveFolder(null); setFolderFiles([]); }}>🔙 Back to Folders</button>
      {folderFiles.length > 0 ? (
        <ul className="results-list">
          {folderFiles.map((file, i) => (
            <li key={i}>
              <a
                className="results-link"
                href={`/datasets/user/${activeFolder}/${file}`}
                target="_blank"
                rel="noreferrer"
              >
                📄 {file}
              </a>
            </li>
          ))}
        </ul>
      ) : (
        <p className="no-results">🚫 No files found in this folder.</p>
      )}
    </div>
  );

  return (
    <div className="results-container">
      <div className="results-header">
        <h1 className="results-main-title">📦 Available Datasets</h1>
        <p className="results-description">
          Browse uploaded datasets and explore available chunks.
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
        {renderSection('⚙️ Internal Datasets', filter(internalFiles), 'internal')}
        {!activeFolder && renderSection('🧑‍💻 User Datasets (Folders)', filter(userFolders), 'folder')}
        {activeFolder && renderFolderContents()}
      </div>
    </div>
  );
}
