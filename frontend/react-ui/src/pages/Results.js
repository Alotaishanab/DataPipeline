import React, { useEffect, useState } from 'react';
import './Results.css';

export default function Results() {
  const [results, setResults] = useState([]);
  const [datasets, setDatasets] = useState([]);

  const fetchFiles = async (path, setter) => {
    try {
      const res = await fetch(path);
      const text = await res.text();
      const matches = [...text.matchAll(/href="(.*?\.json|\.fasta(?:\.gz)?)"/g)].map(m => m[1]);
      setter(matches);
    } catch (err) {
      console.error(`Failed to fetch ${path}:`, err);
    }
  };

  useEffect(() => {
    fetchFiles('/results/', setResults);
    fetchFiles('/datasets/', setDatasets);
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
        <p className="no-results">🚫 No files found.</p>
      )}
    </div>
  );

  return (
    <div className="results-container">
      {renderSection('🧬 Datasets', datasets, '/datasets/')}
      {renderSection('🧪 Processed Results', results, '/results/')}
    </div>
  );
}
