from flask_wtf import FlaskForm
from wtforms.widgets import ListWidget, CheckboxInput
from wtforms.validators import DataRequired, Optional, NumberRange
from wtforms import SelectMultipleField, FloatField, IntegerField
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import StringField, SubmitField, SelectField, BooleanField, TextAreaField

# Dynamische Auswahl der Module
available_modules = [
    ('datascience', 'Data Science'),
    ('algodat', 'Algorithmen und Datenstrukturen'),
    # Weitere Module hier hinzufügen
]

class UploadForm(FlaskForm):
    module = SelectField('Modul auswählen', choices=available_modules, validators=[DataRequired()])
    pdf_file = FileField('PDF hochladen', validators=[FileRequired(), FileAllowed(['pdf'], 'Nur PDFs erlaubt!')])
    changes = BooleanField('Gab es Änderungen seit dem letzten Upload?', validators=[Optional()])
    pages = StringField('Seitenzahlen angeben', validators=[Optional()])
    submit = SubmitField('Hochladen')

class QuestionForm(FlaskForm):
    module = SelectField('Modul auswählen', choices=available_modules, validators=[DataRequired()])
    pages = StringField('Seitenzahlen angeben', validators=[DataRequired()])
    max_output_tokens = IntegerField(
        'Maximale Ausgabetokens', 
        default=2048, 
        validators=[NumberRange(min=1, max=8192, message="Maximale Ausgabetokens müssen mindestens 1 sein.")]
    )
    temperature = FloatField(
        'Temperatur', 
        default=0.20, 
        validators=[NumberRange(min=0, max=1, message="Temperatur muss zwischen 0 und 1 liegen.")]
    )
    top_k = IntegerField(
        'Top-K', 
        default=40, 
        validators=[NumberRange(min=0, message="Top-K muss mindestens 0 sein.")]
    )
    top_p = FloatField(
        'Top-P', 
        default=0.95, 
        validators=[NumberRange(min=0, max=1, message="Top-P muss zwischen 0 und 1 liegen.")]
    )
    
    submit = SubmitField('Fragen generieren')

class ShowQuestionsForm(FlaskForm):
    module = SelectField('Modul auswählen', choices=available_modules, validators=[DataRequired()])
    pages = StringField('Seitenzahlen angeben', validators=[Optional()])
    submit = SubmitField('Fragen anzeigen')

class ShowTextForm(FlaskForm):
    module = SelectField('Modul auswählen', choices=available_modules, validators=[DataRequired()])
    pages = StringField('Seitenzahlen angeben', validators=[Optional()])
    submit = SubmitField('Texte anzeigen')

class GoogleFormCreationForm(FlaskForm):
    module_name = StringField('Name', validators=[Optional()])
    module = SelectField('Modul auswählen', choices=available_modules, validators=[DataRequired()])
    pages = StringField('Seitenzahlen (z.B. 5,6,10-12)', validators=[Optional()])
    ids = StringField('Fragen-IDs (z.B. 1,2,5-7)', validators=[Optional()])
    first_name = SelectMultipleField('Zur Freigabe auswählen', choices=[], coerce=str, option_widget=CheckboxInput(), widget=ListWidget(prefix_label=False))
    submit = SubmitField('Formular erstellen')


class QuickForm(FlaskForm):
    module_name = StringField('Name', validators=[Optional()])
    pdf_file = FileField('PDF hochladen', validators=[FileRequired(), FileAllowed(['pdf'], 'Nur PDFs erlaubt!')], render_kw={"class": "form-control", "id": "formFile"})
    pages = StringField('Seitenzahlen angeben', validators=[Optional()], render_kw={"class": "form-control", "id": "pages"})
    first_name = SelectMultipleField('Zur Freigabe auswählen', choices=[], coerce=str, option_widget=CheckboxInput(), widget=ListWidget(prefix_label=False))
    submit = SubmitField('Formular generieren', render_kw={"class": "btn btn-primary btn-lg w-100"})