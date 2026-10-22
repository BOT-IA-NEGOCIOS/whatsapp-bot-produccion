import os
import json
import sqlite3
import requests
from flask import Flask, request, jsonify
from openai import OpenAI

app = Flask(__name__)

# Configuración de credenciales seguras desde Render
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
ULTRAMSG_INSTANCE_ID = os.environ.get("ULTRAMSG_INSTANCE_ID")
ULTRAMSG_TOKEN = os.environ.get("ULTRAMSG_TOKEN")
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
# 3. SISTEMA DE ALERTAS AL ADMINISTRADOR
# ==========================================
def enviar_alerta_al_negocio(nombre, telefono, direccion, pedido):
    if not ADMIN_PHONE:
        return
    url = f"https://api.ultramsg.com/{ULTRAMSG_INSTANCE_ID}/messages/chat"
    mensaje = (
        f"🚨 *¡NUEVO PEDIDO COMPLETADO!* 🚨\n\n"
        f"👤 *Cliente:* {nombre}\n"
        f"📱 *Teléfono:* {telefono}\n"
        f"📍 *Dirección:* {direccion}\n"
        f"🛍️ *Detalle:* {pedido}"
    )
    payload = {'token': ULTRAMSG_TOKEN, 'to': ADMIN_PHONE, 'body': mensaje}
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print(f"Error al enviar alerta: {e}")

# ==========================================
# 4. WEBHOOK DE WHATSAPP
# ==========================================
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    
    if data and 'data' in data:
        message_data = data['data']
        from_number = message_data.get('from', '')
        body = message_data.get('body', '')
        is_from_me = message_data.get('fromMe', False)
        
        if is_from_me or not body:
            return jsonify({"status": "ignored"}), 200

        telefono_cliente = from_number.split('@')[0]

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

        try:
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

            # Enviar respuesta al cliente
            enviar_respuesta_ultramsg(telefono_cliente, respuesta_ia)

        except Exception as e:
            print(f"Error procesando con OpenAI: {e}")

    return jsonify({"status": "success"}), 200

def enviar_respuesta_ultramsg(to, message):
    url = f"https://api.ultramsg.com/{ULTRAMSG_INSTANCE_ID}/messages/chat"
    payload = {'token': ULTRAMSG_TOKEN, 'to': to, 'body': message}
    requests.post(url, data=payload)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
