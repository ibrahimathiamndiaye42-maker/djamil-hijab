import React from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App.jsx";
import { AuthProvider } from "./auth.jsx";
import "./pwa.js";
import "./styles.css";

createRoot(document.getElementById("root")).render(
  <BrowserRouter><AuthProvider><App /></AuthProvider></BrowserRouter>
);
if ("serviceWorker" in navigator && import.meta.env.PROD) {
  window.addEventListener("load", () => navigator.serviceWorker.register("/sw.js"));
}
