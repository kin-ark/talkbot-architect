import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import '@fontsource-variable/inter'
import './index.css'
import './theme/code.css'
import App from './App.jsx'
import { getInitialTheme, applyTheme } from './theme/useTheme'
import ToastViewport from './components/ToastViewport'
import { ConfirmProvider } from './confirm/ConfirmProvider'

applyTheme(getInitialTheme())

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <ConfirmProvider>
      <App />
    </ConfirmProvider>
    <ToastViewport />
  </StrictMode>,
)
