# C AutoGrader

A Computing Lab project for grading C programs using instructor-defined rules and test cases.

The application grades one C file. Up to four additional C files can be uploaded for originality comparison only.

## 1. Install requirements

Install:
- Python 3.11
- Docker Desktop
- Ollama

Open Docker Desktop and Ollama. On Windows, use Docker's Linux containers.

## 2. Install Python packages

Open a terminal in the project folder.

### Windows — Command Prompt

```bat
py -3.11 -m venv .venv
.venv\Scripts\activate.bat
python -m pip install -r requirements.txt
```

### macOS — Terminal

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## 3. Prepare Docker and Llama

Run once from the project folder:

```bash
docker build -t autograder-c:1 .
ollama pull llama3.2:1b
```

In the instructor JSON, set the readability model to:

```json
"model": "llama3.2:1b"
```

## 4. Run the project

Keep Docker and Ollama running, then run:

```bash
python app.py
```

Open the local URL shown in the terminal.

Upload:
- One C file to grade.
- Up to four optional C files for similarity comparison.
- Instructor JSON.
- Test-cases JSON.

Click **Generate report** to view and download the TXT and JSON reports.

Keep `report_notes.json` beside `feedback.py`.

## 5. Run again later

Open Docker and Ollama, activate the environment, and start the app.

Windows:

```bat
.venv\Scripts\activate.bat
python app.py
```

macOS:

```bash
source .venv/bin/activate
python app.py
```

Press **Ctrl+C** in the terminal to stop the app.