import { useEffect } from "react";

type KeyCombo = {
  key: string;
  ctrl?: boolean;
  alt?: boolean;
  shift?: boolean;
  meta?: boolean;
};

type HotkeyAction = (e: KeyboardEvent) => void;

export function useHotkeys(
  keyCombo: string | KeyCombo,
  callback: HotkeyAction,
  deps: unknown[] = []
) {
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      const combo = typeof keyCombo === "string" ? { key: keyCombo } : keyCombo;

      const keyMatch = event.key.toLowerCase() === combo.key.toLowerCase();
      const ctrlMatch = !!combo.ctrl === event.ctrlKey;
      const altMatch = !!combo.alt === event.altKey;
      const shiftMatch = !!combo.shift === event.shiftKey;
      const metaMatch = !!combo.meta === event.metaKey;

      if (keyMatch && ctrlMatch && altMatch && shiftMatch && metaMatch) {
        event.preventDefault();
        callback(event);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [keyCombo, callback, ...deps]);
}
