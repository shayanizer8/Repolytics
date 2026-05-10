# Repolytics

A powerful GitHub repository analyzer that provides instant insights into any repo's tech stack, health, and activity.

## Features

- **Tech Stack Detection**: Automatically detects frameworks (React, Django, Express, etc.), databases (MongoDB, PostgreSQL, etc.), package managers, and more
- **Health Scoring**: Intelligent health scoring that adapts based on project type (library, application, documentation, CLI)
- **Activity Analysis**: Tracks stars, forks, issues, contributors, and commit activity
- **Repository Comparison**: Compare two repositories side-by-side
- **LLM-Powered Insights**: Uses Groq LLM for README summarization and deep tech stack inference
- **Caching**: Redis-based caching for faster repeated analysis

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/repolytics.git
cd repolytics

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys
```

## Environment Variables

Create a `.env` file with:

```env
GITHUB_TOKEN=your_github_personal_access_token
GROQ_API_KEY=your_groq_api_key
REDIS_HOST=localhost
REDIS_PORT=6379
```

### Getting GitHub Token
1. Go to GitHub Settings → Developer settings → Personal access tokens
2. Generate a classic token with `repo` scope

### Getting Groq API Key
1. Sign up at [groq.com](https://groq.com)
2. Get your API key from the dashboard

## Usage

### Analyze a Repository

```bash
python -m cli.main analyze https://github.com/owner/repo
```

Or use the CLI command:

```bash
python -m cli.main analyze github.com/owner/repo
```

Options:
- `--no-cache` - Skip cache and fetch fresh data
- `--export pdf|markdown` - Export results (coming soon)

### Compare Two Repositories

```bash
python -m cli.main compare https://github.com/repo1 https://github.com/repo2
```

### Run as API Server

```bash
uvicorn api.main:app --reload
```

API will be available at `http://localhost:8000`

## Output Example

```
┌─────────────────────────────────────────┐
│ Repository                              │
├─────────────────────────────────────────┤
│ repo-name                               │
│ https://github.com/owner/repo           │
│                                         │
│ 🟢 High (85)                            │
└─────────────────────────────────────────┘

┌───────────────────┬─────────────────────┐
│ Tech Stack        │                     │
├───────────────────┼─────────────────────┤
│ Languages         │ JavaScript, HTML    │
│ Framework         │ MERN Stack          │
│ Database          │ MongoDB             │
│ CI/CD             │ GitHub Actions      │
│ Containerization  │ Docker              │
│ Package Manager   │ npm                 │
│ Has Tests         │ ✓                   │
│ Has CI            │ ✓                   │
└───────────────────┴─────────────────────┘

┌───────────────────┬─────────────────────┐
│ Activity          │                     │
├───────────────────┼─────────────────────┤
│ Stars             │ 1250                 │
│ Forks             │ 89                   │
│ Open Issues       │ 12                   │
│ Days Since Commit │ 3                    │
│ Contributors      │ 5                   │
│ Is Active         │ ✓                    │
└───────────────────┴─────────────────────┘

┌───────────────────┬─────────────────────┐
│ Language Breakdown                      │
├───────────────────┼─────────────────────┤
│ JavaScript        │ 75.2%               │
│ HTML              │ 14.5%               │
│ CSS               │ 10.3%               │
└───────────────────┴─────────────────────┘

┌─────────────────────────────────────────┐
│ README                                   │
├─────────────────────────────────────────┤
│ Summary: A full-stack MERN application  │
│ Purpose: Real-time chat application     │
│ Audience: Developers building chat apps │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│ Project Flags                           │
├─────────────────────────────────────────┤
│ Missing:                                │
│ • No CI/CD pipeline                     │
│ • Not containerized                    │
└─────────────────────────────────────────┘
```

## Project Structure

```
repolytics/
├── cli/            # Command-line interface
├── core/           # Core analysis logic
│   ├── analyzer.py     # Repository analysis
│   ├── fetcher.py      # GitHub API fetching
│   ├── llm.py          # LLM-powered insights
│   ├── cache.py       # Redis caching
│   └── db.py          # Database models
├── api/            # FastAPI server
├── web/            # Web frontend (future)
└── requirements.txt
```

## How It Works

### Tech Stack Detection
1. **Static Analysis**: Scans file tree for indicators (package.json, requirements.txt, Dockerfiles, etc.)
2. **Package.json Analysis**: Fetches and parses package.json from root and subdirectories to detect exact dependencies
3. **LLM Inference**: Uses Groq LLM for deeper framework and database inference

### Health Scoring
Scoring adapts based on project type:
- **Libraries**: Lower thresholds for stars/forks, values documentation quality
- **Applications**: Emphasizes tests, CI/CD, and containerization
- **Documentation**: Focuses on community engagement
- **Mature Projects**: Less penalty for inactivity

| Factor | Weight (App) | Weight (Library) |
|--------|--------------|------------------|
| Tests | 25 | 15 |
| CI/CD | 25 | 10 |
| Activity | 20 | 15 |
| Stars | 10 | 15 |
| Forks | 5 | 15 |

## Tech Stack

- **Language**: Python
- **LLM**: Groq (Llama 3.3)
- **CLI**: Rich, Typer
- **API**: FastAPI
- **Cache**: Redis
- **Database**: PostgreSQL (via SQLAlchemy + asyncpg)

## License

MIT License

## Contributing

Contributions are welcome! Please open an issue or submit a PR.