import React from 'react';
import ReactDOM from 'react-dom/client';
import CollaborationDashboard from './components/CollaborationDashboard';
import './collaboration.css';

const root = ReactDOM.createRoot(
  document.getElementById('collaboration-root') as HTMLElement
);

root.render(
  <React.StrictMode>
    <CollaborationDashboard />
  </React.StrictMode>
);
