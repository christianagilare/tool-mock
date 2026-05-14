# Mock Ticket Tool API

Este es un endpoint mock sencillo desarrollado en Python (Flask) y Dockerizado.

## Requisitos

- Docker
- Docker Compose

## Despliegue rápido

Para levantar el servicio en `localhost:5001`, simplemente ejecuta:

```bash
docker-compose up --build
```

## Endpoint

- **URL:** `http://localhost:5001/api/ticket-tool-test`
- **Método:** `POST`
- **Payload:** Cualquier JSON.
- **Respuesta:** 
  - Status: `200 OK`
  - Body:
    ```json
    {
      "success": true,
      "message": "Ticket created successfully",
      "data": {
        "ticketId": "TCK-1001",
        "status": "OPEN",
        "createdAt": "2026-05-14T09:00:00Z"
      }
    }
    ```

## Probar con cURL

```bash
curl -X POST http://localhost:5001/api/ticket-tool-test \
     -H "Content-Type: application/json" \
     -d '{"test": "data", "issue": "No puedo entrar al sistema"}'
```
