import os
import io
import base64
import json
import PyPDF2
from flask_wtf import CSRFProtect
from werkzeug.utils import secure_filename
from flask import Flask, render_template, request, redirect, session, url_for, flash, send_file, jsonify
from pdf_processing import extract_pages, validate_pages
from api_interaction import configure_genai_api
from create_google_form import get_questions_by_ids, generate_google_form, generate_qr_code, get_questions_from_db
from app_database import get_extracted_texts, delete_text_from_db, get_extracted_questions, delete_question_from_db, Session, create_module_tables, get_total_pages_for_module, get_existing_pages
from create_questions import configure_genai_api, generate_and_save_questions_for_page
from quick_form import quick_generate_google_form, quick_generate_questions, quick_text_extract_from_pdf
from googleapiclient.discovery import build, service_account
from forms import UploadForm, QuestionForm, QuickForm, ShowTextForm, GoogleFormCreationForm, ShowQuestionsForm

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf'}
EMAIL_STORAGE = 'email_give_edit_permission.json'

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', os.urandom(24).hex())
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

csrf = CSRFProtect(app)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def load_emails():
    if os.path.exists(EMAIL_STORAGE):
        with open(EMAIL_STORAGE, 'r') as file:
            emails = json.load(file)
        return {email['first_name']: email['email'] for email in emails}
    return {}

@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    form = UploadForm()
    if form.validate_on_submit():
        file = form.pdf_file.data
        module = form.module.data
        changes = form.changes.data
        pages = form.pages.data if form.pages.data else None

        # Überprüfen, ob Änderungen angegeben wurden, aber keine Seiten
        if changes and not pages:
            flash('Bitte geben Sie die Seitenzahlen an, wenn es Änderungen gab.', 'danger')
            return redirect(url_for('upload_file'))

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(pdf_path)

            extracted_texts = extract_pages(module, pdf_path, pages)
            flash('PDF erfolgreich hochgeladen und verarbeitet!', 'success')
            return redirect(url_for('upload_file'))

    return render_template('upload.html', form=form)

@app.route('/create_question', methods=['GET', 'POST'])
def create_question():
    form = QuestionForm()
    
    # Überprüfen, ob Seiten aus der Session übergeben wurden (z.B. aus `show_texts`)
    session_pages = session.get('selected_pages')
    module_from_session = session.get('module')

    # Fragen nur erstellen, wenn das Formular validiert und abgeschickt wurde
    if form.validate_on_submit():
        # Seiten aus dem Formular verwenden
        module = form.module.data if form.module.data else module_from_session
        pages = form.pages.data if form.pages.data else ','.join(session_pages)

        # Konfigurieren des generativen AI-Modells
        model = configure_genai_api()

        # Iteriere über jede angegebene Seite und generiere Fragen
        for part in pages.split(','):
            part = part.strip()
            if '-' in part:
                start, end = map(int, part.split('-'))
                for page in range(start, end + 1):
                    generate_and_save_questions_for_page(module, page, model)
            else:
                page = int(part)
                generate_and_save_questions_for_page(module, page, model)

        flash('Fragen erfolgreich generiert und gespeichert!', 'success')
        
        # Nach erfolgreicher Nutzung die Session-Einträge löschen
        session.pop('selected_pages', None)
        session.pop('module', None)

        return redirect(url_for('create_question'))

    # Fülle das Formular mit Daten aus der Session, falls vorhanden
    if session_pages and not form.pages.data:
        form.pages.data = ','.join(session_pages)
    if module_from_session and not form.module.data:
        form.module.data = module_from_session

    # Keine Fragen generieren, nur Formular anzeigen
    return render_template('create_question.html', form=form)

