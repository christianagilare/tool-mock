from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import uuid
import datetime
import threading
import time
import urllib.request
import urllib.error

app = Flask(__name__)
CORS(app) # Habilita CORS para todos los orígenes

# In-memory storage (cleared on restart)
ACCOUNTS = {
    "ACC-001": {
        "accountId": "ACC-001",
        "debtorRef": "CONTACT-123",
        "balance": 85.50,
        "currency": "USD",
        "daysPastDue": 12,
        "nextDueDate": "2026-06-15",
        "status": "PENDING",
        "reference": "ACC-001"
    },
    "ACC-002": {
        "accountId": "ACC-002",
        "debtorRef": "CONTACT-456",
        "balance": 0.00,
        "currency": "USD",
        "daysPastDue": 0,
        "nextDueDate": None,
        "status": "PAID",
        "reference": "ACC-002"
    }
}

PAYMENT_LINKS_BY_IDEMPOTENCY = {}
PAYMENT_LINKS_BY_REF = {}
PAYMENT_PROMISES_BY_IDEMPOTENCY = {}
PAYMENT_PROMISES_COUNTER = 0


def trigger_webhook_async(session_id, external_reference, amount, currency):
    def run():
        time.sleep(3)
        urls = [
            "http://host.docker.internal:8180/agent-ai-backend/api/webhooks/payments/mock",
            "http://localhost:8180/agent-ai-backend/api/webhooks/payments/mock"
        ]
        payload = {
            "sessionId": session_id,
            "externalReference": external_reference,
            "status": "PAID",
            "amount": amount,
            "currency": currency
        }
        data = json.dumps(payload).encode('utf-8')
        
        success = False
        for webhook_url in urls:
            req = urllib.request.Request(
                webhook_url,
                data=data,
                headers={'Content-Type': 'application/json'}
            )
            try:
                print(f"\n[Webhook] Sending payment notification to {webhook_url}...")
                print(f"[Webhook] Payload: {payload}")
                with urllib.request.urlopen(req, timeout=5) as response:
                    print(f"[Webhook] Received response code: {response.getcode()}")
                    success = True
                    break
            except Exception as e:
                print(f"[Webhook INFO] Attempt to {webhook_url} failed: {e}")
                
        if not success:
            print("[Webhook ERROR] Failed to send webhook to any configured endpoint.")

    threading.Thread(target=run, daemon=True).start()

# --- Health check endpoint ---
@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        "status": "ok",
        "service": "collections-mock"
    }), 200

# --- Ticket Tool endpoint (Must co-exist) ---
@app.route('/api/ticket-tool-test', methods=['POST'])
def ticket_tool_test():
    # Obtener el payload
    payload = request.get_json(silent=True) or request.form.to_dict() or request.data.decode('utf-8')
    
    print("\n--- NUEVA PETICIÓN RECIBIDA (Ticket Tool) ---")
    print(f"Payload: {payload}")
    print("---------------------------------------------\n")
    
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

# --- 1. GET — Consultar cuenta / saldo ---
@app.route('/api/collections/accounts/<accountId>', methods=['GET'])
def get_account(accountId):
    # Log the query parameters
    client_id = request.args.get('clientId')
    conversation_id = request.args.get('conversationId')
    contact_id = request.args.get('contactId')
    debtor_ref = request.args.get('debtorRef')
    
    print(f"\n--- GET ACCOUNT {accountId} ---")
    print(f"clientId: {client_id}, conversationId: {conversation_id}, contactId: {contact_id}, debtorRef: {debtor_ref}")
    
    if accountId not in ACCOUNTS:
        return jsonify({
            "success": False,
            "message": "Cuenta no encontrada",
            "data": None
        }), 404
        
    account_data = ACCOUNTS[accountId].copy()
    
    # Optional override of debtorRef from query parameter or contactId for testing convenience
    effective_debtor_ref = debtor_ref or contact_id
    if effective_debtor_ref:
        account_data["debtorRef"] = effective_debtor_ref
        
    return jsonify({
        "success": True,
        "data": account_data
    }), 200

