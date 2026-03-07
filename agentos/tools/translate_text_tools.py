from deep_translator import GoogleTranslator

def translate_text(text, target_language):
    translated = GoogleTranslator(source='auto', target=target_language).translate(text)
    return {"status": "success", "translated_text": translated}