@app.route('/', methods=['GET', 'POST'])
def quick_form():
    form = QuickForm()

    # Vornamen und entsprechende E-Mails laden
    name_to_email_map = load_emails()
    form.first_name.choices = [(name, name) for name in name_to_email_map.keys()]

    if form.validate_on_submit():
        # Ausgewählte Vornamen verarbeiten und entsprechende E-Mails zur Freigabe auswählen
        selected_first_names = form.first_name.data
        selected_emails = [name_to_email_map[name] for name in selected_first_names]
        
        # Speichern der eingegebenen Daten in der Session
        session['module_name'] = form.module_name.data
        
        file = form.pdf_file.data
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(pdf_path)
            session['pdf_file_path'] = pdf_path

            # Überprüfe, ob die Datei leer ist
            if os.path.getsize(pdf_path) == 0:
                flash('Die hochgeladene Datei ist leer und kann nicht verarbeitet werden.', 'danger')
                return redirect(url_for('quick_form'))

        session['pages'] = form.pages.data

        pages = form.pages.data if form.pages.data else None
        module_name = form.module_name.data if form.module_name.data else "Generierter"

        if pdf_path:
            # Ermittele die Gesamtseitenzahl des PDFs
            try:
                with open(pdf_path, 'rb') as pdf_file:
                    pdf_reader = PyPDF2.PdfReader(pdf_file)
                    total_pages = len(pdf_reader.pages)  # Die Gesamtseitenzahl des PDFs
            except PyPDF2.errors.EmptyFileError:
                flash('Die hochgeladene Datei ist leer und kann nicht verarbeitet werden.', 'danger')
                return redirect(url_for('quick_form'))
            except Exception as e:
                print(f"Fehler beim Ermitteln der Gesamtseitenzahl: {e}")
                flash('Fehler beim Ermitteln der Gesamtseitenzahl des PDFs.', 'danger')
                return redirect(url_for('quick_form'))

            if pages and not validate_pages(pages, total_pages):
                flash('Ungültige Seitenangaben.', 'danger')
                return redirect(url_for('quick_form'))

            # Text aus den angegebenen Seiten extrahieren
            pdf_text = quick_text_extract_from_pdf(pdf_path, pages)

            # Generative AI Model konfigurieren und Fragen generieren
            model = configure_genai_api()
            try:
                questions_json = quick_generate_questions(model, pdf_text)
            except json.JSONDecodeError:
                flash('Ausgabe von Gemini nicht im korrektem JSON-Format.\nBitte versuchen Sie es erneut.', 'danger')
                return redirect(url_for('quick_form'))

            # Google API-Anmeldedaten laden
            SERVICE_ACCOUNT_FILE = 'C:\\Codes\\QuizCraft\\gen-lang-client-0625082558-a958e1c7fe1e.json'
            SCOPES = ['https://www.googleapis.com/auth/forms.body', 'https://www.googleapis.com/auth/drive']

            creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)

            # Generiere den Google Form-Link
            google_form_url = quick_generate_google_form(questions_json, pages, module_name)

            # Freigeben des Formulars für die ausgewählten E-Mail-Adressen
            drive_service = build('drive', 'v3', credentials=creds)
            for email in selected_emails:
                drive_service.permissions().create(
                    fileId=google_form_url.split('/d/')[1].split('/edit')[0],
                    body={
                        'type': 'user',
                        'role': 'writer',
                        'emailAddress': email
                    },
                ).execute()

            # Generiere den QR-Code
            qr_code_data = generate_qr_code(google_form_url)

            # `qr_code_data` als Bytes in base64-Format konvertieren
            encoded_qr_code = qr_code_data.decode('latin1')  # Um es als String zu speichern

            return render_template('quick_form_result.html', google_form_url=google_form_url, qr_code=encoded_qr_code)

    elif request.method == 'GET':
        # Daten aus der Session laden und ins Formular setzen
        form.module_name.data = session.get('module_name', '')
        pdf_path = session.get('pdf_file_path')
        if pdf_path and os.path.exists(pdf_path):
            with open(pdf_path, 'rb') as pdf_file:
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                total_pages = len(pdf_reader.pages)

        form.pages.data = session.get('pages', '')

    return render_template('quick_form.html', form=form)

@app.route('/download_qr')
def download_qr():
    qr_code_base64 = session.get('qr_code')
    if qr_code_base64:
        # Dekodiert den Base64-String zurück in Bytes
        qr_code_bytes = base64.b64decode(qr_code_base64)
        buffer = io.BytesIO(qr_code_bytes)
        buffer.seek(0)
        return send_file(buffer, mimetype='image/png', as_attachment=True, download_name='qr_code.png')
    else:
        flash('QR-Code konnte nicht heruntergeladen werden.', 'danger')
        return redirect(url_for('create_google_form'))

@app.route('/show_texts', methods=['GET', 'POST'])
def show_texts():
    form = ShowTextForm()
    module = request.args.get('module') or request.form.get('module') or 'datascience'
    pages = request.args.get('pages') or request.form.get('pages') or None
    texts = None

    if request.method == 'POST':
        selected_pages = request.form.getlist('selected_pages')

        if 'delete' in request.form:
            if selected_pages:
                for page in selected_pages:
                    delete_text_from_db(module, int(page))
                flash(f'{len(selected_pages)} Seite(n) wurde(n) erfolgreich gelöscht.', 'success')
            else:
                flash('Es wurden keine Seiten zum Löschen ausgewählt.', 'warning')

            texts = get_extracted_texts(module, pages=pages)

        elif 'create_questions' in request.form:
            if selected_pages:
                # Speichere die ausgewählten Seiten in der Session
                session['selected_pages'] = selected_pages
                session['module'] = module
                return redirect(url_for('create_question'))
            else:
                flash('Es wurden keine Seiten zum Erstellen von Fragen ausgewählt.', 'warning')

            texts = get_extracted_texts(module, pages=pages)

        else:
            if form.validate_on_submit():
                module = form.module.data
                pages = form.pages.data
                texts = get_extracted_texts(module, pages=pages)
                if not texts:
                    flash('Keine Texte für die angegebenen Seiten gefunden.', 'warning')

    else:
        texts = get_extracted_texts(module, pages=pages)

    form.module.data = module
    form.pages.data = pages
    return render_template('show_texts.html', form=form, module_name=module, texts=texts)

