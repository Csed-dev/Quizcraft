from flask import flash
from google.oauth2 import service_account
from googleapiclient.discovery import build
from pdf_processing import extract_page_text
from api_interaction import validate_questions_and_format
import PyPDF2
import json

def quick_text_extract_from_pdf(pdf_path, pages=None):
    with open(pdf_path, 'rb') as pdf_file:
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        total_pages = len(pdf_reader.pages)

        extracted_texts = {}

        if not pages:  # Wenn keine Seiten angegeben wurden, extrahiere Text von allen Seiten
            pages_to_process = range(1, total_pages + 1)
        else:
            pages_to_process = []
            for part in pages.split(','):
                part = part.strip()
                if '-' in part:
                    start, end = map(int, part.split('-'))
                    pages_to_process.extend(range(start, end + 1))
                else:
                    pages_to_process.append(int(part))

        for page in pages_to_process:
            text = extract_page_text(pdf_path, page)
            extracted_texts[page] = text

        return extracted_texts

def quick_generate_questions(model, pdf_text):
    
    prompt = (
        "Aufgabe:\n"
        "Erstelle eine Liste von spezifischen, inhaltlich präzisen Fragen, die direkt aus dem folgenden Text abgeleitet werden können. "
        "Die Fragen sollen ausschließlich auf die Inhalte des Textes bezogen sein und keine externen Informationen beinhalten. Das heißt, dass die Fragen von dem übergegebenen Text beantwortet werden können."
        "Jede Frage soll geeignet sein, um das Verständnis von Informatik-Studierenden zu prüfen und relevant für die Vorlesung sein.\n\n"
        
        "Anleitung:\n"
        "1. Lies den bereitgestellten Text aufmerksam durch.\n"
        "2. Generiere pro Textabschnitt sinnvolle Fragen.\n"
        "3. Stelle sicher, dass jede Frage aus dem Text beantwortbar ist.\n"
        "4. Formatiere die Ausgabe als JSON-Liste im folgenden Format:\n"
        "[\n"
        "  {\n"
        '    "frage": "<<Frage>>"\n'
        "  },\n"
        "  {\n"
        '    "frage": "<<Frage>>"\n'
        "  }\n"
        "]\n"
        
        "Beispiel:\n"
        "[\n"
        "  {\n"
        '    "frage": "Was ist die Definition eines Algorithmus?"\n'
        "  },\n"
        "  {\n"
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
    return validate_questions_and_format(response.text, model)

def quick_correct_json_format_for_questions(text, model):
    correction_prompt = (
        f"Der folgende Text entspricht nicht dem gewünschten JSON-Format. "
        f"Er muss im JSON-Format strukturiert sein, darf jedoch nicht mit '```json\n' oder anderen Zeichen beginnen. "
        f"Der Text muss ausschließlich mit '[\n' beginnen und korrekt formatiert sein. "
        f"Bitte formatiere diesen Text exakt im folgenden JSON-Format, nach den oben genannten bedingungen:\n\n"
        f"Falls die Frage leer ist, also null, dann fülle es mit 'undefined'. Hier ist der fehlerhafte Text:\n\n"
        f"{text}\n\n"
        "[\n"
        "   {\n"
        f'      "frage": "<<Generierter Frageninhalt>>",\n'
        "   }\n"
        "]"
    )

    correction_response = model.generate_content(correction_prompt)
    return correction_response.text

def quick_generate_google_form(questions_json, pages=None, module_name=None, model=None, pdf_text=None):
    SERVICE_ACCOUNT_FILE = 'C:\\Codes\\QuizCraft\\gen-lang-client-0625082558-a958e1c7fe1e.json'
    SCOPES = ['https://www.googleapis.com/auth/forms.body', 'https://www.googleapis.com/auth/drive']

    # Service Account Credentials laden
    creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)

    # Google Forms API Service erstellen
    service = build('forms', 'v1', credentials=creds)
    drive_service = build('drive', 'v3', credentials=creds)

    # Wiederholungslogik für JSONDecodeError
    try:
        # Versuche, die JSON-Fragen zu laden
        questions = json.loads(questions_json)
    except json.JSONDecodeError as e:
        flash("Fragen sind nicht im korrekten JSON-Format, wird neu generiert.", "warning")
        print(f"JSONDecodeError: {e}")

        # Versuche, die Fragen erneut zu generieren, falls das JSON fehlerhaft ist
        if model and pdf_text:
            questions_json = quick_generate_questions(model, pdf_text)
            try:
                questions = json.loads(questions_json)
            except json.JSONDecodeError as e:
                flash("Konnte die Fragen nach der erneuten Generierung nicht im JSON-Format laden.", "danger")
                print(f"Fehler nach erneuter Generierung: {e}")
                return None
        else:
            flash("Keine weiteren Daten verfügbar, um die Fragen erneut zu generieren.", "danger")
            return None

    # Modulname verwenden oder Platzhalter setzen
    form_title = f"{module_name if module_name else 'Generierter'} Quiz {'für die S. ' + pages if pages else ''}"
    form = {
        "info": {
            "title": form_title,
            "documentTitle": form_title,
        }
    }
    result = service.forms().create(body=form).execute()
    form_id = result['formId']
    print(f'Formular erstellt: https://docs.google.com/forms/d/{form_id}/edit')

    # Fragen aus JSON-Format hinzufügen
    requests = []
    for question in questions:
        requests.append({
            "createItem": {
                "item": {
                    "title": question['frage'],
                    "questionItem": {
                        "question": {
                            "required": False,
                            "textQuestion": {
                                "paragraph": True  # Falls längere Antworten erwartet werden, auf True setzen
                            }
                        }
                    }
                },
                "location": {
                    "index": 0  # Position im Formular
                }
            }
        })

    # Fragen zum Formular hinzufügen
    service.forms().batchUpdate(formId=form_id, body={"requests": requests}).execute()

    # Formular-URL zurückgeben
    form_url = f"https://docs.google.com/forms/d/{form_id}/edit"
    return form_url
