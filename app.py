import os
import json
import sqlite3
import requests
from flask import Flask, request, jsonify
from openai import OpenAI

app = Flask(__name__)

# Configuración de credenciales seguras desde Render (Meta Cloud API + OpenAI)
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID")
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN")
ADMIN_PHONE = os.environ.get("ADMIN_PHONE")

# ==========================================
# 1. CARGAR CONFIGURACIÓN DINÁMICA DEL NEGOCIO
# ==========================================
def cargar_configuracion():
    """Lee el config.json para que el bot adopte la personalidad del cliente."""
    try:
        with open("config.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error cargando config.json: {e}")
        return {"business_name": "Negocio", "services": [], "faq": []}

# ==========================================
# 2. GESTIÓN DE BASE DE DATOS (SQLite)
# ==========================================
def inicializar_bd():
    conn = sqlite3.connect('clientes_negocio.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pedidos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telefono TEXT,
            nombre TEXT,
            direccion TEXT,
            pedido TEXT,
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def guardar_pedido_en_db(telefono, nombre, direccion, pedido):
    conn = sqlite3.connect('clientes_negocio.db')
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO pedidos (telefono, nombre, direccion, pedido) VALUES (?, ?, ?, ?)",
        (telefono, nombre, direccion, pedido)
    )
    conn.commit()
    conn.close()

inicializar_bd()

# ==========================================
# 3. ENVÍO DE MENSAJES Y ALERTAS (Meta Cloud API)
# ==========================================
def enviar_mensaje_meta(to, message):
    """Envía un mensaje de texto usando la API Cloud oficial de Meta."""
    if not WHATSAPP_TOKEN or not PHONE_NUMBER_ID:
        print("Error: Faltan credenciales de Meta (WHATSAPP_TOKEN o PHONE_NUMBER_ID)")
        return
    
    url = f"https://graph.facebook.com/v17.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": message}
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code != 200:
            print(f"Error enviando mensaje via Meta: {response.text}")
    except Exception as e:
        print(f"Excepción al enviar mensaje con Meta: {e}")

def enviar_alerta_al_negocio(nombre, telefono, direccion, pedido):
    if not ADMIN_PHONE:
        return
    mensaje = (
        f"🚨 *¡NUEVO PEDIDO COMPLETADO!* 🚨\n\n"
        f"👤 *Cliente:* {nombre}\n"
        f"📱 *Teléfono:* {telefono}\n"
        f"📍 *Dirección:* {direccion}\n"
        f"🛍️ *Detalle:* {pedido}"
    )
    enviar_mensaje_meta(ADMIN_PHONE, mensaje)

# ==========================================
# 4. WEBHOOK DE WHATSAPP (GET y POST)
# ==========================================
@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    # 1. Verificación del Webhook por parte de Meta (GET)
    if request.method == 'GET':
        mode = request.args.get('hub.mode')
        token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')
        
        if mode and token:
            if mode == 'subscribe' and token == VERIFY_TOKEN:
                return challenge, 200
            else:
                return 'Token de verificación incorrecto', 403
        return 'Parámetros faltantes', 400

    # 2. Recepción de mensajes de usuarios (POST)
    elif request.method == 'POST':
        data = request.json
        
        try:
            # Estructura del payload de Meta Cloud API
            if data and "entry" in data:
                for entry in data["entry"]:
                    for change in entry.get("changes", []):
                        value = change.get("value", {})
                        if "messages" in value:
                            message = value["messages"][0]
                            telefono_cliente = message.get("from")
                            
                            # Validar si es mensaje de texto
                            if message.get("type") == "text":
                                body = message["text"].get("body", "")
                                
                                if not body:
                                    return jsonify({"status": "ignored"}), 200

                                # Cargamos los datos del negocio desde config.json
                                config = cargar_configuracion()
                                business_name = config.get("business_name", "nuestro negocio")
                                services = json.dumps(config.get("services", []), ensure_ascii=False)
                                faq = json.dumps(config.get("faq", []), ensure_ascii=False)

                                prompt_sistema = (
                                    f"Eres el asistente virtual de ventas oficial de '{business_name}'. "
                                    f"Tus servicios/productos y precios son: {services}. "
                                    f"Preguntas frecuentes: {faq}. "
                                    "Tu objetivo es guiar al cliente, responder preguntas y OBLIGATORIAMENTE recolectar 3 datos antes de terminar: "
                                    "1. Nombre completo, 2. Dirección de entrega, 3. Pedido exacto. "
                                    "Cuando tengas esos 3 datos, indícale al cliente que su pedido ha sido tomado con éxito."
                                )

                                # Procesar con OpenAI
                                response = client.chat.completions.create(
                                    model="gpt-4o-mini",
                                    messages=[
                                        {"role": "system", "content": prompt_sistema},
                                        {"role": "user", "content": body}
                                    ]
                                )
                                
                                respuesta_ia = response.choices[0].message.content

                                # Si la IA confirma el pedido, lo guardamos y alertamos al dueño
                                if "pedido" in respuesta_ia.lower() or "éxito" in respuesta_ia.lower():
                                    guardar_pedido_en_db(telefono_cliente, "Cliente WhatsApp", "Por confirmar", body)
                                    enviar_alerta_al_negocio("Cliente WhatsApp", telefono_cliente, "Por confirmar", body)

                                # Enviar respuesta al cliente usando Meta Cloud API
                                enviar_mensaje_meta(telefono_cliente, respuesta_ia)

        except Exception as e:
            print(f"Error procesando el webhook de Meta: {e}")

        return jsonify({"status": "success"}), 200

@app.route('/', methods=['GET'])
def home():
    return "Bot de WhatsApp operando correctamente con Meta Cloud API 🚀", 200

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
