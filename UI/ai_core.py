import os
import requests
from deep_translator import GoogleTranslator

MODEL_URL = os.getenv(
    "MODEL_URL",
    "https://huggingface.co/QuantFactory/falcon-7b-instruct-GGUF/resolve/main/falcon-7b-instruct.Q4_0.gguf"
)
MODEL_DIR = os.getenv("MODEL_DIR", os.path.join(os.path.dirname(__file__), "models"))
MODEL_FILENAME = os.getenv("MODEL_FILENAME", "falcon-7b-instruct.Q4_0.gguf")
MODEL_PATH = os.path.join(MODEL_DIR, MODEL_FILENAME)

def ensure_model_exists():
    os.makedirs(MODEL_DIR, exist_ok=True)
    if not os.path.exists(MODEL_PATH):
        print("⬇️ Завантаження моделі з Hugging Face...")
        with requests.get(MODEL_URL, stream=True) as r:
            r.raise_for_status()
            with open(MODEL_PATH, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        print("✅ Модель успішно завантажена.")
    else:
        print("✅ Модель вже існує локально.")

# ↓ Ініціалізується лише при першому виклику
llm = None

# Абсолютний шлях до файлу моделі (.gguf)
current_dir = os.path.dirname(os.path.abspath(__file__))
model_path = os.path.join(current_dir, MODEL_DIR, MODEL_FILENAME)

# lazy init
_llm = None

def translate(text, src_lang, dest_lang):
    try:
        return GoogleTranslator(source=src_lang, target=dest_lang).translate(text)
    except Exception as e:
        return f"Translation Error: {str(e)}"

def ask_ai(prompt):
    global llm
    try:
        ensure_model_exists()
        translated_prompt = translate(prompt, 'uk', 'en')
        system_prompt = (
            "You are a helpful AI assistant. Provide clear answers and code examples if needed. "
            "Respond in the user's language when possible."
        )
        full_prompt = f"{system_prompt}\n\nUser: {translated_prompt}\nAI:"

        # 🔄 Перекладаємо запит на англійську
        translated_prompt = translate(prompt, 'uk', 'en')

        # 🧠 Ініціалізуємо модель (тільки один раз)
        if llm is None:
            from llama_cpp import Llama
            llm = Llama(model_path=MODEL_PATH, n_ctx=2048)

        response = llm(full_prompt, max_tokens=100, temperature=0.3, top_p=0.7, stop=["User:", "AI:"])

        text = response.get("choices", [{}])[0].get("text", "")
        if not text.strip():
            return "AI не відповів."

        return translate(text, 'en', 'uk').strip()

    except Exception as e:
        return f"Error: {str(e)}"
