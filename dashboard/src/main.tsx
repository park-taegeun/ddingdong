import { StrictMode } from "react"
import { createRoot } from "react-dom/client"
import App from "./App.tsx"
import { ErrorBoundary } from "@/components/feedback/ErrorBoundary"
import { OnboardingProvider } from "@/contexts/OnboardingContext"
import { SettingsProvider } from "@/contexts/SettingsContext"
import "./index.css"

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ErrorBoundary>
      <SettingsProvider>
        <OnboardingProvider>
          <App />
        </OnboardingProvider>
      </SettingsProvider>
    </ErrorBoundary>
  </StrictMode>,
)