# --- 1.1 GET — Catálogo de ofertas de negociación ---
@app.route('/api/collections/accounts/<accountId>/negotiation-offers', methods=['GET'])
def get_negotiation_offers(accountId):
    client_id = request.args.get('clientId')
    conversation_id = request.args.get('conversationId')
    contact_id = request.args.get('contactId')
    
    print(f"\n--- GET NEGOTIATION OFFERS for {accountId} ---")
    print(f"clientId: {client_id}, conversationId: {conversation_id}, contactId: {contact_id}")
    
    if accountId == "ACC-001":
        return jsonify({
            "success": True,
            "data": {
                "accountId": "ACC-001",
                "currentBalance": 85.50,
                "currency": "USD",
                "offers": [
                    {
                        "offerId": "OFFER-SETTLE-70",
                        "type": "SETTLEMENT",
                        "title": "Liquidación al 70%",
                        "description": "Paga USD 59.85 y saldas la deuda por completo.",
                        "amount": 59.85,
                        "discountPercent": 30,
                        "currency": "USD",
                        "expiresAt": "2026-12-31",
                        "requiresHumanApproval": True
                    },
                    {
                        "offerId": "OFFER-PARTIAL-50",
                        "type": "PARTIAL_PAYMENT",
                        "title": "Abono mínimo congelación de mora",
                        "description": "Abona USD 42.75 (50% del saldo) y congelamos intereses por 30 días.",
                        "amount": 42.75,
                        "discountPercent": 0,
                        "currency": "USD",
                        "expiresAt": "2026-09-30",
                        "requiresHumanApproval": True
                    },
                    {
                        "offerId": "OFFER-EXTENSION-15",
                        "type": "EXTENSION",
                        "title": "Prórroga 15 días sin recargo",
                        "description": "Nueva fecha límite sin penalidad si confirmas por escrito con un asesor.",
                        "amount": None,
                        "discountPercent": 0,
                        "currency": "USD",
                        "expiresAt": "2026-08-15",
                        "requiresHumanApproval": True
                    }
                ]
            }
        }), 200
    elif accountId == "ACC-002":
        return jsonify({
            "success": True,
            "data": {
                "accountId": "ACC-002",
                "currentBalance": 0,
                "currency": "USD",
                "offers": []
            }
        }), 200
    else:
        return jsonify({
            "success": False,
            "message": "No hay ofertas de negociación para esta cuenta",
            "data": None
        }), 404

# --- 2. POST — Generar link de pago ---
@app.route('/api/collections/payment-links', methods=['POST'])
def generate_payment_link():
    payload = request.get_json(silent=True) or {}
    print(f"\n--- POST PAYMENT LINK ---")
    print(f"Payload: {payload}")
    
    idempotency_key = payload.get("idempotencyKey")
    if not idempotency_key:
        return jsonify({
            "success": False,
            "message": "idempotencyKey is required",
            "data": None
        }), 400
        
    # Check idempotency
    if idempotency_key in PAYMENT_LINKS_BY_IDEMPOTENCY:
        print(f"[Idempotency] Returning cached response for key: {idempotency_key}")
        return jsonify(PAYMENT_LINKS_BY_IDEMPOTENCY[idempotency_key]), 200
        
    account_id = payload.get("accountId")
    amount = payload.get("amount")
    currency = payload.get("currency", "USD")
    provider = payload.get("provider", "mock")
    session_id = payload.get("sessionId")
    
    try:
        amount = float(amount)
    except (TypeError, ValueError):
        return jsonify({
            "success": False,
            "message": "amount is required and must be a number",
            "data": None
        }), 400
        
    suffix = str(uuid.uuid4())[:8]
    external_ref = f"PAY-{suffix}"
    payment_url = f"https://pay.mock.example/checkout/{suffix}"
    
    # Calculate expiry: 2 hours in the future
    expires_at = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=2)).strftime('%Y-%m-%dT%H:%M:%SZ')
    
    response_data = {
        "success": True,
        "data": {
            "paymentUrl": payment_url,
            "externalReference": external_ref,
            "provider": provider,
            "amount": amount,
            "currency": currency,
            "expiresAt": expires_at
        }
    }
    
    # Save to memory
    PAYMENT_LINKS_BY_IDEMPOTENCY[idempotency_key] = response_data
    PAYMENT_LINKS_BY_REF[external_ref] = {
        "sessionId": session_id,
        "amount": amount,
        "currency": currency
    }
    
    return jsonify(response_data), 200

