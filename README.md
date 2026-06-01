# 📊 OOP Purity Analyzer v2.0

A premium, full-stack quantitative software engineering and academic research instrument designed to evaluate the Object-Oriented Programming (OOP) purity of GitHub repositories. Moving beyond static, language-level assumptions, **OOP Purity Analyzer v2.0** uses a custom **AST (Abstract Syntax Tree) Code Analysis Engine** to parse actual repository source code alongside a comprehensive 7-category, 24-sub-criterion academic rubric.

It visualizes repository metrics in rich interactive Plotly.js dashboards, supports side-by-side repository comparisons, stores long-term analysis runs in a SQLite database, exposes a RESTful JSON API, and compiles detailed academic scorecards into professional PDF reports.

---

## ✨ Features in v2.0

*   🧠 **AST-Based Code Analysis Engine**: Dynamically clones, parses, and measures the repository code itself. Extracts deep structural OOP indicators (Class count, Encapsulation visibility modifiers, Multiple inheritance constructs, Static/Global utility patterns) to adjust the theoretical base score of the dominant programming language.
*   📊 **Repository Comparison Dashboard**: Select multiple analyzed repositories (2–4) from your history and compare their structural OOP profiles side-by-side using multi-trace radar charts and grouped category comparisons.
*   💾 **SQLite Database Persistence**: Full historical tracking. All past analysis sessions, repository results, and AST metrics are persistently saved in a SQLite database (`instance/oop_analyzer.db`), replacing volatile flask sessions.
*   📄 **Branded PDF Report Generator**: Export detailed analysis runs into beautiful, publication-ready PDF reports built programmatically using Flowable layouts, tabular metrics breakdowns, and academic styling.
*   🔌 **RESTful JSON API**: Exposes the complete scraping, scoring, and historical data engine under `/api/v1/` for external automated scoring pipelines.

---

## 🛠️ Tech Stack

*   **Backend**: Python, Flask, Flask-SQLAlchemy (SQLite)
*   **AST Analysis**: Multi-Language Regex Engine (Python, Java dominant)
*   **Report Generation**: ReportLab (PDF Engine)
*   **Visualizations**: Plotly.js, Vanilla CSS Glassmorphism
*   **API Client**: PyGitHub (Scraping & Metadata Extraction)

---

## 🚀 Local Setup

### 1. Clone the Repository
```bash
git clone <your-repo-url>
cd oop_purity_analyzer
```

### 2. Configure Virtual Environment & Dependencies
```powershell
# Create venv
python -m venv venv

# Activate venv (Windows)
.\venv\Scripts\Activate.ps1

# Install requirements
pip install -r requirements.txt
```

### 3. Setup Environment Configuration
Copy the `.env.example` to `.env`:
```bash
cp .env.example .env
```
Open `.env` and fill out the configuration:
```ini
# Set to your GitHub token for live analysis or 'mock' to run offline with pre-configured datasets
GITHUB_TOKEN=mock
SECRET_KEY=generate-a-strong-random-key
FLASK_ENV=development
SESSION_FILE_DIR=./flask_session
```

### 4. Run the Server
Use the venv python interpreter to start the Flask application:
```powershell
.\venv\Scripts\python app.py
```
Open your browser and navigate to **`http://localhost:5000`**.

---

## 📈 RESTful JSON API Documentation

Exposed endpoints under `/api/v1` for automated scoring integrations:

### 1. Supported Languages
*   **URL**: `/api/v1/languages`
*   **Method**: `GET`
*   **Description**: Get theoretical scoring metrics and categories for the 8 supported OOP languages.

### 2. Historical Analysis Runs
*   **URL**: `/api/v1/history?page=1&per_page=10`
*   **Method**: `GET`
*   **Description**: Fetch paginated database records of all past analysis sessions.

### 3. Analyze Repositories
*   **URL**: `/api/v1/analyze`
*   **Method**: `POST`
*   **Body**:
    ```json
    {
      "mode": "search",
      "input_data": "design patterns",
      "limit": 5
    }
    ```
*   **Description**: Programmatically trigger, score, and persist a new repository analysis run.

### 4. Single Repository Quick-Score
*   **URL**: `/api/v1/score/<owner>/<repo>`
*   **Method**: `GET`
*   **Description**: Retrieve instant score details and AST indicators for a specific repository.

---

## 📊 Academic Scoring Rubric

Theoretical base language scores are distributed across **7 categories (Total 100 points)**:

| Category | OOP Metric Focus | Max Points |
|:---|:---|:---:|
| **C1** | Encapsulation & Access Control | 20 |
| **C2** | Inheritance Mechanics | 15 |
| **C3** | Polymorphism & Dynamic Dispatch | 15 |
| **C4** | Abstraction Models | 15 |
| **C5** | Object-Centric Lifecycle & Design | 15 |
| **C6** | OOP Paradigm Enforcement | 10 |
| **C7** | Advanced OOP Features & Type Safety | 10 |
| | **Total Maximum Score** | **100** |

### 🏷️ Purity Tiering
*   **85–100**: 🟢 **Pure OOP** (e.g., Smalltalk, Java)
*   **65–84**: 🔵 **Near-Pure OOP** (e.g., Python, C#, Kotlin)
*   **45–64**: 🟡 **Mixed Paradigm** (e.g., JavaScript, C++)
*   **25–44**: 🟠 **OOP-Adjacent** (e.g., Go, Rust)
*   **0–24**: 🔴 **Non-OOP** (Procedural/Functional dominants)

---

## 🧠 Code-Level Heuristics (AST Modifiers)
At runtime, the analyzer scans repository files and adjusts base language purity scores:
*   ➕ **Encapsulation Bonus**: Reward usage of `private` and `protected` fields (strict access safety).
*   ➖ **Static/Global Penalty**: Penalty for excessive global functions, file-level variables, or `static` utility classes bypassing object lifecycle principles.
*   ➖ **Anti-Inheritance Penalty**: Penalty for excessive multi-inheritance constructs or non-class-oriented structures in OOP languages.

---

## 📄 Exporting & Citation

### PDF Reports
You can download professional PDFs by clicking the **"Export PDF"** button on the results dashboard or history cards. These reports detail the executive summary, language breakdown, AST modifications, and a technical scorecard.

### Academic Citation
If you use this analyzer or its scoring metrics in your research, please cite:
```text
OOP Purity Framework: An AST-Augmented, 7-Category, 24-Sub-Criterion Quantitative Scoring Rubric for Evaluating Repository-Level Object-Oriented Adherence.
```

---

## 📄 License
This application is designed for research, academic evaluation, and software quality assurance. All rights reserved.
