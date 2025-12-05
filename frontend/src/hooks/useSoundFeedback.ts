import { useCallback } from "react";

// Sonidos cortos en base64 para no depender de archivos externos inmediatos
const SOUNDS = {
  success: "data:audio/wav;base64,UklGRl9vT1BXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YU", // Placeholder muy corto
  error: "data:audio/wav;base64,UklGRl9vT1BXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YU", // Placeholder
  beep: "data:audio/wav;base64,UklGRl9vT1BXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YU", // Placeholder
};

// En una implementación real, usaríamos archivos .mp3 o .wav reales en /assets/sounds/
// Por ahora, definimos la interfaz.

export type SoundType = "success" | "error" | "beep" | "click";

export function useSoundFeedback() {
  const playSound = useCallback((type: SoundType) => {
    // En un entorno real, aquí cargaríamos el audio.
    // Como no tengo los archivos de audio a mano, dejaré la lógica preparada.
    // const audio = new Audio(\`/assets/sounds/\${type}.mp3\`);
    // audio.play().catch(e => console.warn("Audio play failed", e));

    // Simulación visual en consola para desarrollo
    console.log(`[SoundFeedback] Playing: ${type}`);
  }, []);

  return { playSound };
}
