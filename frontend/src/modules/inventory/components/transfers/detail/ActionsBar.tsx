type Props = {
  onPick?: () => void;
  onPack?: () => void;
  onShip?: () => void;
  onReceive?: () => void;
  onPrint?: () => void;
};

function ActionsBar({ onPick, onPack, onShip, onReceive, onPrint }: Props) {
  return (
    <div className="actions-bar">
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
      <button type="button" className="ghost" onClick={onPrint}>
        Imprimir
      </button>
    </div>
  );
}

export default ActionsBar;
