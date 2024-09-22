import io
import os
import base64
import qrcode
from flask import flash, session
from sqlalchemy.orm import Session
from app_database import create_module_tables, parse_pages, Session
import googleapiclient.discovery
from google.oauth2 import service_account
from googleapiclient.discovery import build

GOOGLE_CREDENTIALS_FILE = os.getenv('GOOGLE_CREDENTIALS_FILE', 'C:\\Codes\\QuizCraft\\gen-lang-client-0625082558-a958e1c7fe1e.json')
creds = service_account.Credentials.from_service_account_file(GOOGLE_CREDENTIALS_FILE)

def get_questions_by_ids(module_name, ids_str):
    # Erstellen einer neuen Session
    session_db = Session()
    _, QuestionTable = create_module_tables(module_name)
    ids_list = parse_pages(ids_str)  # Verwenden der parse_pages-Funktion zum Parsen der IDs

    questions = session_db.query(QuestionTable).filter(QuestionTable.id.in_(ids_list)).all()
    session_db.close()

    question_list = [{"frage": q.frage, "seite": q.seite} for q in questions]
    return question_list

def get_questions_from_db(module_name, pages_str):
    session = Session()
    _, QuestionTable = create_module_tables(module_name)
    page_numbers = parse_pages(pages_str)

    questions = session.query(QuestionTable).filter(QuestionTable.seite.in_(page_numbers)).all()
    session.close()

    question_list = [{"frage": q.frage, "seite": q.seite} for q in questions]
    return question_list


def generate_google_form(name, pages, ids, emails, questions_list):
    try:
        creds = service_account.Credentials.from_service_account_file(GOOGLE_CREDENTIALS_FILE)
        service = googleapiclient.discovery.build('forms', 'v1', credentials=creds)

        # Formular-Titel erstellen
        form_title_parts = [name if name else 'Generierter Quiz']
        if pages:
            form_title_parts.append(f"S. {pages}")
        if ids:
            form_title_parts.append(f"IDs: {ids}")
        form_title = ' - '.join(form_title_parts)

        form = {
            "info": {
                "title": form_title,
                "documentTitle": form_title,
            }
        }

        # Google Form erstellen
        result = service.forms().create(body=form).execute()
        form_id = result['formId']
        form_url = f"https://docs.google.com/forms/d/{form_id}/edit"  # Edit-Link verwenden

        # Fragen hinzufügen
        requests = []
        for question in questions_list:
            requests.append({
                "createItem": {
                    "item": {
                        "title": question["frage"],
                        "questionItem": {
                            "question": {
                                "required": False,
                                "textQuestion": {
                                    "paragraph": False
                                }
                            }
                        }
                    },
                    "location": {
                        "index": 0
                    }
                }
            })

        # Batch-Anfrage zum Hinzufügen der Fragen
        service.forms().batchUpdate(formId=form_id, body={"requests": requests}).execute()

        # Berechtigungen hinzufügen
        add_permissions(form_id, emails, creds)

        # QR-Code generieren
        qr_code_bytes = generate_qr_code(form_url)

        if qr_code_bytes:
            # QR-Code binäre Daten Base64-kodieren
            qr_code_base64 = base64.b64encode(qr_code_bytes).decode('utf-8')
            # QR-Code in der Session speichern
            session['qr_code'] = qr_code_base64

        return form_url, qr_code_base64
    except Exception as e:
        print(f"Fehler bei der Google Form-Erstellung: {e}")
        return None, None


def add_permissions(form_id, selected_emails, creds):
    try:
        drive_service = build('drive', 'v3', credentials=creds)
        # Nutze die form_id direkt aus der API-Antwort, statt sie aus der URL zu extrahieren
        for email in selected_emails:
            print(f"Füge Berechtigung hinzu für: {email}")
            permission = drive_service.permissions().create(
                fileId=form_id,  # Verwende die form_id direkt
                body={
                    'type': 'user',
                    'role': 'writer',
                    'emailAddress': email
                },
                fields='id'
            ).execute()
            print(f"Berechtigung hinzugefügt: {permission}")
        
        print(f"Berechtigungen erfolgreich hinzugefügt für: {selected_emails}")
    except Exception as e:
        print(f"Fehler beim Hinzufügen von Berechtigungen: {e}")

def generate_qr_code(google_form_url):
    if google_form_url is None:
        flash("Fehler beim Erstellen des Google Formulars. Keine gültige URL erhalten.", "danger")
        return None
    
    # Die URL für den QR-Code soll die "viewform"-Version verwenden
    view_form_url = google_form_url.replace('/edit', '/viewform')

    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=2)
    qr.add_data(view_form_url)
    qr.make(fit=True)
    img = qr.make_image(fill='black', back_color='white')

    # QR-Code als Datei speichern und zum Herunterladen bereitstellen
    buffer = io.BytesIO()
    img.save(buffer, 'PNG')
    buffer.seek(0)
    return buffer.getvalue()
