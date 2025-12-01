import Modal from "@components/ui/Modal";
import PermissionMatrix, { type PermissionMatrixProps } from "./PermissionMatrix";

export type RoleModalProps = {
  open: boolean;
  onClose: () => void;
} & PermissionMatrixProps;

function RoleModal({ open, onClose, ...permissionProps }: RoleModalProps) {
  return (
    <Modal
      open={open}
      onClose={onClose}
      title={`Permisos para ${permissionProps.selectedRole}`}
      size="lg"
      footer={null}
    >
      <PermissionMatrix {...permissionProps} />
    </Modal>
  );
}

export default RoleModal;
