// Centralized API Base URL configuration for the frontend app.
// Supports override via Vite environment variables in production.
export const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";
