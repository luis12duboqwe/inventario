type ReceiptViewerProps = {
  saleId: number | null;
  receiptUrl: string | null;
  receiptPdfBase64?: string | null;
};

// [PACK34-UI]
export default function ReceiptViewer({ saleId, receiptUrl, receiptPdfBase64 }: ReceiptViewerProps) {
  if (!saleId) {
    return (
      <section className="card">
        <header className="card__header">
          <h3 className="card__title">Recibo POS</h3>
        </header>
        <p className="muted-text">Genera una venta para visualizar y descargar el recibo.</p>
      </section>
    );
  }

  const downloadHref = receiptPdfBase64 ? `data:application/pdf;base64,${receiptPdfBase64}` : receiptUrl ?? undefined;

  return (
    <section className="card">
      <header className="card__header">
        <h3 className="card__title">Recibo POS #{saleId}</h3>
        {downloadHref ? (
          <a className="btn btn--ghost" href={downloadHref} target="_blank" rel="noreferrer">
            Descargar PDF
          </a>
        ) : null}
      </header>
      {receiptPdfBase64 ? (
        <object
          data={`data:application/pdf;base64,${receiptPdfBase64}`}
          type="application/pdf"
          className="pos-receipt-preview"
          aria-label="Recibo PDF"
        >
          <p>
            El navegador no puede mostrar el PDF embebido. Puedes descargarlo en el botón «Descargar PDF».
          </p>
        </object>
      ) : (
        <p className="muted-text">
          El recibo se encuentra disponible en <code>{receiptUrl}</code>.
        </p>
      )}
    </section>
  );
}

