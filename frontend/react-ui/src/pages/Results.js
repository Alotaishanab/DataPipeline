import React, { useEffect, useState } from 'react';
import './Panels.css';

export default function Results() {
  const [internalResults, setInternalResults] = useState([]);
  const [userFolders, setUserFolders] = useState([]);
  const [folderFiles, setFolderFiles] = useState([]);
  const [activeFolder, setActiveFolder] = useState(null);
  const [query, setQuery] = useState('');

  useEffect(() => {
    const fetchResults = async () => {
      try {
        const res = await fetch('/api/results');
        const data = await res.json();
        setInternalResults(data.internal || []);
        setUserFolders(data.user_folders || []);
      } catch (err) {
        console.error('❌ Failed to fetch results:', err);
      }
    };
    fetchResults();
  }, []);

  const handleFolderClick = async (jobId) => {
    try {
      const res = await fetch(`/api/results/user/${jobId}`);
      const data = await res.json();
      setFolderFiles(data.files || []);
      setActiveFolder(jobId);
    } catch (err) {
      console.error(`❌ Failed to fetch folder ${jobId}:`, err);
    }
  };

  const filter = (items) =>
    items.filter(item => item.toLowerCase().includes(query.toLowerCase()));

  const renderSection = (title, items, isFolder = false) => (
    <div className="results-card">
      <h2 className="results-title">{title}</h2>
      {items.length > 0 ? (
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
                  target="_blank"
                  rel="noreferrer"
                >
                  📄 {item}
                </a>
              )}
            </li>
          ))}
        </ul>
      ) : (
        <p className="no-results">🚫 No items found.</p>
      )}
    </div>
  );

  const renderFolderContents = () => (
    <div className="results-card">
      <h2 className="results-title">📂 Files in {activeFolder}</h2>
      <button onClick={() => { setActiveFolder(null); setFolderFiles([]); }}> 🔙 Back to Folders</button>
      {folderFiles.length > 0 ? (
        <ul className="results-list">
          {folderFiles.map((file, i) => (
            <li key={i}>
              <a
                className="results-link"
                href={`/results/user/${activeFolder}/${file}`}
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
        <h1 className="results-main-title">📊 Processed Dataset Chunks</h1>
        <p className="results-description">
          View results from internal and user-submitted jobs. You can browse by folder or search by job ID.
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
        {renderSection('⚙️ Internal Results', filter(internalResults))}
        {!activeFolder && renderSection('🧑‍💼 User Results (Folders)', filter(userFolders), true)}
        {activeFolder && renderFolderContents()}
      </div>
    </div>
  );
}