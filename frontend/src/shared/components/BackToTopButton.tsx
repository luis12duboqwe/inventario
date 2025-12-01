import { useEffect, useState } from "react";
import { ArrowUp } from "lucide-react";

import Button from "@components/ui/Button";

function BackToTopButton() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      setVisible(window.scrollY > 320);
    };
    handleScroll();
    window.addEventListener("scroll", handleScroll, { passive: true });
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  const handleClick = () => {
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  if (!visible) {
    return null;
  }

  return (
    <Button
      type="button"
      className="back-to-top"
      variant="primary"
      size="sm"
      leadingIcon={<ArrowUp size={18} />}
      onClick={handleClick}
      aria-label="Volver arriba"
    >
      <span className="sr-only">Volver arriba</span>
    </Button>
  );
}

export default BackToTopButton;
