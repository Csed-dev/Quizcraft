import re
import PyPDF2
import pytesseract
from pdf2image import convert_from_path
from app_database import store_page_text, create_module_tables, Session

# Setze den Pfad zur Tesseract-Installation (nur für Windows notwendig)
pytesseract.pytesseract.tesseract_cmd = r'C:\\Program Files\\Tesseract-OCR\\tesseract.exe'

def validate_pages(pages, total_pages):
    try:
        total_pages = int(total_pages)  # Sicherstellen, dass total_pages ein Integer ist
    except ValueError:
        print(f"Ungültiger Wert für die Gesamtseitenzahl: {total_pages}")
        return False

    valid_pages = []
    for part in pages.split(','):
        part = part.strip()
        if '-' in part:
            try:
                start, end = map(int, part.split('-'))  # Konvertiere sowohl start als auch end in int
            except ValueError:
                print(f"Ungültiger Seitenbereich: {part}")
                return False

            if start > end:
                print(f"Ungültiger Seitenbereich: {start}-{end}. Startseite muss kleiner oder gleich Endseite sein.")
                return False
            if start < 1 or end > total_pages:
                print(f"Seitenbereich {start}-{end} liegt außerhalb des gültigen Bereichs (1-{total_pages}).")
                return False
            valid_pages.append(f"{start}-{end}")
        else:
            try:
                page = int(part)  # Konvertiere page in int
            except ValueError:
                print(f"Ungültige Seitenangabe: {part}")
                return False

            if page < 1 or page > total_pages:
                print(f"Seite {page} liegt außerhalb des gültigen Bereichs (1-{total_pages}).")
                return False
            valid_pages.append(str(page))
    return True

def get_existing_pages(module_name):
    # Erstellt eine Sitzung mit dem Session-Maker
    session = Session()  
    TextTable, _ = create_module_tables(module_name)  # Erstelle dynamisch die Tabelle
    try:
        existing_pages = session.query(TextTable.page).all()  # Führe die Abfrage aus
    except Exception as e:
        print(f"Fehler bei der Abfrage: {e}")
        existing_pages = []  # Leere Liste, falls ein Fehler auftritt
    finally:
        session.close()  # Schließe die Sitzung, um Ressourcen freizugeben
    return {page[0] for page in existing_pages}  # Extrahiere die Seitenzahlen aus dem Ergebnis

def extract_pages(module_name, pdf_path, pages=None):
    with open(pdf_path, 'rb') as pdf_file:
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        total_pages = len(pdf_reader.pages)

        extracted_texts = {}

        if not pages:  # Wenn keine Seiten angegeben wurden
            existing_pages = get_existing_pages(module_name)
            pages_to_process = [page for page in range(1, total_pages + 1) if page not in existing_pages]
        else:
            pages_to_process = []
            for part in pages.split(','):
                part = part.strip()
                if '-' in part:
                    start, end = map(int, part.split('-'))
                    pages_to_process.extend(range(start, end + 1))
                else:
                    pages_to_process.append(int(part))
            pages_to_process = [page for page in pages_to_process if page not in get_existing_pages(module_name)]

        for page in pages_to_process:
            text = extract_page_text(pdf_path, page)
            # Text mit Seitenanzahl hinzufügen
            text_with_page = f"[Seite: {page}] {text}"
            store_page_text(module_name, page, text_with_page)
            extracted_texts[page] = text_with_page

        return extracted_texts


def extract_page_text(pdf_path, page_number):
    # Konvertiere die bestimmte Seite in ein Bild und führe OCR durch
    images = convert_from_path(pdf_path, first_page=page_number, last_page=page_number)

    text = ""
    for image in images:
        text += pytesseract.image_to_string(image) + "\n"

    return clean_text(text)


def clean_text(text):
    text = text.replace('-\n', '')
    text = text.replace('\n', ' ')
    return ' '.join(text.split())
