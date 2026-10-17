import json
import os
from openai import OpenAI

# Inicializar cliente de OpenAI
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# Cargar configuración del negocio
def load_config():
    try:
        with open("config.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error cargando config.json: {e}")
        return {}

# Memoria de conversación por número de cliente
conversation_history = {}

def get_system_prompt():
    config = load_config()
    business_name = config.get("business_name", "la Barbería")
    services = config.get("services", [])
    hours = config.get("business_hours", "Lunes a Sábado de 9:00 AM a 8:00 PM")
    
    services_text = "\n".join([f"- {s.get('name')}: ${s.get('price')}" for s in services])
    
    prompt = f"""
Eres el asistente virtual oficial de {business_name}. Tu objetivo es brindar atención al cliente fluida, amable y natural, ayudando a agendar citas y respondiendo preguntas sobre nuestros servicios.

Servicios y precios actuales:
{services_text}

Horario de atención:
{hours}

Instrucciones de comportamiento:
1. Mantén un tono amigable, profesional y cercano.
2. Recuerda SIEMPRE la información previa enviada por el cliente (nombre, servicio deseado, hora). NO vuelvas a pedir datos que el cliente ya te dio en la conversación.
3. Cuando el cliente te dé su nombre, servicio y hora, confirma la cita de forma clara.
4. Respuestas breves y directas, óptimas para WhatsApp.
"""
    return prompt.strip()

def procesar_mensaje_cliente(user_phone, user_message):
    """
    Procesa un mensaje manteniendo la memoria de conversación por número telefónico.
    """
    global conversation_history

    # Si es la primera vez que escribe este número, iniciamos su historial
    if user_phone not in conversation_history:
        conversation_history[user_phone] = [
            {"role": "system", "content": get_system_prompt()}
        ]

    # Agregar el mensaje entrante del usuario
    conversation_history[user_phone].append({"role": "user", "content": user_message})

    # Mantener máximo los últimos 10 mensajes en memoria para optimizar el contexto
    if len(conversation_history[user_phone]) > 12:
        system_prompt = conversation_history[user_phone][0]
        recent_messages = conversation_history[user_phone][-10:]
        conversation_history[user_phone] = [system_prompt] + recent_messages

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=conversation_history[user_phone],
            temperature=0.7
        )
        
        bot_reply = response.choices[0].message.content.strip()

        # Guardar la respuesta dada en el historial del cliente
        conversation_history[user_phone].append({"role": "assistant", "content": bot_reply})

        return bot_reply

    except Exception as e:
        print(f"Error con la API de OpenAI: {e}")
        return "Lo siento, tuve un pequeño inconveniente procesando tu mensaje. ¿Me lo podrías repetir?"
