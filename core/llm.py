import json
import logging
import os
from typing import Dict, Any
from groq import AsyncGroq
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a code analysis assistant. Always respond with valid JSON only. "
    "No markdown, no backticks, no explanation. Just the JSON object."
)

MODEL = "llama-3.3-70b-versatile"
TEMPERATURE = 0.3


def _get_groq_client() -> AsyncGroq:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY environment variable not set")
    return AsyncGroq(api_key=api_key)


async def summarize_readme(readme_text: str) -> dict:
    if not readme_text or readme_text.strip() == "":
        return {
            "summary": "No README found",
            "purpose": "",
            "audience": "",
        }
    
    truncated_readme = readme_text[:3000]
    
    prompt = f"""Analyze this README and provide a structured analysis in JSON format:

README:
{truncated_readme}

Return ONLY a JSON object with these keys:
- summary: 2-3 sentence overview of what the project does
- purpose: one line — the core problem it solves
- audience: who this project is for"""
    
    try:
        client = _get_groq_client()
        message = await client.chat.completions.create(
            model=MODEL,
            temperature=TEMPERATURE,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        )
        
        response_text = message.choices[0].message.content.strip()
        result = json.loads(response_text)
        
        return {
            "summary": result.get("summary", ""),
            "purpose": result.get("purpose", ""),
            "audience": result.get("audience", ""),
        }
    except Exception as e:
        logger.error(f"Error summarizing README: {e}")
        return {
            "summary": "",
            "purpose": "",
            "audience": "",
        }


async def detect_code_smells(
    file_tree: list,
    languages: dict,
    tech_stack: dict,
    activity: dict = None,
) -> dict:
    if activity is None:
        activity = {}
    
    flags = []
    
    if not tech_stack.get("has_tests", False):
        flags.append("No tests")
    
    if not tech_stack.get("has_ci", False):
        flags.append("No CI/CD pipeline")
    
    if not tech_stack.get("containerized", False):
        flags.append("Not containerized")
    
    days_since = activity.get("days_since_commit")
    if days_since is not None and days_since > 90:
        flags.append("Inactive project (90+ days)")
    
    contributor_count = activity.get("contributor_count", 0)
    if contributor_count < 2:
        flags.append("Single contributor")
    
    return {
        "flags": flags,
        "suggestions": [],
    }


async def compare_repos(repo_a: dict, repo_b: dict) -> dict:
    a_name = repo_a.get("name", "Repository A")
    b_name = repo_b.get("name", "Repository B")
    
    a_health = repo_a.get("health_score", 0)
    b_health = repo_b.get("health_score", 0)
    
    a_activity = repo_a.get("activity", {})
    b_activity = repo_b.get("activity", {})
    
    a_tech = repo_a.get("tech_stack", {})
    b_tech = repo_b.get("tech_stack", {})
    
    prompt = f"""Compare these two repositories:

Repository A: {a_name}
- Health Score: {a_health}/100
- Stars: {a_activity.get('stars', 0)}
- Active: {a_activity.get('is_active', False)}
- Tests: {a_tech.get('has_tests', False)}
- CI/CD: {a_tech.get('has_ci', False)}
- Contributors: {a_activity.get('contributor_count', 0)}

Repository B: {b_name}
- Health Score: {b_health}/100
- Stars: {b_activity.get('stars', 0)}
- Active: {b_activity.get('is_active', False)}
- Tests: {b_tech.get('has_tests', False)}
- CI/CD: {b_tech.get('has_ci', False)}
- Contributors: {b_activity.get('contributor_count', 0)}

Return ONLY a JSON object with these keys:
- verdict: which repo is better maintained and why (2-3 sentences)
- winner: "repo_a" or "repo_b" or "tie"
- reasoning: object with keys activity, code_quality, community, documentation 
  (each value is a one-line comparison string)"""
    
    try:
        client = _get_groq_client()
        message = await client.chat.completions.create(
            model=MODEL,
            temperature=TEMPERATURE,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        )
        
        response_text = message.choices[0].message.content.strip()
        result = json.loads(response_text)
        
        return {
            "verdict": result.get("verdict", ""),
            "winner": result.get("winner", "tie"),
            "reasoning": result.get("reasoning", {
                "activity": "",
                "code_quality": "",
                "community": "",
                "documentation": "",
            }),
        }
    except Exception as e:
        logger.error(f"Error comparing repositories: {e}")
        return {
            "verdict": "",
            "winner": "tie",
            "reasoning": {
                "activity": "",
                "code_quality": "",
                "community": "",
                "documentation": "",
            },
        }


