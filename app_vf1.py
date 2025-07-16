import streamlit as st
import google.generativeai as genai

# Configurar la clave API de Gemini
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

st.set_page_config(page_title="Agente de Historias", layout="wide")
st.title("📚 Chatbot Generador de Historias")

st.markdown("Interactúa con el chatbot para construir tu historia paso a paso. El agente validará tus respuestas y generará una historia personalizada apropiada para tu edad (300 a 800 palabras).")

# Estado del chat
if "chat" not in st.session_state:
    st.session_state.chat = [
        {"role": "assistant", "content": "¡Hola! Soy tu agente de historias. Antes de empezar, ¿cuántos años tienes?"}
    ]
    st.session_state.etapas = ["edad", "personajes", "escenario", "género", "tono", "trama", "longitud"]
    st.session_state.respuestas = {}
    st.session_state.etapa_actual = 0
    st.session_state.modo_edicion = False
    st.session_state.historia_generada = ""
    st.session_state.historia_confirmada = False

# Mostrar historial
for msg in st.session_state.chat:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Validación
def validar_respuesta(etapa, respuesta):
    if etapa == "edad":
        try:
            edad = int(respuesta)
            return 3 <= edad <= 120
        except:
            return False

    prompt_validacion = f"""
Tu tarea es verificar si la siguiente respuesta es coherente con la pregunta:

Pregunta: ¿{etapa}?
Respuesta: {respuesta}

Responde solamente con 'Sí' si es coherente o 'No' si no lo es.
"""
    try:
        model = genai.GenerativeModel("models/gemini-2.0-flash")
        result = model.generate_content(prompt_validacion)
        evaluacion = result.text.strip().lower()
        return evaluacion.startswith("sí")
    except:
        return False

# Generación de historia con filtro por edad
def generar_historia():
    datos = st.session_state.respuestas
    edad = int(datos.get("edad", 18))
    longitud = datos.get('longitud', '').lower()
    rango_palabras = {
        "corta": "300 a 400",
        "media": "400 a 600",
        "larga": "600 a 800"
    }.get(longitud, "300 a 800")

    prompt_final = f"""
Eres un autor creativo. Escribe una historia original en español de aproximadamente {rango_palabras} palabras.

Ten en cuenta que el lector tiene {edad} años. Asegúrate de que el contenido sea apropiado para esa edad: 
usa lenguaje, temas y tono adecuados.

Género: {datos.get('género')}
Tono: {datos.get('tono')}
Personajes: {datos.get('personajes')}
Escenario: {datos.get('escenario')}
Trama: {datos.get('trama')}

No separes el texto en partes como 'Introducción, conflicto y desenlace'. Solo redacta una historia continua y coherente, si la historia generada es inadecuada para la edad del usuario, no la generes y genera un mensaje del por qué no puedes generarlo.
"""

    with st.spinner("Generando la historia..."):
        try:
            model = genai.GenerativeModel("models/gemini-2.0-flash")
            response = model.generate_content(prompt_final)
            historia = response.text
            st.session_state.historia_generada = historia
            st.session_state.chat.append({"role": "assistant", "content": historia})
            with st.chat_message("assistant"):
                st.markdown(historia)

            st.session_state.chat.append({"role": "assistant", "content": "¿Deseas modificar algo de la historia o continuar así como está?"})
            with st.chat_message("assistant"):
                st.markdown("¿Deseas modificar algo de la historia o continuar así como está?")
            st.session_state.modo_edicion = True
        except Exception as e:
            error = f"❌ Ocurrió un error al generar la historia: {e}"
            st.session_state.chat.append({"role": "assistant", "content": error})
            with st.chat_message("assistant"):
                st.error(error)

# Entrada del usuario
if prompt := st.chat_input("Escribe tu respuesta aquí..."):
    if st.session_state.modo_edicion:
        st.session_state.chat.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        if "modificar" in prompt.lower():
            prompt_validar_cambio = f"""
Historia:
{st.session_state.historia_generada}

Instrucción del usuario:
{prompt}

¿La petición indica claramente una parte específica para modificar? Responde 'Sí' o 'No'.
"""
            model = genai.GenerativeModel("models/gemini-2.0-flash")
            result = model.generate_content(prompt_validar_cambio)
            if result.text.strip().lower().startswith("sí"):
                prompt_edicion = f"""
Modifica la historia a continuación según la instrucción del usuario:

Historia original:
{st.session_state.historia_generada}

Instrucción:
{prompt}

Devuelve solo la historia modificada.
"""
                response = model.generate_content(prompt_edicion)
                historia_modificada = response.text
                st.session_state.historia_generada = historia_modificada
                st.session_state.chat.append({"role": "assistant", "content": historia_modificada})
                with st.chat_message("assistant"):
                    st.markdown(historia_modificada)
                st.session_state.chat.append({"role": "assistant", "content": "¿Deseas seguir modificando la historia o continuar así como está?"})
            else:
                advertencia = "🚫 No se entiende qué parte deseas modificar. Especifica si es el inicio, los personajes, el final, etc."
                st.session_state.chat.append({"role": "assistant", "content": advertencia})
                with st.chat_message("assistant"):
                    st.warning(advertencia)
        else:
            st.success("¡Perfecto! Historia finalizada.")
            st.session_state.chat.append({"role": "assistant", "content": "¡Perfecto! Historia finalizada."})
            st.session_state.historia_confirmada = True
            st.session_state.modo_edicion = False
    else:
        etapa = st.session_state.etapas[st.session_state.etapa_actual]

        if validar_respuesta(etapa, prompt):
            st.session_state.chat.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            st.session_state.respuestas[etapa] = prompt
            st.session_state.etapa_actual += 1

            if st.session_state.etapa_actual < len(st.session_state.etapas):
                siguiente = st.session_state.etapas[st.session_state.etapa_actual]
                preguntas = {
                    "personajes": "¿Quiénes son los personajes principales? (Me puedes mencionar sus nombres y una descripción de ellos si prefieres)",
                    "escenario": "¿Dónde y cuándo ocurre la historia? (Dime una ciudad, época o descripción para enriquecer la historia)",
                    "género": "¿Qué género prefieres? (Por ejemplo: Fantasía, Ciencia ficción, Romance, Terror, Aventura, Drama...)",
                    "tono": "¿Qué tono quieres? (Por ejemplo: Serio, Divertido, Oscuro, Inspirador, Melancólico...)",
                    "trama": "¿Qué elementos importantes quieres en la trama? (Por ejemplo: Conflictos, giros inesperados...)",
                    "longitud": "¿Qué longitud prefieres? (Corta: 300-400, Media: 400-600, Larga: 600-800 palabras)"
                }
                mensaje = preguntas.get(siguiente, "Gracias. Ya tengo todo para generar tu historia.")
                st.session_state.chat.append({"role": "assistant", "content": mensaje})
                with st.chat_message("assistant"):
                    st.markdown(mensaje)
            else:
                generar_historia()
        else:
            st.warning("🚫 La respuesta no parece coherente con la pregunta. Intenta de nuevo.")

st.markdown("---")
st.caption("Desarrollado con ❤️ usando Streamlit y Gemini")
