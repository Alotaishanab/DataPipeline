// src/pages/Datasets.js
import React, { useEffect, useState } from 'react';
import './Results.css'; // Reuse the same dark theme

export default function Datasets() {
  const [files, setFiles] = useState([]);

  useEffect(() => {
    const fetchDatasets = async () => {
      try {
        const res = await fetch('/datasets/');
        const text = await res.text();
        const matches = [...text.matchAll(/href="(.*?)"/g)]
          .map(m => m[1])
          .filter(file => !file.startsWith('?')); // ignore Apache ? icons
        setFiles(matches);
      } catch (err) {
        console.error(err);
      }
    };

    fetchDatasets();
  }, []);

  return (
    <div className="results-container">
      <div className="results-card">
        <h1 className="results-title">📦 Available Datasets</h1>
        {files.length > 0 ? (
          <ul className="results-list">
            {files.map((file, i) => (
              <li key={i}>
                <a href={`/datasets/${file}`} target="_blank" rel="noreferrer">
                  {file}
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
