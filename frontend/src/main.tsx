import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import App from './App';
import { AuthProvider } from './context/AuthContext';
import './styles/global.css';

const storedTheme = localStorage.getItem('sita_theme');
if (storedTheme === 'light') {
  document.body.dataset.theme = 'light';
} else {
  document.body.dataset.theme = 'dark';
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <App />
      </AuthProvider>
    </BrowserRouter>
  </React.StrictMode>
);