@app.route('/delete_texts', methods=['POST'])
def delete_texts():
    module = request.args.get('module') or 'datascience'

    # Holen Sie sich die ausgewählten Text-IDs aus dem Formular
    selected_text_pages = request.form.getlist('selected_texts')

    if not selected_text_pages:
        flash('Keine Seiten ausgewählt.', 'warning')
        return redirect(url_for('show_texts', module=module))

    # Erstellen Sie die entsprechende Text-Tabelle für das Modul
    TextTable, _ = create_module_tables(module)

    # Öffnen Sie eine Datenbanksitzung
    session = Session()

    # Löschen Sie die ausgewählten Texte
    for text_page in selected_text_pages:
        text = session.query(TextTable).get(int(text_page))
        if text:
            session.delete(text)

    # Änderungen speichern und Sitzung schließen
    session.commit()
    session.close()

    flash('Ausgewählte Texte wurden erfolgreich gelöscht.', 'success')
    return redirect(url_for('show_texts', module=module))

@app.route('/update_text', methods=['POST'])
def update_text():
    page = request.form.get('page')
    updated_text = request.form.get('updated_text')

    if not page or not updated_text:
        return jsonify({'success': False, 'message': 'Missing data'}), 400

    try:
        session = Session()

        # Finde den Text für die gegebene Seite
        text_entry = None
        for module_name in table_cache:
            TextTable, _ = create_module_tables(module_name)
            text_entry = session.query(TextTable).filter_by(page=page).first()
            if text_entry:
                break

        if not text_entry:
            return jsonify({'success': False, 'message': 'Text not found'}), 404

        # Bereinige den aktualisierten Text: Entfernt überflüssige Leerzeichen und Zeilenumbrüche
        cleaned_text = clean_input_text(updated_text)

        # Prüfe, ob der bereinigte Text sich von dem existierenden Text unterscheidet
        if cleaned_text == text_entry.text.strip():
            return jsonify({'success': False, 'message': 'No changes detected'}), 200

        # Aktualisiere den Text in der Datenbank, wenn es Unterschiede gibt
        text_entry.text = cleaned_text
        session.commit()

        return jsonify({'success': True, 'message': 'Text updated successfully'})
    except Exception as e:
        session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        session.close()

# Funktion zum Bereinigen des Textes
def clean_input_text(text):
    return ' '.join(text.split()).strip()

@app.route('/show_questions', methods=['GET', 'POST'])
def show_questions():
    form = ShowQuestionsForm()
    questions = None

    # Abrufen der Parameter aus request.args oder request.form
    module = request.args.get('module') or request.form.get('module') or 'datascience'
    sort_starred = request.args.get('sort_starred') or request.form.get('sort_starred') or 'off'
    sort_starred = sort_starred == 'on'
    pages = request.args.get('pages') or request.form.get('pages') or None

    if request.method == 'POST':
        selected_questions = request.form.getlist('selected_questions')

        if 'delete' in request.form:
            # Aktion: Löschen
            if selected_questions:
                for question_id in selected_questions:
                    delete_question_from_db(module, int(question_id))
                flash(f'{len(selected_questions)} Frage(n) wurde(n) erfolgreich gelöscht.', 'success')
            else:
                flash('Es wurden keine Fragen zum Löschen ausgewählt.', 'warning')
            # Fragen erneut abrufen
            questions = get_extracted_questions(module, sort_starred_first=sort_starred, pages=pages)

        elif 'create_form' in request.form:
            # Aktion: Weiterleitung zur Google Form-Erstellung
            if selected_questions:
                session['selected_questions'] = selected_questions
                session['module'] = module
                return redirect(url_for('create_google_form'))
            else:
                flash('Es wurden keine Fragen zum Erstellen des Google Formulars ausgewählt.', 'warning')
            questions = get_extracted_questions(module, sort_starred_first=sort_starred, pages=pages)

        else:
            # Fragen anzeigen
            if form.validate_on_submit():
                module = form.module.data
                pages = form.pages.data
            else:
                pages = None

    else:
        # GET-Anfrage: Seitenangaben validieren
        if pages:
            total_pages = get_total_pages_for_module(module)
            if not validate_pages(pages, total_pages):
                flash('Ungültige Seitenangaben.', 'danger')
                return redirect(url_for('show_questions', module=module))

    # Fragen abrufen
    questions = get_extracted_questions(module, sort_starred_first=sort_starred, pages=pages)
    if not questions:
        flash('Keine Fragen gefunden.', 'warning')

    # Formularfelder mit aktuellen Werten füllen
    form.module.data = module
    form.pages.data = pages

    return render_template('show_questions.html', form=form, module_name=module, questions=questions, sort_starred=sort_starred)

