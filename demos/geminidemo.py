import vertexai
from vertexai.generative_models import GenerativeModel
import env

PROJECT_ID = env.PROJECT_ID
REGION = env.REGION

vertexai.init(project=PROJECT_ID, location=REGION)

# model = GenerativeModel("gemini-2.0-flash-001")
model = GenerativeModel(model_name='gemini-2.5-flash-lite',
            system_instruction='Eres un asistente útil que responde en español y le gusta hablar. Tu repuestas son sin simbolos, debes responder de forma textual para una conversacion, no listas, ni parentesis, ni otro simbolo, solo palabras, signos de puntuacion y conectores.',)
# chatSession = model.start_chat()
response = model.generate_content(
    "Saluda!"
)
# prompt = 'Dame un chiste divertido en español.'
# # Generar respuesta en streaming
# chunks = chatSession.send_message(prompt, stream=False)

print(response.text)
