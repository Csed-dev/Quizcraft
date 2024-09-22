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
2. A Google Cloud Project set up with access to Google Forms API and Generative AI API.
3. **gen-lang-client-XXXXX.json** file for authentication with Google APIs (explained below).
4. **email_give_edit_permission.json** file for assigning permissions (explained below).

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

### 5. Run the application

After setting up the environment and required files, you can run the application locally.

```bash
flask run
```

The app will be available at `http://127.0.0.1:5000/`.

### 6. Customize Question Generation

In the user interface, you can specify custom parameters for question generation. These include:

- **Temperature**: Controls the randomness of the model's output. A higher value (e.g., 1) produces more creative results, while a lower value (e.g., 0.2) produces more focused results.
- **Top-K**: Limits the next word's probability distribution to the top-K most likely tokens.
- **Top-P**: Limits the probability of selecting the next token based on a cumulative probability threshold.

These parameters can be adjusted or set to default values.

## License

This project is licensed under the **MIT License**. See the [LICENSE](LICENSE) file for more details.
