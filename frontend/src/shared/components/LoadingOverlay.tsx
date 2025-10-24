import { AnimatePresence, motion } from "framer-motion";

type Props = {
  visible: boolean;
  label?: string;
};

function LoadingOverlay({ visible, label = "Cargando información..." }: Props) {
  return (
    <AnimatePresence>
      {visible ? (
        <motion.div
          className="loading-overlay"
          role="status"
          aria-live="polite"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.3 }}
        >
          <div className="spinner" aria-hidden="true" />
          <p>{label}</p>
        </motion.div>
      ) : null}
    </AnimatePresence>
  );
}

export default LoadingOverlay;
