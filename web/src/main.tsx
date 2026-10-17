import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./index.css";
import { ErrorStatusProvider } from "./ErrorStatus";
import { ScreenSwitcher } from "./ScreenSwitcher";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ErrorStatusProvider>
      <ScreenSwitcher />
    </ErrorStatusProvider>
  </StrictMode>,
);
