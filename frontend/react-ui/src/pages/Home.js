// src/pages/Home.js
import React, { useState, useRef } from 'react';
import './Home.css';

export default function Home() {
  const [file, setFile] = useState(null);
  const [email, setEmail] = useState('');
  const [message, setMessage] = useState(null);
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef();

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!file || !email) {
      setMessage('Please provide both an email and a file.');
      return;
    }

    setUploading(true);
    setMessage(null);

    const formData = new FormData();
    formData.append('file', file);
    formData.append('email', email); // Add email to the backend request

    try {
      const response = await fetch('/upload', {
        method: 'POST',
        body: formData,
      });

      const data = await response.json();
      setMessage(data.message || 'Uploaded successfully!');
    } catch (err) {
      setMessage('Upload failed. Please try again.');
    } finally {
      setUploading(false);
    }
  };

  const handleFileChange = (e) => {
    const selected = e.target.files[0];
    if (selected) {
      setFile(selected);
    }
  };

  return (
    <div className="home-container">
      <div className="home-box">
        <h1 className="home-title">🧬 UniRef50 Dataset Processor</h1>
        <p className="home-description">
          Upload your FASTA file for vector embedding and processing with our ESM2-powered pipeline.
          We'll email you when your results are ready!
        </p>

        <a href="/results" className="home-button">📁 View Processed Results</a>

        <hr className="home-divider" />

        <h2 className="upload-title">Upload & Get Notified</h2>
        <form onSubmit={handleUpload} className="upload-form">
          <div className="custom-upload-wrapper">
            <button
              type="button"
              className="custom-file-button"
              onClick={() => fileInputRef.current.click()}
            >
              {file ? `✅ ${file.name}` : '📂 Choose a FASTA File'}
            </button>
            <input
              type="file"
              accept=".fasta"
              onChange={handleFileChange}
              ref={fileInputRef}
              style={{ display: 'none' }}
            />
          </div>

          <input
            type="email"
            placeholder="Enter your email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="email-input"
            required
          />

          <button
            type="submit"
            className="upload-button"
            disabled={uploading}
          >
            {uploading ? '⏳ Uploading...' : '🚀 Submit'}
          </button>
        </form>

        {message && <p className="upload-message">{message}</p>}
      </div>
    </div>
  );
}
