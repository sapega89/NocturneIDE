import os
from llama_cpp import Llama
from deep_translator import GoogleTranslator  # pip install deep-translator

# Абсолютний шлях до файлу моделі (.gguf)
current_dir = os.path.dirname(os.path.abspath(__file__))
model_path = os.path.join(current_dir, 'models', 'falcon-7b-instruct.Q4_0.gguf')

# Завантажуємо модель через llama-cpp-python
llm = Llama(model_path=model_path, n_ctx=2048)

# Ініціалізуємо перекладач
translator = GoogleTranslator()

def translate(text, src_lang, dest_lang):
    try:
        return GoogleTranslator(source=src_lang, target=dest_lang).translate(text)
    except Exception as e:
        return f"Translation Error: {str(e)}"

def ask_ai(prompt):
    try:
        # 🔄 Перекладаємо запит на англійську
        translated_prompt = translate(prompt, 'uk', 'en')

        # ⚡ Додаємо системний промпт
        system_prompt = (
            "You are a helpful AI assistant. Provide clear answers and code examples if needed. "
            "Respond in the user's language when possible."
        )
        full_prompt = f"{system_prompt}\n\nUser: {translated_prompt}\nAI:"

        # ⚡ Виклик AI
        response = llm(full_prompt, max_tokens=100, temperature=0.3, top_p=0.7, stop=["User:", "AI:"])

        # 🔄 Переклад відповіді назад на українську
        translated_response = translate(response["choices"][0]["text"], 'en', 'uk')

        return translated_response.strip()

    except Exception as e:
        return f"Error: {str(e)}"

# 🟢 Тест
if __name__ == "__main__":
    user_input = input("Введіть запит: ")
    print("AI:", ask_ai(user_input))
