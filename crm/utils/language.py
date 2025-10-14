from langdetect import detect
from langcodes import Language

def detect_language(text: str) -> str:
    """
    Detect language
    Args:
        text(str) : text input for lanauge detection
    Returns:
        (str)
    """
    lang_code = detect(text)
    lang_name = Language.get(lang_code).display_name()
    return lang_code, lang_name

def is_same_language(response: str, expected_lang_code: str) -> bool:
    """
    Check either the language is exected or not
    Args:
        response(str): text to check the language 
        expected_lang_code(str): expected lanague code
    Returns:
        (bool)
    """
    detected_lang = detect(response)
    return detected_lang == expected_lang_code

def translate_to_language(text: str, target_lang: str) -> str:
    translation_prompt = f"Translate the following text to {target_lang}:\n\n{text}"
    return

