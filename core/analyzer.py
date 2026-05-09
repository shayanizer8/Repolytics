import asyncio
from datetime import datetime
from typing import Dict, Any


def analyze_repo(repo_data: dict) -> dict:
    languages = _analyze_languages(repo_data.get("languages", {}))
    tech_stack = _analyze_tech_stack(
        repo_data.get("file_tree", []),
        repo_data.get("languages", {}),
    )
    activity = _analyze_activity(
        repo_data.get("last_commit"),
        repo_data.get("contributors", []),
        repo_data.get("stars", 0),
        repo_data.get("forks", 0),
        repo_data.get("open_issues", 0),
    )
    health_score = _calculate_health_score(repo_data, activity, tech_stack)
    
    return {
        "languages": languages,
        "tech_stack": tech_stack,
        "activity": activity,
        "health_score": health_score,
    }


def _analyze_languages(languages: dict) -> dict:
    if not languages:
        return {}
    
    total_bytes = sum(languages.values())
    if total_bytes == 0:
        return {}
    
    return {
        lang: round((bytes_count / total_bytes) * 100, 2)
        for lang, bytes_count in languages.items()
    }


def _analyze_tech_stack(file_tree: list, languages: dict) -> dict:
    file_tree_lower = [f.lower() for f in file_tree]
    
    primary_language = _get_primary_language(languages)
    framework = _detect_framework(file_tree_lower)
    containerized = _has_containerization(file_tree_lower)
    has_ci = _has_ci_cd(file_tree_lower)
    has_tests = _has_tests(file_tree_lower)
    database = _detect_database(file_tree_lower)
    
    return {
        "language": primary_language,
        "framework": framework,
        "containerized": containerized,
        "has_ci": has_ci,
        "has_tests": has_tests,
        "database": database,
    }


def _get_primary_language(languages: dict) -> str:
    if not languages:
        return "unknown"
    return max(languages.items(), key=lambda x: x[1])[0]


def _detect_framework(file_tree: list) -> str:
    framework_indicators = {
        "requirements.txt": "Python",
        "package.json": "Node.js",
        "pom.xml": "Java",
        "cargo.toml": "Rust",
        "go.mod": "Go",
    }
    
    for indicator, framework in framework_indicators.items():
        if indicator in file_tree:
            return framework
    
    return "unknown"


def _has_containerization(file_tree: list) -> bool:
    return "dockerfile" in file_tree or "docker-compose.yml" in file_tree


def _has_ci_cd(file_tree: list) -> bool:
    ci_indicators = [".github", ".travis.yml", ".circleci"]
    return any(indicator in file_tree for indicator in ci_indicators)


def _has_tests(file_tree: list) -> bool:
    test_indicators = ["test", "tests", "spec"]
    return any(indicator in file_tree for indicator in test_indicators)


def _detect_database(file_tree: list) -> str:
    database_indicators = {
        "alembic": "PostgreSQL",
        "mongoose": "MongoDB",
        "prisma": "PostgreSQL",
    }
    
    for indicator, db in database_indicators.items():
        if indicator in file_tree:
            return db
    
    return "unknown"


def _analyze_activity(
    last_commit: str,
    contributors: list,
    stars: int,
    forks: int,
    open_issues: int,
) -> dict:
    days_since_commit = _calculate_days_since_commit(last_commit)
    is_active = days_since_commit < 90 if days_since_commit is not None else False
    
    return {
        "last_commit": last_commit,
        "days_since_commit": days_since_commit,
        "is_active": is_active,
        "contributor_count": len(contributors) if contributors else 0,
        "stars": stars,
        "forks": forks,
        "open_issues": open_issues,
    }


def _calculate_days_since_commit(last_commit: str) -> int | None:
    if not last_commit:
        return None
    
    try:
        commit_date = datetime.fromisoformat(last_commit.replace("Z", "+00:00"))
        today = datetime.now(commit_date.tzinfo)
        delta = today - commit_date
        return delta.days
    except (ValueError, TypeError):
        return None


def _calculate_health_score(
    repo_data: dict,
    activity: dict,
    tech_stack: dict,
) -> int:
    score = 0
    
    if tech_stack.get("has_tests"):
        score += 20
    
    if tech_stack.get("has_ci"):
        score += 20
    
    if activity.get("is_active"):
        score += 20
    
    if activity.get("stars", 0) > 100:
        score += 10
    
    if activity.get("forks", 0) > 10:
        score += 10
    
    if repo_data.get("license"):
        score += 10
    
    if activity.get("contributor_count", 0) > 1:
        score += 10
    
    return min(score, 100)


async def full_analysis(repo_url: str, use_cache: bool = True) -> dict:
    from core.fetcher import get_repo
    from core.llm import summarize_readme, detect_code_smells
    
    repo_data = await get_repo(repo_url, use_cache=use_cache)
    analysis = analyze_repo(repo_data)
    
    readme_summary, code_smells = await asyncio.gather(
        summarize_readme(repo_data.get("readme", "")),
        detect_code_smells(
            repo_data.get("file_tree", []),
            analysis.get("languages", {}),
            analysis.get("tech_stack", {}),
            analysis.get("activity", {}),
        ),
    )
    
    return {
        "meta": {
            "name": repo_data.get("name"),
            "full_name": repo_data.get("full_name"),
            "description": repo_data.get("description"),
            "url": repo_data.get("url"),
            "license": repo_data.get("license"),
            "default_branch": repo_data.get("default_branch"),
        },
        "languages": analysis.get("languages", {}),
        "tech_stack": analysis.get("tech_stack", {}),
        "activity": analysis.get("activity", {}),
        "health_score": analysis.get("health_score", 0),
        "readme_summary": readme_summary,
        "code_smells": code_smells,
    }


async def full_comparison(url1: str, url2: str, use_cache: bool = True) -> dict:
    from core.llm import compare_repos
    
    analysis_a, analysis_b = await asyncio.gather(
        full_analysis(url1, use_cache=use_cache),
        full_analysis(url2, use_cache=use_cache),
    )
    
    comparison = await compare_repos(analysis_a, analysis_b)
    
    return {
        "repo_a": analysis_a,
        "repo_b": analysis_b,
        "comparison": comparison,
    }