async def infer_tech_stack(
    file_tree: list,
    languages: dict,
) -> dict:
    """
    LLM-based tech stack inference.
    Analyzes file tree and language breakdown to identify:
    - framework
    - database  
    - ci_cd
    - containerization
    
    Returns JSON with these fields.
    Falls back to empty values on error.
    """
    if not file_tree:
        return {
            "framework": None,
            "database": None,
            "ci_cd": None,
            "containerization": None,
        }
    
    # Build language breakdown summary
    total_bytes = sum(languages.values()) if languages else 1
    language_breakdown = {}
    if total_bytes > 0:
        for lang, bytes_count in languages.items():
            percentage = round((bytes_count / total_bytes) * 100, 1)
            language_breakdown[lang] = percentage
    
    # Sort by percentage descending
    sorted_langs = sorted(language_breakdown.items(), key=lambda x: x[1], reverse=True)
    lang_summary = ", ".join([f"{lang}: {pct}%" for lang, pct in sorted_langs[:5]])
    
    # Build prompt
    prompt = f"""Analyze this repository structure and language composition to identify the tech stack.

File Tree (Root Directory Files):
{', '.join(file_tree[:50])}

Language Breakdown:
{lang_summary}

For CI/CD detection, check for these specific signals:
- ".github" or ".github/workflows" in filenames → "GitHub Actions"
- ".travis.yml" → "Travis CI"
- ".circleci" → "CircleCI"
- "Jenkinsfile" → "Jenkins"
- ".gitlab-ci.yml" → "GitLab CI"
- "azure-pipelines.yml" → "Azure Pipelines"

For containerization, check for these specific signals:
- Any file containing "dockerfile" (case-insensitive) → "Docker"
- Any file containing "docker-compose" → "Docker Compose"
- Both dockerfile and docker-compose present → "Docker + Compose"
- ".dockerignore" present → "Docker"
- "kubernetes" or "k8s" in any filename → "Kubernetes"

Based on this information, infer:
- framework: The primary web/app framework (e.g., Django, React, Spring, etc.). Return null if not evident.
- database: Database system(s) used (e.g., PostgreSQL, MongoDB, Redis). Can be multiple separated by +. Return null if not evident.
- ci_cd: CI/CD platform from the signals above. Return null if not evident.
- containerization: Containerization tech from the signals above. Return null if not evident.
- reasoning: One line explaining how you determined this.

Return ONLY valid JSON with these exact keys."""
    
    try:
        client = _get_groq_client()
        message = await client.chat.completions.create(
            model=MODEL,
            temperature=0.1,  # Low temperature for consistency
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an expert software engineer. Analyze the provided repository "
                        "structure and dependency files to identify the tech stack. Be specific "
                        "and accurate. If you truly cannot determine something return null. "
                        "Respond with valid JSON only. No markdown, no backticks."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
        )
        
        response_text = message.choices[0].message.content.strip()
        result = json.loads(response_text)
        
        return {
            "framework": result.get("framework"),
            "database": result.get("database"),
            "ci_cd": result.get("ci_cd"),
            "containerization": result.get("containerization"),
        }
    except Exception as e:
        logger.error(f"Error inferring tech stack: {e}")
        return {
            "framework": None,
            "database": None,
            "ci_cd": None,
            "containerization": None,
        }
