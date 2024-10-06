# QuizCraft

**QuizCraft** is a Full-Stack-Python tool for generating questions from PDF documents and automatically creating Google Forms with those questions. This tool is designed for educators and students to automate the process of creating quizzes and assessments based on provided materials.

## Features

- Upload PDF files and extract texts.
- Automatically generate questions based on the extracted texts.
- Create Google Forms with the generated questions.
- Customize question generation parameters (e.g., temperature, top_k, etc.).
- Assign permissions to users to access and edit the Google Forms.

## Prerequisites

Before running this project, ensure you have the following:

1. **Python 3.12+** installed on your system.
2. A Google Cloud Project set up with **access to Google APIs** (explained below).
3. **gen-lang-client-XXXXX.json** file for authentication with Google APIs.
4. **email_give_edit_permission.json** file for assigning permissions (explained below).
5. **tesseract** installed and included in your system's PATH (explained below).

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/Csed-dev/quizcraft.git
cd quizcraft
```

### 2. Create a virtual environment (optional, but recommended)

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Required Files

1. **gen-lang-client-XXXXX.json**:  
   You need a Google Cloud API service account file (`gen-lang-client-XXXXX.json`) to connect to the Google services. This file should be placed in the root directory of the project.

2. **email_give_edit_permission.json**:  
   This file should contain the list of users who will be available for permission sharing when creating Google Forms. The format is as follows:

   ```json
   [
       {
           "first_name": "John",
           "last_name": "Doe",
           "email": "john.doe@example.com"
       },
       {
           "first_name": "Jane",
           "last_name": "Smith",
           "email": "jane.smith@example.com"
       }
   ]
   ```

   Replace the sample data with your actual email addresses.

3. **.env file**:  
   You need to create a `.env` file to store your API key securely. Add the following line to your `.env` file:

   ```
   GOOGLE_API_KEY_QUIZCRAFT=your_google_api_key_here
   ```

### 5. OCR for Text Extraction

For the application to extract text from PDF files using Optical Character Recognition (OCR), you will need to install **Tesseract**. This is especially necessary if the PDFs contain images or scanned documents rather than selectable text.

#### Tesseract Installation:
- **Windows**: You can download Tesseract from [here](https://sourceforge.net/projects/tesseract-ocr-alt/files/).
   For further information visit the orignal GitHub-Page [here](https://github.com/tesseract-ocr/tessdoc/blob/main/README.md).
- **Linux**: Use the following command:
  ```bash
  sudo apt-get install tesseract-ocr
  ```
- **MacOS**: Use Homebrew to install Tesseract:
  ```bash
  brew install tesseract
  ```

After installation, make sure the `tesseract` executable is available in your system's PATH. The application uses the **pytesseract** Python library, which interfaces with Tesseract for OCR functionality. Ensure that you also install the **pytesseract** package via pip:
```bash
pip install pytesseract
```

### 6. Dynamic Module Selection

In the file `forms.py`, you can specify the available modules for dynamic selection on the website. The `available_modules` list at the top of the file allows you to add modules that can be displayed in the application. Each entry in the list consists of two elements: the first is the **prefix name** used for database identification, and the second is the **display name** shown on the website. To add more modules, simply append them to the list following the existing format.

Example:
```python
# Dynamic selection of modules
available_modules = [
    ('datascience', 'Data Science'),
    ('algodat', 'Algorithms and Data Structures'),
    # Add more modules here
]
```
When using a new modul in your application, new tables will automatically be created under `prefix_texts` and `prefix_questions`.

### 7. Required Google APIs
- Drive Labels API					
- Gemini for Google Cloud API					
- Generative Language API					
- Google Drive API					
- Google Forms API

You can enable this in your Google Cloud Project under "Enabled APIs and services", press "+ ENABLE APIS AND SERVICES" and search for the required APIs.

### 8. Run the application

After setting up the environment and required files, you can run the application locally.

```bash
flask run
```

The app will be available at `http://127.0.0.1:5000/`.

As first, you need to upload a PDF that will be extracted. Then you can generate Questions and after that you may create a Google-Form.

## License

This project is licensed under the **MIT License**. See the [LICENSE](LICENSE) file for more details.

## Contact
For any questions or suggestions, please reach out to mikyta.mikyta@gmail.com.
