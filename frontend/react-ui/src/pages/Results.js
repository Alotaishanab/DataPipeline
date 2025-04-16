import React, { useEffect, useState } from 'react';
import './Panels.css';

export default function Results() {
  const [internalResults, setInternalResults] = useState([]);
  const [userFolders,   setUserFolders]   = useState([]);
  const [folderFiles,   setFolderFiles]   = useState([]);
  const [activeFolder,  setActiveFolder]  = useState(null);
  const [query,         setQuery]         = useState('');

  // helper fetch
  const fetchResults = async () => {
    try {
      const res  = await fetch('/api/results');
      const data = await res.json();
      setInternalResults(data.internal || []);
      setUserFolders(data.user_folders || []);
    } catch (err) {
      console.error('❌ Failed to fetch results:', err);
    }
  };

  // initial + 30 s refresh
  useEffect(() => {
    fetchResults();
    const id = setInterval(fetchResults, 30_000);
    return () => clearInterval(id);
  }, []);

  // fetch files inside a user result folder
  const handleFolderClick = async (jobId) => {
    try {
      const res  = await fetch(`/api/results/user/${jobId}`);
      const data = await res.json();
      setFolderFiles(data.files || []);
      setActiveFolder(jobId);
    } catch (err) {
      console.error(`❌ Failed to fetch folder ${jobId}:`, err);
    }
  };

  const filter = (arr) => arr.filter(x =>
    x.toLowerCase().includes(query.toLowerCase())
  );

  /* ---------- render helpers ------------------------------------------------ */
  const renderSection = (title, items, isFolder=false) => (
    <div className="results-card">
      <h2 className="results-title">{title}</h2>
      {items.length ? (
        <ul className="results-list">
          {items.map((item, i) => (
            <li key={i}>
              {isFolder ? (
                <button className="results-link" onClick={() => handleFolderClick(item)}>
                  📁 {item}
                </button>
              ) : (
                <a
                  className="results-link"
                  href={`/results/internal/${item}`}
                  target="_blank" rel="noreferrer"
                >
                  📄 {item}
                </a>
              )}
            </li>
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
                href={`/results/user/${activeFolder}/${file}`}
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
        <h1 className="results-main-title">📊 Processed Dataset Chunks</h1>
        <p className="results-description">
          View results from internal and user‑submitted jobs. Browse by folder or search filenames.
        </p>
        <input
          type="text"
          className="results-search"
          placeholder="🔍 Search..."
          value={query}
          onChange={e => setQuery(e.target.value)}
        />
      </div>

      <div className="results-grid">
        {renderSection('⚙️ Internal Results', filter(internalResults))}
        {!activeFolder && renderSection('🧑‍💼 User Results (Folders)', filter(userFolders), true)}
        {activeFolder && renderFolderContents()}
      </div>
    </div>
  );
}
