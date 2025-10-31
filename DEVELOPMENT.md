# Desarrollo local — Softmobile 2025 v2.2.0

## Requisitos
- Python 3.11
- Node 20

## Pasos rápidos
```bash
cp .env.example .env
make install
make run-backend
# en otra terminal
make run-frontend
```

## Cargar demo
```bash
make seed  # requiere backend arriba y credenciales admin válidas
```

## Pruebas y lint
```bash
make test
make lint
```

## Notas
- Todos los endpoints corporativos requieren header **X-Reason**.
- El módulo de Analítica usa `GET /reports/...` (endpoints mínimos ya incluidos).
