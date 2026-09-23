import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App'
import './index.css'
import { CameraProvider } from './lib/camera'
import { AppProvider } from './lib/store'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <AppProvider>
        <CameraProvider>
          <App />
        </CameraProvider>
      </AppProvider>
    </BrowserRouter>
  </React.StrictMode>,
)
