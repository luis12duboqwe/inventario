import React from "react";
import Modal from "../../../../../components/ui/Modal";
import Button from "../../../../../components/ui/Button";
import TextField from "../../../../../components/ui/TextField";

type Props = {
  open?: boolean;
  onClose?: () => void;
  onSubmit?: (payload: { categoryId: string }) => void;
};

export default function MoveCategoryModal({ open, onClose, onSubmit }: Props) {
  const [categoryId, setCategoryId] = React.useState<string>("");

  if (!open) {
    return null;
  }

  const valid = categoryId.trim().length > 0;

  const handleSubmit = () => {
    if (valid && onSubmit) {
      onSubmit({ categoryId });
    }
  };

  return (
    <Modal
      isOpen={open}
      onClose={onClose || (() => {})}
      title="Mover a categoría"
      size="sm"
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>
            Cancelar
          </Button>
          <Button variant="primary" disabled={!valid} onClick={handleSubmit}>
            Mover
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-4">
        <p className="m-0 text-muted-foreground text-sm">Ingresa el ID de la categoría destino.</p>
        <TextField
          placeholder="Categoría ID"
          value={categoryId}
          onChange={(event) => setCategoryId(event.target.value)}
          fullWidth
        />
      </div>
    </Modal>
  );
}
