type Props = {
  number?: string;
  status?: string;
  from?: string;
  to?: string;
  onPick?: () => void;
  onPack?: () => void;
  onShip?: () => void;
  onReceive?: () => void;
  onCancel?: () => void;
};

function Header({ number, status, from, to, onPick, onPack, onShip, onReceive, onCancel }: Props) {
  return (
    <header className="transfer-header">
      <div>
        <span className="transfer-header__subtitle">Transferencia</span>
        <h2>{number ?? "—"}</h2>
        <p>
          {from ?? "—"} → {to ?? "—"} · {status ?? "REQUESTED"}
        </p>
      </div>
      <div className="transfer-header__actions">
        <button type="button" className="ghost" onClick={onPick}>
          Picking
        </button>
        <button type="button" className="ghost" onClick={onPack}>
          Empaquetar
        </button>
        <button type="button" className="ghost" onClick={onShip}>
          Enviar
        </button>
        <button type="button" className="primary" onClick={onReceive}>
          Recibir
        </button>
        <button type="button" className="danger" onClick={onCancel}>
          Cancelar
        </button>
      </div>
    </header>
  );
}

export default Header;
