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

# Memoria temporal por número de teléfono
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
2. Recuerda los datos que el cliente ya te haya compartido en la conversación (nombre, servicio deseado, hora, etc.). NO vuelvas a pedir información que ya se ha mencionado.
3. Si el cliente indica su nombre, el servicio y la hora deseada, confirma la cita de manera clara y directa.
4. Respuestas concisas e ideales para WhatsApp (evita párrafos excesivamente largos).
"""
    return prompt.strip()

def process_message(user_phone, user_message):
    """
    Procesa un mensaje entrante manteniendo el historial del usuario.
    """
    global conversation_history

    # Crear historial para nuevos usuarios
    if user_phone not in conversation_history:
        conversation_history[user_phone] = [
            {"role": "system", "content": get_system_prompt()}
        ]

    # Añadir el mensaje actual del cliente
    conversation_history[user_phone].append({"role": "user", "content": user_message})

    # Mantener el historial dentro de un tamaño manejable (últimos 10 mensajes)
    if len(conversation_history[user_phone]) > 12:
        # Conservar el prompt inicial del sistema y los últimos 10 mensajes
        system_prompt = conversation_history[user_phone][0]
        recent_messages = conversation_history[user_phone][-10:]
        conversation_history[user_phone] = [system_prompt] + recent_messages

    try:
        # Llamar a OpenAI enviando todo el contexto
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=conversation_history[user_phone],
            temperature=0.7
        )
        
        bot_reply = response.choices[0].message.content.strip()

        # Guardar la respuesta del asistente en el historial
        conversation_history[user_phone].append({"role": "assistant", "content": bot_reply})

        return bot_reply

    except Exception as e:
        print(f"Error generando respuesta con OpenAI: {e}")
        return "Lo siento, tuve un inconveniente procesando tu solicitud. Por favor intenta de nuevo en un momento."
