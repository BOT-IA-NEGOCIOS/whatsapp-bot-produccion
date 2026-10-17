import os
import requests
from flask import Flask, request, jsonify
from bot_engine import procesar_mensaje_cliente

app = Flask(__name__)

# Credenciales de UltraMsg desde variables de entorno
ULTRAMSG_INSTANCE_ID = os.environ.get("ULTRAMSG_INSTANCE_ID")
ULTRAMSG_TOKEN = os.environ.get("ULTRAMSG_TOKEN")

def enviar_mensaje_whatsapp(numero_destino, texto_respuesta):
    """Envía la respuesta generada por la IA de regreso al cliente mediante UltraMsg."""
    url = f"https://api.ultramsg.com/{ULTRAMSG_INSTANCE_ID}/messages/chat"
    payload = {
        "token": ULTRAMSG_TOKEN,
        "to": numero_destino,
        "body": texto_respuesta
    }
    headers = {'content-type': 'application/x-www-form-urlencoded'}
    try:
        response = requests.post(url, data=payload, headers=headers)
        print("Respuesta de UltraMsg al enviar:", response.json())
    except Exception as e:
        print(f"Error al enviar mensaje por UltraMsg: {e}")

@app.route('/', methods=['GET'])
def home():
    return "Servidor del Bot de WhatsApp activo y en línea.", 200

@app.route('/webhook', methods=['POST'])
def whatsapp_webhook():
    try:
        data = request.json
        print("Datos recibidos de WhatsApp:", data)

        incoming_msg = ""
        sender_phone = ""

        if 'data' in data and isinstance(data['data'], dict):
            incoming_msg = data['data'].get('body', '') or data['data'].get('text', '')
            sender_phone = data['data'].get('from', '')

        # Evitar responder mensajes vacíos o del propio sistema
        if incoming_msg and sender_phone and not data['data'].get('fromMe', False):
            print(f"Mensaje de {sender_phone}: {incoming_msg}")
            
            # Generar respuesta con la IA manteniendo memoria del cliente
            respuesta_bot = procesar_mensaje_cliente(sender_phone, incoming_msg)
            
            # Enviar la respuesta por WhatsApp
            enviar_mensaje_whatsapp(sender_phone, respuesta_bot)

        return jsonify({"status": "success"}), 200

    except Exception as e:
        print(f"Error en el webhook: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
