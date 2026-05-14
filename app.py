from flask import Flask, request, jsonify
from flask_cors import CORS
import json

app = Flask(__name__)
CORS(app) # Habilita CORS para todos los orígenes

@app.route('/api/ticket-tool-test', methods=['POST'])
def ticket_tool_test():
    # Obtener el payload
    payload = request.get_json(silent=True) or request.form.to_dict() or request.data.decode('utf-8')
    
    print("\n--- NUEVA PETICIÓN RECIBIDA ---")
    print(f"Payload: {payload}")
    print("-------------------------------\n")
    
    # Respuesta solicitada
    response_data = {
        "success": True,
        "message": "Ticket created successfully",
        "data": {
            "ticketId": "TCK-1001",
            "status": "OPEN",
            "createdAt": "2026-05-14T09:00:00Z"
        }
    }
    
    return jsonify(response_data), 200

if __name__ == '__main__':
    # host='0.0.0.0' es necesario para que sea accesible desde fuera del contenedor Docker
    app.run(host='0.0.0.0', port=5001, debug=True)
