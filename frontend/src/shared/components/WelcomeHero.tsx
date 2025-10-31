import { memo } from "react";
import { motion } from "framer-motion";

import Button from "./ui/Button";
import { colors } from "../../theme/designTokens";

type Props = {
  themeLabel: string;
  onToggleTheme: () => void;
  activeTheme: "dark" | "light";
};

const logoVariants = {
  initial: { opacity: 0, scale: 0.8, rotateX: -12 },
  animate: { opacity: 1, scale: 1, rotateX: 0 },
};

const cardVariants = {
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0 },
};

function WelcomeHero({ themeLabel, onToggleTheme, activeTheme }: Props) {
  return (
    <motion.section
      className="card welcome-hero"
      initial="initial"
      animate="animate"
      transition={{ staggerChildren: 0.2, duration: 0.6, ease: "easeOut" }}
    >
      <motion.div variants={logoVariants} className="welcome-logo" aria-hidden="true">
        <svg viewBox="0 0 180 64" role="img" aria-label="Softmobile" focusable="false">
          <defs>
            <linearGradient id="softmobileGradient" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor={colors.accent} />
              <stop offset="50%" stopColor={colors.accentBright} />
              <stop offset="100%" stopColor={colors.accentDeep} />
            </linearGradient>
          </defs>
          <path
            d="M21.4 48.6c-11.8 0-19.9-6.3-19.9-15.9 0-8.2 6.1-13 15.8-14.6l7.8-1.3c4.3-.7 6.3-2.1 6.3-4.4 0-3.1-3.3-5.1-8.7-5.1-6 0-9.7 2.2-10.4 6.5H2.3C3.1 6.5 11.5.7 22.7.7 34 0.7 41.6 6 41.6 14.9c0 7.9-5.4 12.5-15.3 14.1l-7.9 1.3c-4.9.8-7 2.4-7 5 0 3.1 3.7 5.2 9.4 5.2 6.5 0 10.5-2.3 11.3-6.9h10.1C41.5 42.7 33.2 48.6 21.4 48.6Z"
            fill="url(#softmobileGradient)"
          />
          <path
            d="M50.7 47.6V16.4h10.6v5c1.9-3.8 5.8-5.7 11-5.7 8.7 0 14.8 6.1 14.8 15.3v16.6H76.4V33c0-4.7-3-7.8-7.5-7.8-5 0-7.9 3.3-7.9 8.6v13.8H50.7ZM119.3 48.3c-10.4 0-18-7.1-18-16.6 0-9.6 7.5-16.6 18.2-16.6 10.4 0 18 7 18 16.5 0 9.6-7.5 16.7-18.2 16.7Zm0-9.2c4.7 0 8-3.1 8-7.5 0-4.4-3.3-7.5-8-7.5s-8 3.1-8 7.5c0 4.4 3.3 7.5 8 7.5ZM162.3 48.3c-10.4 0-18-7.1-18-16.6 0-9.6 7.5-16.6 18.2-16.6 10.4 0 18 7 18 16.5 0 9.6-7.5 16.7-18.2 16.7Zm0-9.2c4.7 0 8-3.1 8-7.5 0-4.4-3.3-7.5-8-7.5s-8 3.1-8 7.5c0 4.4 3.3 7.5 8 7.5Z"
            fill={colors.textSecondary}
          />
        </svg>
      </motion.div>
      <motion.div variants={cardVariants} className="welcome-copy">
        <h1>Softmobile Inventario</h1>
        <p>
          Plataforma corporativa para sincronizar existencias, capturar movimientos y obtener reportes en tiempo real con
          tema {themeLabel}.
        </p>
        <div className="welcome-actions">
          <Button type="button" variant="ghost" size="sm" onClick={onToggleTheme}>
            Cambiar a tema {activeTheme === "dark" ? "claro" : "oscuro"}
          </Button>
        </div>
      </motion.div>
    </motion.section>
  );
}

export default memo(WelcomeHero);
