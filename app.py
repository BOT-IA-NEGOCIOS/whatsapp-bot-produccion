from flask import Flask, request, jsonify
import requests
import bot_engine

app = Flask(__name__)

# Configuración de tu cuenta de UltraMsg (Sácala de la pantalla principal de UltraMsg)
ULTRAMSG_INSTANCE_ID = "instance194595"  # Tu ID de instancia
ULTRAMSG_TOKEN = "276v3f4f8q6fn0rw"      # Tu Token de UltraMsg

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

@app.route('/webhook', methods=['POST'])
def whatsapp_webhook():
    try:
        data = request.json
        print("Datos recibidos de WhatsApp:", data)
        
        # Extraer el texto y el número del remitente
        incoming_msg = ""
        sender_phone = ""
        
        if 'data' in data and isinstance(data['data'], dict):
            incoming_msg = data['data'].get('body', '') or data['data'].get('text', '')
            sender_phone = data['data'].get('from', '')
            
        if not incoming_msg:
            incoming_msg = data.get('message', '') or data.get('body', '') or data.get('text', '')
            sender_phone = data.get('from', '')
            
        if not incoming_msg or not sender_phone:
            return jsonify({"status": "error", "message": "Datos incompletos"}), 400
            
        print(f"Mensaje de {sender_phone}: {incoming_msg}")
        
        # 1. Generar la respuesta con la Inteligencia Artificial
        response_text = bot_engine.procesar_mensaje_cliente(incoming_msg)
        print(f"Respuesta IA: {response_text}")
        
        # 2. Enviar el mensaje de vuelta al celular del cliente por WhatsApp
        enviar_mensaje_whatsapp(sender_phone, response_text)
        
        return jsonify({"status": "success"}), 200
        
    except Exception as e:
        print(f"Error en el servidor: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)