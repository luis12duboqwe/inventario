# Frontend Softmobile Inventario

Este módulo React + Vite mantiene la interfaz corporativa en tema oscuro para Softmobile 2025 v2.2.0. La reorganización técnica del 23/10/2025 conserva el diseño existente, pero agrupa los archivos en capas claras y habilita consultas/mutaciones con React Query.

## Estructura de carpetas

```
src/
  app/               # Punto de entrada de la aplicación y orquestadores de routing/estado global
  shared/            # Componentes reutilizables y utilidades UI (botones, formularios, layouts, hero, etc.)
  services/api/      # SDK de frontend con cliente Axios + módulos por dominio (auth, stores, inventory, pos)
  features/          # Espacio reservado para casos de uso compuestos (se mantiene como placeholder)
  pages/             # Contenedores de página o wrappers de rutas específicas
  widgets/           # Pequeños bloques de UI que pueden incrustarse en dashboards/páginas
  modules/           # Módulos funcionales existentes (inventario, operaciones, analítica, etc.)
  config/            # Utilidades de configuración (detectores de entorno, URLs base)
  theme/             # Tokens de diseño y ajustes visuales
  styles.css         # Hoja de estilos global con el tema oscuro corporativo
```

Las carpetas `features/`, `pages/` y `widgets/` incorporan archivos `.gitkeep` como marcadores para mantener la estructura incluso cuando no haya implementaciones nuevas.

## Servicios API y React Query

- `services/api/http.ts` crea un cliente Axios centralizado que adjunta automáticamente el token `Bearer`, maneja `401 Unauthorized` y solicita `/auth/refresh` antes de despachar el evento corporativo `softmobile:unauthorized`.
- `services/api/auth.ts` gestiona flujos de autenticación (bootstrap, login, sesión) y exporta los tipos reutilizados por la UI.
- `services/api/{stores,inventory,pos}.ts` exponen funciones y tipos por dominio para mantener un punto único de acceso al backend.
- `main.tsx` envuelve la aplicación con `QueryClientProvider`, habilitando `useQuery`/`useMutation` en componentes.
- `App.tsx` consume `useMutation` para login seguro y `useQuery` para el estado de bootstrap inicial, manteniendo la compatibilidad visual.

## Consideraciones

- La reorganización no altera estilos ni rutas visibles: todo el impacto es técnico para facilitar pruebas, modularidad y adopción gradual de React Query en los módulos existentes.
- Los componentes y pruebas continúan en español y respetan la paleta corporativa (fondos azul/gris, acentos cian).
- Cualquier nuevo flujo debe documentarse en este archivo y en el README raíz del repositorio para preservar la trazabilidad corporativa.
