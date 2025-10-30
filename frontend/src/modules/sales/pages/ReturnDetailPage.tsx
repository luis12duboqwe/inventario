import React from "react";
import { ReturnEditor } from "../components/returns";

export function ReturnDetailPage() {
  return (
    <div style={{ display: "grid", gap: 12 }}>
      <ReturnEditor
        onSubmit={(payload) => {
          // TODO(save)
        }}
      />
      {/* <PrintReturnNote business={{ name: "SOFTMOBILE" }} doc={{ number: "RET-0001", date: new Date().toISOString(), reason: "DEFECT", lines: [] }} /> */}
    </div>
  );
}
