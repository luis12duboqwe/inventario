import React from "react";

export default function SkipLink() {
  return (
    <a
      href="#main-content"
      className="absolute left-2 top-2 px-3 py-2 rounded-lg bg-gray-900 text-gray-200 no-underline -translate-y-[150%] focus:translate-y-0 transition-transform z-50"
    >
      Ir al contenido principal
    </a>
  );
}