@app.route('/delete_questions', methods=['POST'])
def delete_questions():
    selected_questions = request.form.getlist('selected_questions')
    module = request.form.get('module')
    form = ShowQuestionsForm()  # Verwenden Sie das richtige Formular
    questions = None

    if selected_questions and module:
        for question_id in selected_questions:
            delete_question_from_db(module, int(question_id))
        flash(f'{len(selected_questions)} Frage(n) wurde(n) erfolgreich gelöscht.', 'success')
    else:
        flash('Es wurden keine Fragen zum Löschen ausgewählt oder Modul fehlt.', 'warning')

    # Fragen erneut abrufen
    questions = get_extracted_questions(module)

    return render_template('show_questions.html', form=form, module_name=module, questions=questions)

@app.route('/toggle_starred', methods=['POST'])
def toggle_starred():
    data = request.get_json()
    question_id = data.get('question_id')
    starred = data.get('starred')
    module = data.get('module')  # Modulname aus den Daten

    # Validierung der Daten
    if question_id and starred is not None and module:
        try:
            session_db = Session()
            _, QuestionTable = create_module_tables(module)
            question = session_db.query(QuestionTable).filter_by(id=question_id).first()
            if question:
                question.starred = starred
                session_db.commit()
                session_db.close()
                return jsonify({'success': True})
            else:
                session_db.close()
                return jsonify({'success': False, 'error': 'Frage nicht gefunden'})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})
    else:
        return jsonify({'success': False, 'error': 'Ungültige Daten'})

@app.route('/update_question', methods=['POST'])
def update_question():
    question_id = request.form.get('question_id')
    updated_question_text = request.form.get('updated_question')

    if not question_id or not updated_question_text:
        return jsonify({'success': False, 'message': 'Missing data'}), 400

    try:
        session = Session()

        # Frage in der Datenbank finden, um das Modul herauszufinden
        question_entry = None
        for module_name in table_cache:
            _, QuestionTable = create_module_tables(module_name)
            question_entry = session.query(QuestionTable).filter_by(id=question_id).first()
            if question_entry:
                break

        if not question_entry:
            return jsonify({'success': False, 'message': 'Question not found'}), 404

        # Aktualisiere den Fragetext
        question_entry.frage = updated_question_text
        session.commit()

        return jsonify({'success': True, 'message': 'Question updated successfully'})
    except Exception as e:
        session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        session.close()

@app.route('/create_google_form', methods=['GET', 'POST'])
def create_google_form():
    form = GoogleFormCreationForm()

    # Laden der verfügbaren E-Mail-Adressen
    emails = load_emails()
    form.first_name.choices = [(name, name) for name in emails.keys()]

    # Verarbeiten von Session-Daten aus show_questions
    selected_questions = session.get('selected_questions')
    module_from_session = session.get('module')

    if selected_questions and module_from_session:
        form.module.data = module_from_session
        form.ids.data = ','.join(selected_questions)
        session.pop('selected_questions', None)
        session.pop('module', None)

    if form.validate_on_submit():
        name = form.module_name.data
        module = form.module.data
        pages = form.pages.data
        ids = form.ids.data
        selected_emails = [emails[name] for name in form.first_name.data]

        # Validierung: Entweder pages oder ids
        if pages and ids:
            flash('Bitte geben Sie entweder Seitenzahlen oder Fragen-IDs an, nicht beides.', 'danger')
            return render_template('create_google_form.html', form=form)
        elif not pages and not ids:
            flash('Bitte geben Sie Seitenzahlen oder Fragen-IDs an.', 'danger')
            return render_template('create_google_form.html', form=form)

        # Fragen abrufen
        if ids:
            question_list = get_questions_by_ids(module, ids)
        elif pages:
            question_list = get_questions_from_db(module, pages)

        if not question_list:
            flash('Keine Fragen gefunden. Bitte überprüfen Sie Ihre Eingaben.', 'warning')
            return render_template('create_google_form.html', form=form)

        # Google Form erstellen
        form_url, qr_code = generate_google_form(name, pages, ids, selected_emails, question_list)

        if form_url and qr_code:
            return render_template('quick_form_result.html', google_form_url=form_url, qr_code=qr_code)
        else:
            flash('Fehler bei der Erstellung des Google Formulars.', 'danger')

    return render_template('create_google_form.html', form=form)

if __name__ == '__main__':
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    app.run(debug=True)