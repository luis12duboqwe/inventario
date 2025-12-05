import React from "react";
import Modal from "../../../../../components/ui/Modal";
import Button from "../../../../../components/ui/Button";
import TextField from "../../../../../components/ui/TextField";

type Props = {
  open?: boolean;
  onClose?: () => void;
  onSubmit?: (payload: { tags: string[] }) => void;
};

export default function TagModal({ open, onClose, onSubmit }: Props) {
  const [tags, setTags] = React.useState<string>("");

  if (!open) {
    return null;
  }

  const list = tags
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
  const valid = list.length > 0;

  const handleSubmit = () => {
    if (valid && onSubmit) {
      onSubmit({ tags: list });
    }
  };

  return (
    <Modal
      isOpen={open}
      onClose={onClose || (() => {})}
      title="Asignar etiquetas"
      size="sm"
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>
            Cancelar
          </Button>
          <Button variant="primary" disabled={!valid} onClick={handleSubmit}>
            Aplicar
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-4">
        <p className="m-0 text-muted-foreground text-sm">
          Ingresa las etiquetas separadas por coma.
        </p>
        <TextField
          placeholder="tag1, tag2, tag3"
          value={tags}
          onChange={(event) => setTags(event.target.value)}
          fullWidth
        />
      </div>
    </Modal>
  );
}
