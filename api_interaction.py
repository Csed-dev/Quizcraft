import os
import json
import textwrap
import google.generativeai as genai

def configure_genai_api():
    GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY_QUIZCRAFT')
    if not GOOGLE_API_KEY:
        raise ValueError("Der API-Schlüssel ist nicht gesetzt. Bitte setzen Sie die Umgebungsvariable 'GOOGLE_API_KEY_QUIZCRAFT'.")
    genai.configure(api_key=GOOGLE_API_KEY)
    return genai.GenerativeModel('gemini-1.5-flash')

def extract_chapter_and_topic(model, pdf_text):
    prompt = (
        f"Analysiere den folgenden Text und extrahiere das übergeordnete Kapitel und das Hauptthema. "
        f"Das Kapitel sollte den gesamten Abschnitt repräsentieren, während das Thema das spezifische Thema innerhalb des Kapitels beschreibt. "
        f"Füge keine weiteren Zeichen und Informationen hinzu. Gib die Ergebnisse im folgenden Format zurück und in keinem anderen:\n"
        "[\n"
        "   {\n"
        f'      "kapitel": "<<Erkanntes übergreifendes Kapitel>>",\n'
        f'      "thema": "<<Erkanntes spezifisches Thema>>"\n'
        "   }\n"
        "]\n"
        f"Der Text:\n\n{pdf_text}\n\n"
    )
    response = model.generate_content(prompt)
    
    try:
        result = json.loads(response.text)
        kapitel = result[0]["kapitel"]
        thema = result[0]["thema"]
        return kapitel, thema
    except (json.JSONDecodeError, KeyError):
        # Fehlerbehandlung falls das JSON-Parsing fehlschlägt
        corrected_text = correct_json_format_for_chapter_and_topic(response.text, model)
        try:
            result = json.loads(corrected_text)
            kapitel = result[0]["kapitel"]
            thema = result[0]["thema"]
            return kapitel, thema
        except (json.JSONDecodeError, KeyError):
            return "Allgemeines Kapitel", "Allgemeines Thema"

def correct_json_format_for_chapter_and_topic(text, model):
    correction_prompt = (
        f"Der folgende Text entspricht nicht dem gewünschten JSON-Format. "
        f"Er muss im JSON-Format strukturiert sein, darf jedoch nicht mit '```json\n' oder anderen Zeichen beginnen. "
        f"Der Text muss ausschließlich mit '[\n' beginnen und korrekt formatiert sein. "
        f"Hier ist der fehlerhafte Text:\n\n"
        f"{text}\n\n"
        f"Bitte formatiere diesen Text exakt im folgenden JSON-Format, "
        f"ohne zusätzliche Felder wie 'frage' oder 'antwort':\n\n"
        "[\n"
        "   {\n"
        f'      "kapitel": "<<Kapitel>>",\n'
        f'      "thema": "<<Thema>>"\n'
        "   }\n"
        "]"
    )

    correction_response = model.generate_content(correction_prompt)
    return correction_response.text

def generate_questions(model, pdf_text):
    kapitel, thema = extract_chapter_and_topic(model, pdf_text)
    
    prompt = (
        f"Erstelle spezifische, inhaltlich präzise Fragen, die direkt aus dem folgenden Text "
        f"abgeleitet werden können. Die Fragen sollen sich ausschließlich auf die Inhalte des "
        f"Textes beziehen und dürfen keine allgemeinen oder externen Informationen beinhalten. "
        f"Stelle sicher, dass jede Frage aus dem Text beantwortet werden kann und relevant für "
        f"die Vorlesung ist. "
        f"Es ist sehr wichtig, sich an das folgende Format zu halten:"
        "[\n"
        "   {\n"
        f'      "kapitel": "{kapitel}",\n'
        f'      "thema": "{thema}",\n'
        f'      "frage": "<<Generierte Frage>>",\n'
        f'      "antwort": "<<Extrahierte Antwort>>",\n'
        f'      "seiten": "<<Extrahierte Seite>>"\n'
        "   }\n"
        "]\n"
        f"Füge keine weiteren Informationen hinzu."
        f"Der Text:\n\n{pdf_text}\n\n"
    )
    
    response = model.generate_content(prompt)
    return validate_questions_and_format(response.text, model)

def validate_questions_and_format(text, model):
    validation_prompt = (
        f"Überprüfe die folgenden Fragen darauf, ob sie sinnvoll und direkt aus dem Text ableitbar sind. "
        f"Eine Frage gilt als nicht sinnvoll, wenn sie eine der folgenden Bedingungen erfüllt:\n"
        f"1. Die Frage kann nicht eindeutig und vollständig aus dem Text beantwortet werden.\n"
        f"2. Die Frage basiert auf einer fehlerhaften Interpretation oder einem Missverständnis des Textes.\n"
        f"3. Die Frage trägt nicht zum Lernfortschritt der Zielgruppe bei.\n"
        f"4. Die Frage ist unklar formuliert oder enthält logische Fehler.\n"
        f"Zusätzlich zu diesen Bedingungen kannst du selbst bestimmen, ob eine Frage sinnvoll ist, basierend auf deinem Verständnis des Themas. "
        f"Verbessere die Fragen, die als nicht sinnvoll gelten, oder entferne sie, falls sie nicht sinnvoll angepasst werden können.\n\n"
        f"Hier sind die generierten Fragen:\n\n"
        f"{text}"
    )

    validation_response = model.generate_content(validation_prompt)
    validated_text = validation_response.text

    try:
        json.loads(validated_text)
        return validated_text
    except json.JSONDecodeError:
        correction_response = correct_json_format_for_questions(validated_text, model)
        return correction_response

def correct_json_format_for_questions(text, model):
    correction_prompt = (
        f"Der folgende Text entspricht nicht dem gewünschten JSON-Format. "
        f"Er muss im JSON-Format strukturiert sein, darf jedoch nicht mit '```json\n' oder anderen Zeichen beginnen. "
        f"Der Text muss ausschließlich mit '[\n' beginnen und korrekt formatiert sein. "
        f"Falls eins der 4 Meta-Daten, also Kapitel, Thema, Frage und Antwort leer ist, also null, dann fülle es mit 'undefined'. Hier ist der fehlerhafte Text:\n\n"
        f"{text}\n\n"
        f"Bitte formatiere diesen Text exakt im folgenden JSON-Format:\n\n"
        "[\n"
        "   {\n"
        f'      "kapitel": "<<Kapitel>>",\n'
        f'      "thema": "<<Thema>>",\n'
        f'      "frage": "<<Frage>>",\n'
        f'      "antwort": "<<Antwort>>",\n'
        "   }\n"
        "]"
    )

    correction_response = model.generate_content(correction_prompt)
    return correction_response.text