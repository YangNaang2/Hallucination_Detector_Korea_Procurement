import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./index.css";
import SecureDocChat from "./components/SecureDocChat.jsx";

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <SecureDocChat />
  </StrictMode>
);
