import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./index.css";
import { ScreenSwitcher } from "./ScreenSwitcher";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ScreenSwitcher />
  </StrictMode>,
);
