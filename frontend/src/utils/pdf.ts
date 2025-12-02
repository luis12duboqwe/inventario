
/**
 * Generates a simple PDF blob from a text summary.
 * This is a client-side PDF generation utility for simple text reports.
 *
 * @param summary The text content to include in the PDF
 * @returns A Blob containing the PDF data
 */
export function buildSmartSummaryPdf(summary: string): Blob {
  const sanitizedLines = summary.split("\n").map((line) => line.replace(/([()\\])/g, "\\$1"));
  const streamLines = ["BT", "/F1 12 Tf", "50 800 Td"];
  sanitizedLines.forEach((line, index) => {
    if (index === 0) {
      streamLines.push(`(${line}) Tj`);
    } else {
      streamLines.push("T*");
      streamLines.push(`(${line}) Tj`);
    }
  });
  streamLines.push("ET");
  const header = "%PDF-1.4\n";
  const objects = [
    "1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj",
    "2 0 obj << /Type /Pages /Count 1 /Kids [3 0 R] >> endobj",
    "3 0 obj << /Type /Page /Parent 2 0 R /Resources << /Font << /F1 4 0 R >> >> /MediaBox [0 0 595 842] /Contents 5 0 R >> endobj",
    "4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj",
  ];
  const stream = streamLines.join("\n");
  const contentObject = `5 0 obj << /Length ${
    stream.length + 1
  } >> stream\n${stream}\nendstream endobj`;
  const body = `${objects.join("\n")}\n${contentObject}`;

  const entries = [...objects, contentObject];
  const offsets: number[] = [];
  let cursor = header.length;
  for (const entry of entries) {
    offsets.push(cursor);
    cursor += entry.length + 1;
  }

  const xrefEntries = offsets
    .map((offset) => `${offset.toString().padStart(10, "0")} 00000 n `)
    .join("\n");
  const xref = `xref\n0 ${offsets.length + 1}\n0000000000 65535 f \n${xrefEntries}\n`;
  const xrefPosition = header.length + body.length + 1;
  const trailer = `trailer << /Size ${
    offsets.length + 1
  } /Root 1 0 R >>\nstartxref\n${xrefPosition}\n%%EOF`;
  return new Blob([header, body, "\n", xref, trailer], { type: "application/pdf" });
}
