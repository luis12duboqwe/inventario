import React, { useState } from "react";
import { Save } from "lucide-react";
import Modal from "@components/ui/Modal";
import TextField from "@components/ui/TextField";
import Button from "@components/ui/Button";

export interface QuickCustomer {
  nombre: string;
  telefono: string;
  correo: string;
  direccion: string;
  tipo: string;
}

interface QuickCustomerModalProps {
  onClose: () => void;
  onSave: (customer: QuickCustomer) => void;
}

export const QuickCustomerModal: React.FC<QuickCustomerModalProps> = ({ onClose, onSave }) => {
  const [formData, setFormData] = useState<QuickCustomer>({
    nombre: "",
    telefono: "",
    correo: "",
    direccion: "",
    tipo: "regular",
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSave(formData);
  };

  return (
    <Modal open={true} onClose={onClose} title="Nuevo Cliente Rápido" size="md">
      <form onSubmit={handleSubmit} className="space-y-4">
        <TextField
          label="Nombre Completo"
          value={formData.nombre}
          onChange={(e) => setFormData({ ...formData, nombre: e.target.value })}
          required
        />
        <div className="grid grid-cols-2 gap-4">
          <TextField
            label="Teléfono"
            value={formData.telefono}
            onChange={(e) => setFormData({ ...formData, telefono: e.target.value })}
            required
          />
          <TextField
            label="Correo Electrónico"
            type="email"
            value={formData.correo}
            onChange={(e) => setFormData({ ...formData, correo: e.target.value })}
          />
        </div>
        <TextField
          label="Dirección"
          value={formData.direccion}
          onChange={(e) => setFormData({ ...formData, direccion: e.target.value })}
        />
        <div className="flex justify-end gap-2 pt-4">
          <Button variant="ghost" onClick={onClose} type="button">
            Cancelar
          </Button>
          <Button variant="primary" type="submit">
            <Save className="w-4 h-4 mr-2" />
            Guardar Cliente
          </Button>
        </div>
      </form>
    </Modal>
  );
};
