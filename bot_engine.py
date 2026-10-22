import os
import sqlite3
import requests
from flask import Flask, request, jsonify
from openai import OpenAI

app = Flask(__name__)

# ==========================================
# CONFIGURACIÓN DE CREDENCIALES Y API
# ==========================================
# Inicializa OpenAI y UltraMsg con tus variables de entorno o credenciales
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", "TU_OPENAI_API_KEY"))
ULTRAMSG_INSTANCE_ID = os.environ.get("ULTRAMSG_INSTANCE_ID", "tu_instance_id")
ULTRAMSG_TOKEN = os.environ.get("ULTRAMSG_TOKEN", "tu_token")

# ==========================================
# 1. GESTIÓN DE BASE DE DATOS (SQLite)
# ==========================================
def inicializar_bd():
    """Crea la base de datos y la tabla de pedidos si no existen."""
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
    """Guarda los datos del cliente de forma permanente."""
    conn = sqlite3.connect('clientes_negocio.db')
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO pedidos (telefono, nombre, direccion, pedido) VALUES (?, ?, ?, ?)",
        (telefono, nombre, direccion, pedido)
    )
    conn.commit()
    conn.close()

# Inicializamos la base de datos al arrancar el servidor
inicializar_bd()

# ==========================================
# 2. SISTEMA DE ALERTAS (UltraMsg)
# ==========================================
def enviar_alerta_al_negocio(nombre, telefono, direccion, pedido):
    """Dispara un mensaje automático al WhatsApp del administrador del local."""
    url = f"https://api.ultramsg.com/{ULTRAMSG_INSTANCE_ID}/messages/chat"
    
    # Aquí pones el número de WhatsApp del dueño del negocio que recibirá la alerta
    # (Ejemplo con código de país de Colombia: 573101234567)
    admin_phone = os.environ.get("ADMIN_PHONE", "573000000000") 
    
    mensaje = (
        f"🚨 *¡NUEVO PEDIDO COMPLETADO!* 🚨\n\n"
        f"👤 *Cliente:* {nombre}\n"
        f"📱 *Teléfono:* {telefono}\n"
        f"📍 *Dirección:* {direccion}\n"
        f"🛍️ *Detalle del Pedido:* {pedido}"
    )
    
    payload = {
        'token': ULTRAMSG_TOKEN,
        'to': admin_phone,
        'body': mensaje
    }
    
    try:
        response = requests.post(url, data=payload)
        print(f"Alerta enviada al administrador: {response.status_code}")
    except Exception as e:
        print(f"Error al enviar la alerta: {e}")

# ==========================================
# 3. LÓGICA DEL BOT DE WHATSAPP (Webhook)
# ==========================================
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    
    # Validar que el mensaje venga de WhatsApp y no sea un mensaje enviado por el bot mismo
    if data and 'data' in data:
        message_data = data['data']
        from_number = message_data.get('from', '')
        body = message_data.get('body', '')
        is_from_me = message_data.get('fromMe', False)
        
        if is_from_me or not body:
            return jsonify({"status": "ignored"}), 200

        # Limpiar el número de teléfono del cliente
        telefono_cliente = from_number.split('@')[0]

        # Contexto del bot (Instrucciones para ChatGPT)
        prompt_sistema = (
            "Eres un asistente virtual de ventas amable y eficiente. "
            "Tu objetivo es guiar al cliente, responder preguntas sobre los servicios o productos, "
            "y OBLIGATORIAMENTE recolectar 3 datos antes de terminar: 1. Nombre completo, 2. Dirección de entrega, 3. Pedido exacto. "
            "Una vez que tengas esos tres datos, indícale al cliente que su pedido ha sido tomado con éxito."
        )

        try:
            # Petición a la API de OpenAI (GPT-4o-mini)
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": prompt_sistema},
                    {"role": "user", "content": body}
                ]
            )
            
            respuesta_ia = response.choices[0].message.content

            # [VERIFICACIÓN INTELIGENTE DE DATOS]
            # Si la IA detecta que el pedido está completo, simulamos la extracción y guardado.
            # (En una versión más avanzada puedes usar structured outputs de OpenAI, 
            # pero por ahora validamos palabras clave de cierre o guardamos el registro).
            if "pedido" in respuesta_ia.lower() or "éxito" in respuesta_ia.lower():
                # Ejemplo de captura (puedes adaptarlo según el flujo exacto que te entregue la IA)
                nombre_detectado = "Cliente de WhatsApp" 
                direccion_detectada = "Dirección por confirmar en chat"
                pedido_detectado = body
                
                # Guardamos en la base de datos local
                guardar_pedido_en_db(telefono_cliente, nombre_detectado, direccion_detectada, pedido_detectado)
                
                # Lanzamos la alerta al WhatsApp del administrador
                enviar_alerta_al_negocio(nombre_detectado, telefono_cliente, direccion_detectada, pedido_detectado)

            # Enviar la respuesta de vuelta al cliente a través de UltraMsg
            enviar_respuesta_ultramsg(telefono_cliente, respuesta_ia)

        except Exception as e:
            print(f"Error procesando con OpenAI: {e}")

    return jsonify({"status": "success"}), 200

def enviar_respuesta_ultramsg(to, message):
    """Envía la respuesta de la IA de regreso al WhatsApp del usuario."""
    url = f"https://api.ultramsg.com/{ULTRAMSG_INSTANCE_ID}/messages/chat"
    payload = {
        'token': ULTRAMSG_TOKEN,
        'to': to,
        'body': message
    }
    requests.post(url, data=payload)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
