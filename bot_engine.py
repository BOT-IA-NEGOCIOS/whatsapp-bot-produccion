import json
import os
from openai import OpenAI
from dotenv import load_dotenv

# Cargar las variables del archivo .env
load_dotenv()

def cargar_configuracion():
    """Carga el archivo de configuración JSON con los datos del negocio."""
    with open('config.json', 'r', encoding='utf-8') as f:
        return json.load(f)

def procesar_mensaje_cliente(mensaje_cliente):
    """
    Procesa la consulta enviada desde WhatsApp utilizando OpenAI (gpt-4o-mini)
    y la base de conocimientos definida en config.json.
    """
    try:
        config = cargar_configuracion()
        
        # Prompt del sistema con la inteligencia comercial del negocio
        prompt_sistema = f"""
{config.get('system_prompt', '')}

Menú y Reglas del Negocio ({config.get('business_name', 'Negocio')}):
{json.dumps(config.get('knowledge_base', {}), ensure_ascii=False, indent=2)}

Instrucción estricta: Si el cliente hace un pedido, desglósale los precios, recuérdale el costo del domicilio ($4.000) y pídele amablemente su dirección exacta y teléfono de contacto para confirmar el despacho.
"""

        # Inicializar cliente de OpenAI leyendo la llave del .env
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": prompt_sistema},
                {"role": "user", "content": mensaje_cliente}
            ]
        )

        return response.choices[0].message.content

    except Exception as e:
        print(f"Error procesando mensaje: {e}")
        return "Lo siento, tuve un inconveniente técnico al procesar tu solicitud. Por favor intenta de nuevo."