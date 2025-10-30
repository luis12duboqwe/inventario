// [PACK27-DOWNLOAD-UTILS-START]
export function downloadBlob(data: Blob, filename: string) {
  const url = URL.createObjectURL(data);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 2000);
}

export function downloadText(text: string, filename: string, mime = "text/plain;charset=utf-8") {
  downloadBlob(new Blob([text], { type: mime }), filename);
}

export function openUrlNewTab(url: string) {
  window.open(url, "_blank", "noopener,noreferrer");
}
// [PACK27-DOWNLOAD-UTILS-END]
