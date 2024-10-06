import os
import json
import google.generativeai as genai
from app_database import create_module_tables, Session, get_total_pages_for_module
from dotenv import load_dotenv

load_dotenv()

def generate_and_save_questions_for_page(module, page, model):
    # Hole den Text für die Seite
    pdf_text = retrieve_page_text(module, page)

    # Generiere Fragen mit Hilfe des LLM
    questions_json = generate_questions(model, pdf_text)

    # Debugging-Ausgabe: Zeige die generierten JSON-Daten an
    # print("Generated Questions JSON:", questions_json)

    # Speichere die Fragen in der Datenbank
    save_questions_to_db(module, questions_json)

# Konfigurieren der Generative AI API
def configure_genai_api():
    GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY_QUIZCRAFT')
    if not GOOGLE_API_KEY:
        raise ValueError("Der API-Schlüssel ist nicht gesetzt. Bitte setzen Sie die Umgebungsvariable 'GOOGLE_API_KEY_QUIZCRAFT'.")
    genai.configure(api_key=GOOGLE_API_KEY)
    return genai.GenerativeModel('gemini-1.5-flash')

# Generiere Fragen basierend auf dem PDF-Text
def generate_questions(model, pdf_text):
    prompt = (
        "Aufgabe:\n"
        "Erstelle eine Liste von präzisen, inhaltlich spezifischen Fragen, die direkt aus dem folgenden Text "
    "ableitbar sind. Jede Frage muss sich ausschließlich auf den Textinhalt beziehen und darf keine externen "
    "Informationen voraussetzen. Die Fragen müssen aus dem Text beantwortbar sein, ohne dass zusätzliche "
    "Kenntnisse erforderlich sind.\n\n"
    
    "Die Fragen sollen das Verständnis von Informatik-Studierenden prüfen und thematisch relevant zur Vorlesung sein. "
    "Jede Frage muss eindeutig der Seite zugeordnet werden, auf der die entsprechenden Informationen im Text stehen.\n\n"
    
    "Vermeide Fragen wie: 'Welche Informationen stehen auf Seite X?' oder 'Welches Datum stand auf der Folie?'. "
    "Diese Fragen sind nicht sinnvoll, da sie nicht von einer Person ohne direkten Textzugriff beantwortet werden können. "
    "Stattdessen soll die Frage den Inhalt selbst betreffen, z.B.: 'Was ist Data Science?', nicht: 'Auf welcher Folie wird Data Science erklärt?'.\n\n"
        
        "Anleitung:\n"
        "1. Lies den bereitgestellten Text aufmerksam durch.\n"
        "2. Extrahiere die Seitenzahl aus dem Text. Die Seitenzahl ist in der Struktur [Seite: Seitenzahl] angegeben.\n"
        "3. Generiere pro Textabschnitt sinnvolle Fragen.\n"
        "4. Stelle sicher, dass jede Frage aus dem Text beantwortbar ist.\n"
        "5. Formatiere die Ausgabe als JSON-Liste im folgenden Format:\n"
        "[\n"
        "  {\n"
        '    "seite": "<<Seitenzahl>>",\n'
        '    "frage": "<<Frage>>"\n'
        "  },\n"
        "  {\n"
        '    "seite": "<<Seitenzahl>>",\n'
        '    "frage": "<<Frage>>"\n'
        "  }\n"
        "]\n"
        
        "Beispiel:\n"
        "[\n"
        "  {\n"
        '    "seite": "2",\n'
        '    "frage": "Was ist die Definition eines Algorithmus?"\n'
        "  },\n"
        "  {\n"
        '    "seite": "2",\n'
        '    "frage": "Welche Rolle spielt die Datenstruktur in der Informatik?"\n'
        "  }\n"
        "]\n"
        
        "Wichtig:\n"
        "- Halte dich genau an das angegebene JSON-Format.\n"
        "- Füge keine zusätzlichen Informationen oder Erläuterungen hinzu.\n"
        "- Die Ausgabe soll nur die JSON-Liste der Fragen enthalten.\n\n"
        
        "Text:\n"
        f"{pdf_text}\n"
    )


    
    response = model.generate_content(prompt)
    
    try:
        # Validierung und Rückgabe des generierten JSON
        json.loads(response.text)
        return response.text
    except json.JSONDecodeError:
        # Falls das generierte JSON-Format falsch ist, korrigieren wir es
        corrected_text = correct_json_format(response.text, model)
        return corrected_text

# Korrigiere das JSON-Format, falls es ungültig ist
def correct_json_format(text, model):
    correction_prompt = (
        "Aufgabe:\n"
        "Der folgende Text entspricht nicht dem gewünschten JSON-Format.\n\n"
        
        "Anleitung:\n"
        "1. Analysiere den bereitgestellten Text.\n"
        "2. Identifiziere die enthaltenen Fragen und zugehörigen Seitenzahlen.\n"
        "3. Formatiere die Informationen exakt im angegebenen JSON-Format.\n"
        "   - Die Ausgabe muss mit '[\n' beginnen.\n"
        "   - Verwende keine zusätzlichen Zeichen wie '```json' oder Ähnliches.\n"
        "4. Stelle sicher, dass jedes Objekt die Schlüssel \"seite\" und \"frage\" enthält.\n"
        "5. Falls ein Wert fehlt oder unvollständig ist, setze den Wert auf \"Fehlerhafte Generierung\".\n\n"
        
        "Beispiel für das gewünschte Format:\n"
        "[\n"
        "  {\n"
        '    "seite": "3",\n'
        '    "frage": "Was versteht man unter Algorithmen?"\n'
        "  },\n"
        "  {\n"
        '    "seite": "3",\n'
        '    "frage": "Wie werden Datenstrukturen klassifiziert?"\n'
        "  }\n"
        "]\n\n"
        
        "Fehlerhafter Text:\n"
        f"{text}\n\n"
        
        "Wichtig:\n"
        "- Halte dich genau an das angegebene JSON-Format.\n"
        "- Füge keine zusätzlichen Informationen oder Erläuterungen hinzu. Verändere nichts am eigentlichen Inhalt.\n"
        "- Die Ausgabe soll nur die korrekt formatierte JSON-Liste enthalten.\n"
        "- Überspringe jeglichen erläuternden Text oder Kommentare.\n\n"
        
        "Bitte formatiere den Text jetzt entsprechend."
    )

    correction_response = model.generate_content(correction_prompt)
    return correction_response.text

# Funktion zum Speichern der Fragen in der Datenbank
def save_questions_to_db(module_name, questions_json):
    session = Session()  # Neue Session erstellen
    _, QuestionTable = create_module_tables(module_name)  # Erstelle dynamisch die passende Tabelle
    
    questions = json.loads(questions_json)  # JSON-Daten in Python-Objekt konvertieren
    
    for question_data in questions:
        frage = question_data.get("frage", "undefined")
        seite = question_data.get("seite", "undefined")
        
        # Erstellen eines neuen Eintrags in der Datenbank
        question = QuestionTable(
            frage=frage,
            seite=seite
        )
        
        session.add(question)

    session.commit()  # Änderungen speichern
    session.close()  # Session schließen

    

# Text von einer bestimmten Seite aus der Datenbank abrufen
def retrieve_page_text(module_name, page):
    session = Session()  # Neue Session erstellen
    TextTable, _ = create_module_tables(module_name)  # Erstelle die entsprechende Text-Tabelle
    page_entry = session.query(TextTable).filter_by(page=page).first()  # Abfrage der Seite
    
    session.close()  # Session schließen
    return page_entry.text if page_entry else None