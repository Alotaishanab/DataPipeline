import React, { useState, useRef } from 'react';
import { Link } from 'react-router-dom';
import './Home.css';

export default function Home() {
  const [file, setFile] = useState(null);
  const [message, setMessage] = useState(null);
  const [jobId, setJobId] = useState(null);
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef();

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!file) {
      setMessage('Please select a file to upload.');
      return;
    }

    setUploading(true);
    setMessage(null);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch('/upload', {
        method: 'POST',
        body: formData,
      });

      const data = await response.json();

      if (data.job_id) {
        setJobId(data.job_id);
        setMessage(`✅ Upload successful! Save this job ID: ${data.job_id}`);
      } else {
        setMessage(data.message || 'Upload succeeded.');
      }
    } catch (err) {
      setMessage('❌ Upload failed. Please try again.');
    } finally {
      setUploading(false);
    }
  };

  const handleFileChange = (e) => {
    const selected = e.target.files[0];
    if (selected) setFile(selected);
  };

  return (
    <div className="home-container">
      <div className="home-box">
        <h1 className="home-title">UniRef50 Dataset Processor</h1>
        <p className="home-description">
          Upload a <strong>.fasta</strong> or <strong>.fasta.gz</strong> file.
          Your dataset will be split into smaller chunks and processed using the ESM2 model.
          You'll receive a job ID to track your results. Check the "Processed Results" tab to view them.
        </p>

        <div className="home-nav-buttons">
          <Link to="/datasets" className="home-button">Browse Datasets</Link>
          <Link to="/results" className="home-button">View Processed Results</Link>
        </div>

        <hr className="home-divider" />

        <h2 className="upload-title">Upload Your File</h2>
        <p className="upload-instructions">
          Results will be available shortly after processing completes.
        </p>

        <form onSubmit={handleUpload} className="upload-form">
          <div className="custom-upload-wrapper">
            <button
              type="button"
              className="custom-file-button"
              onClick={() => fileInputRef.current.click()}
            >
              {file ? `Selected: ${file.name}` : 'Choose a FASTA or FASTA.GZ File'}
            </button>
            <input
              type="file"
              accept=".fasta,.gz"
              onChange={handleFileChange}
              ref={fileInputRef}
              style={{ display: 'none' }}
            />
          </div>

          <button
            type="submit"
            className="upload-button"
            disabled={uploading}
          >
            {uploading ? 'Uploading...' : 'Submit'}
          </button>
        </form>

        {message && <p className="upload-message">{message}</p>}

        {jobId && (
          <div className="job-id-box">
            <p>🔑 Your Job ID:</p>
            <code>{jobId}</code>
            <p>Bookmark or save this to track your results.</p>
          </div>
        )}
      </div>
    </div>
  );
}
