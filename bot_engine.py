import json
import os
from openai import OpenAI

# Inicializar cliente de OpenAI
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# Cargar configuración del negocio desde config.json
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
    business_name = config.get("business_name", "nuestro negocio")
    services = config.get("services", [])
    hours = config.get("business_hours", "Lunes a Sábado de 9:00 AM a 8:00 PM")
    
    # Formatear catálogo o lista de servicios
    services_text = "\n".join([f"• {s.get('name')}: ${s.get('price')}" for s in services])
    
    prompt = f"""
Eres un asesor de atención al cliente y ventas para {business_name}. Tu estilo de comunicación es cercano, amable, fresco y muy natural, como si fuera una persona de confianza respondiendo por WhatsApp.

Catálogo / Oferta de {business_name}:
{services_text}

Horarios de atención:
{hours}

REGLAS Y OBJETIVOS DE CONVERSACIÓN:
1. TONO HUMANO Y FRESCO: Habla de forma amigable, relajada y directa. Usa respuestas breves (1 a 3 frases máximo por mensaje) y emojis con moderación. Evita sonar como un robot, manual o menú telefónico.
2. MEMORIA ACTIVA: Recuerda absolutamente todo lo que el cliente te ha dicho en la conversación (nombre, interés, horarios, etc.). NUNCA vuelvas a pedir un dato que ya te hayan dado.
3. CAPTURA DE DATOS PARA LA ORDEN / CITA:
   Para completar cualquier agendamiento, pedido o reserva, debes asegurarte de obtener de manera amigable estos datos clave durante la charla:
   - Nombre completo del cliente.
   - Producto / Servicio solicitado.
   - Correo electrónico (diles que es para enviarles la confirmación/recibo).
   - Fecha y hora deseada (o dirección de envío si es producto).
4. CIERRE Y CONFIRMACIÓN: Una vez que tengas todos los datos, dale un resumen bonito y dile que su solicitud ha quedado lista y registrada.
"""
    return prompt.strip()

def procesar_mensaje_cliente(user_phone, user_message):
    """
    Procesa el mensaje del cliente manteniendo el contexto y la recolección de datos.
    """
    global conversation_history

    # Crear historial para clientes nuevos
    if user_phone not in conversation_history:
        conversation_history[user_phone] = [
            {"role": "system", "content": get_system_prompt()}
        ]

    # Añadir mensaje del cliente
    conversation_history[user_phone].append({"role": "user", "content": user_message})

    # Limitar el historial a los últimos 10 mensajes para mantener eficiencia
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

        # Guardar respuesta del bot en la memoria
        conversation_history[user_phone].append({"role": "assistant", "content": bot_reply})

        return bot_reply

    except Exception as e:
        print(f"Error procesando mensaje con OpenAI: {e}")
        return "¡Hola! Tuve un pequeño inconveniente técnico de señal por un segundo. ¿Me podrías repetir tu último mensaje por favor?"

    except Exception as e:
        print(f"Error con la API de OpenAI: {e}")
        return "Lo siento, tuve un pequeño inconveniente procesando tu mensaje. ¿Me lo podrías repetir?"