# --- 3. POST — Registrar promesa de pago (PTP) ---
@app.route('/api/collections/payment-promises', methods=['POST'])
def register_payment_promise():
    global PAYMENT_PROMISES_COUNTER
    payload = request.get_json(silent=True) or {}
    print(f"\n--- POST PAYMENT PROMISE ---")
    print(f"Payload: {payload}")
    
    idempotency_key = payload.get("idempotencyKey")
    if not idempotency_key:
        return jsonify({
            "success": False,
            "message": "idempotencyKey is required",
            "data": None
        }), 400
        
    # Check idempotency
    if idempotency_key in PAYMENT_PROMISES_BY_IDEMPOTENCY:
        print(f"[Idempotency] Returning cached response for key: {idempotency_key}")
        return jsonify(PAYMENT_PROMISES_BY_IDEMPOTENCY[idempotency_key]), 200
        
    account_id = payload.get("accountId")
    if not account_id:
        return jsonify({
            "success": False,
            "message": "accountId is required",
            "data": None
        }), 400
        
    # Simulate Account Not Found check
    if account_id == "ACC-NOTFOUND":
        return jsonify({
            "success": False,
            "message": "Cuenta no encontrada",
            "data": None
        }), 404
        
    promised_amount = payload.get("promisedAmount")
    try:
        promised_amount = float(promised_amount)
        if promised_amount <= 0:
            raise ValueError()
    except (TypeError, ValueError):
        return jsonify({
            "success": False,
            "message": "promisedAmount must be a number greater than 0",
            "data": None
        }), 400
        
    promised_date = payload.get("promisedDate")
    if not promised_date:
        return jsonify({
            "success": False,
            "message": "promisedDate is required",
            "data": None
        }), 400
        
    try:
        promised_date_parsed = datetime.datetime.strptime(promised_date, "%Y-%m-%d").date()
        # Use user local timezone (UTC-5) to determine if a date is in the past
        tz_utc5 = datetime.timezone(datetime.timedelta(hours=-5))
        today_utc5 = datetime.datetime.now(tz_utc5).date()
        if promised_date_parsed < today_utc5:
            return jsonify({
                "success": False,
                "message": "promisedDate cannot be in the past",
                "data": None
            }), 400
    except ValueError:
        return jsonify({
            "success": False,
            "message": "promisedDate must be in YYYY-MM-DD format",
            "data": None
        }), 400
        
    promise_id = str(uuid.uuid4())
    # Increment counter and generate sequential external reference (e.g., PTP-MOCK-001)
    PAYMENT_PROMISES_COUNTER += 1
    external_ref = payload.get("externalReference") or f"PTP-MOCK-{PAYMENT_PROMISES_COUNTER:03d}"
    currency = payload.get("currency") or "USD"
    
    response_data = {
        "success": True,
        "data": {
            "promiseId": promise_id,
            "externalReference": external_ref,
            "accountId": account_id,
            "promisedAmount": promised_amount,
            "currency": currency,
            "promisedDate": promised_date,
            "status": "PENDING"
        }
    }
    
    # Save to memory
    PAYMENT_PROMISES_BY_IDEMPOTENCY[idempotency_key] = response_data
    
    return jsonify(response_data), 200

# --- 4. POST — Simular Pago de forma Manual (Utility/Webhook Trigger) ---
@app.route('/api/collections/simulate-payment', methods=['POST'])
def simulate_payment():
    payload = request.get_json(silent=True) or {}
    external_ref = payload.get("externalReference")
    
    print(f"\n--- POST SIMULATE PAYMENT ---")
    print(f"Payload: {payload}")
    
    if not external_ref:
        return jsonify({
            "success": False,
            "message": "Missing externalReference"
        }), 400
        
    link_info = PAYMENT_LINKS_BY_REF.get(external_ref)
    if link_info:
        session_id = link_info.get("sessionId")
        amount = link_info.get("amount")
        currency = link_info.get("currency")
    else:
        # Fallback to defaults or provided values in payload
        session_id = payload.get("sessionId", "6413a38a-c65e-477f-8e89-973df6b0eb46")
        amount = payload.get("amount", 85.50)
        currency = payload.get("currency", "USD")
        
    # Trigger webhook immediately synchronously to provide test feedback
    urls = [
        "http://host.docker.internal:8180/agent-ai-backend/api/webhooks/payments/mock",
        "http://localhost:8180/agent-ai-backend/api/webhooks/payments/mock"
    ]
    webhook_payload = {
        "sessionId": session_id,
        "externalReference": external_ref,
        "status": "PAID",
        "amount": amount,
        "currency": currency
    }
    
    data = json.dumps(webhook_payload).encode('utf-8')
    
    success = False
    last_error = None
    resp_code = None
    
    for webhook_url in urls:
        req = urllib.request.Request(
            webhook_url,
            data=data,
            headers={'Content-Type': 'application/json'}
        )
        try:
            print(f"[Webhook Manual] Sending payment notification to {webhook_url}...")
            with urllib.request.urlopen(req, timeout=5) as response:
                resp_code = response.getcode()
                print(f"[Webhook Manual] Received response code: {resp_code}")
                success = True
                break
        except Exception as e:
            print(f"[Webhook Manual INFO] Attempt to {webhook_url} failed: {e}")
            last_error = e
            
    if success:
        return jsonify({
            "success": True,
            "message": f"Payment webhook triggered. Backend returned code {resp_code}",
            "data": webhook_payload
        }), 200
    else:
        return jsonify({
            "success": False,
            "message": f"Failed to send webhook to backend: {last_error}",
            "data": webhook_payload
        }), 502

if __name__ == '__main__':
    # host='0.0.0.0' es necesario para que sea accesible desde fuera del contenedor Docker
    app.run(host='0.0.0.0', port=5001, debug=True)
