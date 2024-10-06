from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean
from sqlalchemy.orm import sessionmaker, declarative_base
import datetime
import json

# SQLAlchemy Basis
Base = declarative_base()

# Wichtig um Fehlermeldung zu reparieren: bereits existierende Tabelle erstellen
table_cache = {}

def create_module_tables(module_name):
    # Überprüfen, ob die Tabellen bereits erstellt wurden
    if module_name in table_cache:
        return table_cache[module_name]

    class DynamicTextTable(Base):
        __tablename__ = f'{module_name}_texts'
        __table_args__ = {'extend_existing': True}
        page = Column(Integer, primary_key=True, nullable=False)
        text = Column(Text, nullable=False)

    class DynamicQuestionTable(Base):
        __tablename__ = f'{module_name}_questions'
        __table_args__ = {'extend_existing': True}
        id = Column(Integer, primary_key=True)
        seite = Column(Integer, nullable=False)
        frage = Column(Text, nullable=False)
        starred = Column(Boolean, default=False)

    # Verbindung zur Datenbank herstellen
    engine = create_engine('sqlite:///modular_database.db')
    Base.metadata.create_all(engine)

    # Cache speichern
    table_cache[module_name] = (DynamicTextTable, DynamicQuestionTable)

    return DynamicTextTable, DynamicQuestionTable

# Verbindung zur neuen Datenbank herstellen
engine = create_engine('sqlite:///modular_database.db')
Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def store_page_text(module_name, page, text):
    session = Session()  # Erstelle eine neue Session für diese Funktion
    TextTable, _ = create_module_tables(module_name)  # Erstelle dynamisch die Tabelle
    page_entry = session.query(TextTable).filter_by(page=page).first()

    if page_entry:
        page_entry.text = text  # Aktualisieren, falls der Eintrag bereits existiert
    else:
        page_entry = TextTable(page=page, text=text)
        session.add(page_entry)

    session.commit()
    session.close()  # Session schließen


def retrieve_page_text(module_name, page):
    session = Session()  # Erstelle eine neue Session für diese Funktion
    TextTable, _ = create_module_tables(module_name)
    page_entry = session.query(TextTable).filter_by(page=page).first()
    session.close()  # Session schließen
    return page_entry.text if page_entry else None

# def save_questions_to_db(module_name, questions_json):
#     session = Session()  # Erstelle eine neue Session für diese Funktion
#     _, QuestionTable = create_module_tables(module_name)
#     questions = json.loads(questions_json)
    
#     for question_data in questions:
#         seiten = question_data.get("seiten", "undefined")
#         question = QuestionTable(
#             kapitel=question_data["kapitel"],
#             thema=question_data["thema"],
#             frage=question_data["frage"],
#             antwort=question_data["antwort"],
#             seiten=seiten,
#             erstellungsdatum=datetime.datetime.now(),
#             fragetyp=question_data.get("fragetyp", "Standard"),
#             letzter_aufruf=datetime.datetime.now(),
#             status="In Überprüfung",
#             bewertung="unbewertet",
#             punkteanzahl=0,
#             wiederholungen=0
#         )
#         session.add(question)

#    session.commit()
#    session.close()  # Session schließen

def extract_text_from_pdf_pages(module_name, pages=None):
    session = Session()  # Erstelle eine neue Session für diese Funktion
    TextTable, _ = create_module_tables(module_name)
    
    if pages is None or pages.strip() == '':
        texts = session.query(TextTable).order_by(TextTable.page).all()
        combined_text = " ".join([f"[Seite: {text.page}] {text.text}" for text in texts])
        session.close()  # Session schließen
        return combined_text
    
    combined_text = ""
    pages = pages.replace(' ', '')
    for part in pages.split(','):
        if '-' in part:
            start, end = map(int, part.split('-'))
            for page_num in range(start, end + 1):
                text_entry = session.query(TextTable).filter_by(page=page_num).first()
                if text_entry:
                    combined_text += f"[Seite: {page_num}] {text_entry.text} "
        else:
            page_num = int(part)
            text_entry = session.query(TextTable).filter_by(page=page_num).first()
            if text_entry:
                combined_text += f"[Seite: {page_num}] {text_entry.text} "
    
    session.close()  # Session schließen
    return combined_text.strip()

def get_existing_pages(module_name):
    session = Session()  # **Hier wird die Sitzung instanziiert**
    TextTable, _ = create_module_tables(module_name)  # Erstelle dynamisch die Tabelle
    try:
        existing_pages = session.query(TextTable.page).all()  # **Hier wird eine Sitzung verwendet**
    except Exception as e:
        print(f"Fehler bei der Abfrage: {e}")
        existing_pages = []  # Leere Liste, falls ein Fehler auftritt
    finally:
        session.close()  # Schließe die Sitzung, um Ressourcen freizugeben
    return {page[0] for page in existing_pages}  # Extrahiere die Seitenzahlen aus dem Ergebnis

# << für show_texts.html >>

def get_extracted_texts(module, pages=None):
    session = Session()  # Datenbank-Sitzung öffnen
    TextTable, _ = create_module_tables(module)  # Die entsprechende Text-Tabelle für das Modul abrufen

    # Falls Seiten angegeben sind, filtere nach diesen Seiten
    if pages:
        page_numbers = [int(p.strip()) for p in pages.split(',') if p.strip().isdigit()]
        texts = session.query(TextTable).filter(TextTable.page.in_(page_numbers)).all()
    else:
        # Wenn keine Seiten angegeben sind, alle Texte abrufen
        texts = session.query(TextTable).all()

    session.close()
    return texts


def delete_text_from_db(module_name, page):
    session = Session()
    TextTable, _ = create_module_tables(module_name)

    # Finde den Eintrag mit der angegebenen Seite und lösche ihn
    text_entry = session.query(TextTable).filter_by(page=page).first()
    if text_entry:
        session.delete(text_entry)
        session.commit()

    session.close()

# << für show_questions.html >>

def get_extracted_questions(module_name, sort_starred_first=False, pages=None):
    session = Session()
    _, QuestionTable = create_module_tables(module_name)
    query = session.query(QuestionTable)

    if pages:
        page_numbers = parse_pages(pages)
        query = query.filter(QuestionTable.seite.in_(page_numbers))

    if sort_starred_first:
        questions = query.order_by(QuestionTable.starred.desc(), QuestionTable.seite.asc()).all()
    else:
        questions = query.order_by(QuestionTable.seite.asc()).all()

    session.close()
    return questions

def parse_pages(pages_str):
    page_numbers = set()
    for part in pages_str.split(','):
        part = part.strip()
        if '-' in part:
            try:
                start, end = map(int, part.split('-'))
                page_numbers.update(range(start, end + 1))
            except ValueError:
                continue  # Ungültiger Bereich wird ignoriert
        else:
            try:
                page_numbers.add(int(part))
            except ValueError:
                continue  # Ungültige Zahl wird ignoriert
    return list(page_numbers)

def get_total_pages_for_module(module_name):
    session = Session()
    TextTable, _ = create_module_tables(module_name)
    total_pages = session.query(TextTable.page).count()
    session.close()
    return total_pages

def delete_question_from_db(module_name, question_id):
    session = Session()  # Erstelle eine neue Session
    _, QuestionTable = create_module_tables(module_name)
    question = session.query(QuestionTable).filter_by(id=question_id).first()

    if question:
        session.delete(question)
        session.commit()
    
    session.close()



# DELETE FROM modul1_texts WHERE id IN (SELECT id FROM modul1_texts ORDER BY id DESC LIMIT 5);