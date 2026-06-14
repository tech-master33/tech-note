import requests
import json

def get_ai_response(prompt, settings):
    provider = settings.get('ai_provider', 'ollama').lower()
    endpoint = settings.get('ai_endpoint', 'http://localhost:11434/v1')
    model = settings.get('ai_model', 'llama3')
    api_key = settings.get('ai_api_key', '')
    try:
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": "You are Dora, a helpful personal assistant. Keep responses concise and suitable for text-to-speech."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7
        }
        url = f"{endpoint.rstrip('/')}/chat/completions"
        if provider == 'ollama' and '/v1' not in url:
            url = f"{endpoint.rstrip('/')}/v1/chat/completions"
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        return data['choices'][0]['message']['content'].strip()
    except Exception as e:
        return f"AI error: {str(e)}"

def chat_with_ai(assistant, command):
    assistant.speak("Thinking...")
    response = get_ai_response(command, assistant.settings)
    assistant.speak(response)
