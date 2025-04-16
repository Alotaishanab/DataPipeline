import React, { useEffect, useState } from 'react';
import './Panels.css';

export default function Datasets() {
  const [internalFiles, setInternalFiles] = useState([]);
  const [userFolders, setUserFolders] = useState([]);
  const [folderFiles, setFolderFiles] = useState([]);
  const [activeFolder, setActiveFolder] = useState(null);
  const [query, setQuery] = useState('');

  // ──────────────────────────────────────────
  // Fetch helper (re‑used by interval)
  // ──────────────────────────────────────────
  const fetchDatasets = async () => {
    try {
      const res  = await fetch('/api/datasets');
      const data = await res.json();

      if (data.datasets) {
        setInternalFiles(data.datasets.filter(d => d.type === 'internal'));
        setUserFolders(data.datasets.filter(d => d.type === 'user_folder'));
      }
    } catch (err) {
      console.error('❌ Failed to fetch datasets:', err);
      setInternalFiles([]);
      setUserFolders([]);
    }
  };

  // initial fetch + 30 s auto‑refresh
  useEffect(() => {
    fetchDatasets();                        // first load
    const id = setInterval(fetchDatasets, 30_000);
    return () => clearInterval(id);         // cleanup on unmount
  }, []);

  // fetch files inside a user folder
  const handleFolderClick = async (jobId) => {
    try {
      const res  = await fetch(`/api/datasets/user/${jobId}`);
      const data = await res.json();
      setFolderFiles(data.files || []);
      setActiveFolder(jobId);
    } catch (err) {
      console.error(`❌ Failed to fetch folder ${jobId}:`, err);
    }
  };

  // search helper
  const filter = (items) =>
    items.filter(item =>
      (item.name || '').toLowerCase().includes(query.toLowerCase())
    );

  /* ---------- render helpers ------------------------------------------------ */
  const renderSection = (title, items, type) => (
    <div className="results-card">
      <h2 className="results-title">{title}</h2>
      {items.length ? (
        <ul className="results-list">
          {items.map((item, i) => (
            type === 'internal' ? (
              <li key={i}>
                <a
                  className="results-link"
                  href={`/datasets/internal/${item.name}`}
                  target="_blank" rel="noreferrer"
                >
                  📄 {item.name}
                </a>
              </li>
            ) : (
              <li key={i}>
                <button
                  className="results-link"
                  onClick={() => handleFolderClick(item.name)}
                >
                  📁 {item.name}
                </button>
              </li>
            )
          ))}
        </ul>
      ) : <p className="no-results">🚫 No items found.</p>}
    </div>
  );

  const renderFolderContents = () => (
    <div className="results-card">
      <h2 className="results-title">📂 Files in {activeFolder}</h2>
      <button onClick={() => { setActiveFolder(null); setFolderFiles([]); }}>
        🔙 Back to Folders
      </button>
      {folderFiles.length ? (
        <ul className="results-list">
          {folderFiles.map((file, i) => (
            <li key={i}>
              <a
                className="results-link"
                href={`/datasets/user/${activeFolder}/${file}`}
                target="_blank" rel="noreferrer"
              >
                📄 {file}
              </a>
            </li>
          ))}
        </ul>
      ) : <p className="no-results">🚫 No files found in this folder.</p>}
    </div>
  );

  /* ---------- main render --------------------------------------------------- */
  return (
    <div className="results-container">
      <div className="results-header">
        <h1 className="results-main-title">📦 Available Datasets</h1>
        <p className="results-description">Browse uploaded datasets and explore available chunks.</p>
        <input
          type="text"
          className="results-search"
          placeholder="🔍 Search dataset..."
          value={query}
          onChange={e => setQuery(e.target.value)}
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
