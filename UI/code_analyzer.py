from eric7.UI.ai_core import ask_ai


def analyze_code(code):
    # Додаємо інструкцію для AI
    prompt = f"Find bugs and suggest improvements for the following Python code:\n```python\n{code}\n```"
    response = ask_ai(prompt)
    return response

def send_to_ai(self):
    # Отримуємо код з текстового поля
    prompt = self.textEdit.toPlainText()
    # Викликаємо функцію аналізу
    response = analyze_code(prompt)
    # Додаємо відповідь до текстового поля
    self.textEdit.append(f"\nAI Analysis:\n{response}")
