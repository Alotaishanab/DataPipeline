// src/App.js
import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import Home from './pages/Home';
import Results from './pages/Results';
import Datasets from './pages/Datasets';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/results" element={<Results />} />
        <Route path="/datasets" element={<Datasets />} />
      </Routes>
    </Router>
  );
}

export default App;