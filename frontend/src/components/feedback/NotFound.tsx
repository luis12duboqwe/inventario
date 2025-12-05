import React from "react";
import { Link } from "react-router-dom";

export default function NotFound() {
  return (
    <div className="not-found-container">
      <div className="not-found-content">
        <h1 className="not-found-title">404</h1>
        <p className="not-found-text">Página no encontrada</p>
        <Link to="/dashboard" className="not-found-button">
          Ir al dashboard
        </Link>
      </div>
    </div>
  );
}
