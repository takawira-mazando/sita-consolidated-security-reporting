import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import App from './App';
import { AuthProvider } from './context/AuthContext';
import { DemoProvider } from './context/DemoContext';
import { setupDemoInterceptor, useDemoInterceptor } from './api/demoInterceptor';
import './styles/global.css';

const storedTheme = localStorage.getItem('sita_theme');
if (storedTheme === 'light') {
  document.body.dataset.theme = 'light';
} else {
  document.body.dataset.theme = 'dark';
}

// Initialize demo interceptor
setupDemoInterceptor();

function AppWithDemo() {
  useDemoInterceptor(); // Sync demo mode with interceptor
  return <App />;
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <AuthProvider>
        <DemoProvider>
          <AppWithDemo />
        </DemoProvider>
      </AuthProvider>
    </BrowserRouter>
  </React.StrictMode>
);
