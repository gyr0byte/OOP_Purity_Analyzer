# OOP Purity Analyzer

A quantitative research instrument that scrapes GitHub repositories, identifies their primary programming language, applies a predefined academic OOP Purity scoring rubric, and presents all findings through an interactive web dashboard. The application evaluates languages across 7 core OOP categories and 24 sub-criteria to produce a total purity score out of 100 points.

This tool is designed for academic and comparative research into the object-oriented purity of programming languages. The scoring rubric is based on authoritative language specifications and peer-reviewed academic literature, providing a rigorous, reproducible framework for evaluating how faithfully a language adheres to OOP principles such as encapsulation, inheritance, polymorphism, abstraction, and object-centric design.

## Prerequisites

- **Python 3.10+**
- **GitHub Personal Access Token** (with `repo` scope for public repos)
- **pip** (Python package manager)

## Local Setup

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd oop_purity_analyzer
```

### 2. Create a Virtual Environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

```bash
cp .env.example .env
```

Edit `.env` and configure your credentials:

```ini
# Use 'mock' to run the application with high-fidelity pre-configured offline mock data
# Or replace with a real GitHub Personal Access Token to query live repositories
GITHUB_TOKEN=mock
SECRET_KEY=a-random-secret-key-for-flask
FLASK_ENV=development
SESSION_FILE_DIR=./flask_session
```

### 5. Run the Application

To run the application:

```bash
flask run
```

Or:

```bash
python app.py
```

The app will start locally and will be available in your browser at:
**`http://localhost:5000`** (or `http://127.0.0.1:5000`)

## How to Get a GitHub Personal Access Token

1. Go to [github.com/settings/tokens](https://github.com/settings/tokens)
2. Click **"Generate new token"** → **"Generate new token (classic)"**
3. Give it a descriptive name (e.g., "OOP Purity Analyzer")
4. Select the **`public_repo`** scope (under `repo`)
5. Click **"Generate token"**
6. Copy the token immediately (you won't see it again)
7. Paste it into your `.env` file as `GITHUB_TOKEN`

## Usage Guide

### Mode 1: By URL

Enter one or more full GitHub repository URLs, one per line:

```
https://github.com/django/django
https://github.com/spring-projects/spring-framework
https://github.com/rails/rails
```

### Mode 2: By Topic/Keyword

Enter a search keyword or topic (e.g., "machine learning", "web framework") and set the maximum number of repositories to analyze (1–100).

### Mode 3: By GitHub Username

Enter a GitHub username (e.g., "torvalds", "gvanrossum") and set the maximum number of repositories to fetch (1–100).

## Scoring Rubric

### Categories and Maximum Scores

| Code | Category | Max Score |
|------|----------|-----------|
| C1 | Encapsulation | 20 |
| C2 | Inheritance | 15 |
| C3 | Polymorphism | 15 |
| C4 | Abstraction | 15 |
| C5 | Object-Centric Design | 15 |
| C6 | OOP Enforcement & Non-OOP Resistance | 10 |
| C7 | Type System & Supplementary OOP Features | 10 |
| | **Total** | **100** |

### Sub-Criteria Count

- **C1**: 5 sub-criteria (C1.1–C1.5)
- **C2**: 5 sub-criteria (C2.1–C2.5)
- **C3**: 4 sub-criteria (C3.1–C3.4)
- **C4**: 4 sub-criteria (C4.1–C4.4)
- **C5**: 4 sub-criteria (C5.1–C5.4)
- **C6**: 3 sub-criteria (C6.1–C6.3)
- **C7**: 3 sub-criteria (C7.1–C7.3)

## Purity Tier Definitions

| Score Range | Tier | Description |
|-------------|------|-------------|
| 85–100 | Pure OOP | Language enforces OOP as the sole paradigm |
| 65–84 | Near-Pure OOP | Strong OOP with minor non-OOP allowances |
| 45–64 | Mixed Paradigm | Supports OOP but also other paradigms equally |
| 25–44 | OOP-Adjacent | Has OOP features but doesn't enforce them |
| 0–24 | Non-OOP | Minimal or no OOP support |

## Supported Languages

Smalltalk, Java, Python, JavaScript, C++, Ruby, C#, Kotlin

## Deployment (Render / Railway)

### Using Gunicorn

Create a `Procfile` or configure the start command:

```
web: gunicorn app:app --bind 0.0.0.0:$PORT
```

### Environment Variables

Set the following environment variables in your deployment platform:

- `GITHUB_TOKEN` — Your GitHub Personal Access Token
- `SECRET_KEY` — A strong random secret for Flask sessions
- `FLASK_ENV` — Set to `production`
- `SESSION_FILE_DIR` — Set to `./flask_session`

## Known Limitations

- **Only 8 languages supported**: Smalltalk, Java, Python, JavaScript, C++, Ruby, C#, and Kotlin. Repositories using other languages will be marked as "Unsupported."
- **Scores are static/predefined**: OOP purity scores are based on language specifications and academic literature, not inferred from source code at runtime.
- **GitHub API rate limits**: The GitHub API allows 5,000 requests per hour for authenticated users. Large analyses may hit this limit.
- **Session storage**: Results are stored in the Flask session (filesystem). They persist until the server restarts or the session expires.

## Citation

If using this tool in academic work, please reference the scoring rubric as:

> OOP Purity Framework: A 7-Category, 24-Sub-Criterion Quantitative Scoring Rubric for Evaluating Object-Oriented Programming Language Purity.

## License

This project is intended for academic and research purposes.
