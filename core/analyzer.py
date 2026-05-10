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
    framework = _detect_framework(file_tree_lower, languages)
    database = _detect_database(file_tree_lower, languages)
    ci_cd = _detect_ci_cd(file_tree_lower)
    containerization = _detect_containerization(file_tree_lower)
    package_manager = _detect_package_manager(file_tree_lower)
    has_tests = _has_tests(file_tree_lower)
    has_ci = ci_cd != "None detected"
    
    return {
        "language": primary_language,
        "framework": framework,
        "database": database,
        "ci_cd": ci_cd,
        "containerization": containerization,
        "package_manager": package_manager,
        "has_tests": has_tests,
        "has_ci": has_ci,
        "is_active": True,  # This is determined in activity analysis
    }


def _get_primary_language(languages: dict) -> str:
    if not languages:
        return "Unknown"
    return max(languages.items(), key=lambda x: x[1])[0]


def _detect_framework(file_tree: list, languages: dict) -> str:
    """
    Detect framework from file_tree and languages.
    file_tree is already lowercase.
    """
    languages_str = " ".join(languages.keys()).lower()
    
    # Django / FastAPI detection
    has_manage_py = "manage.py" in file_tree
    has_wsgi_py = "wsgi.py" in file_tree
    has_asgi_py = "asgi.py" in file_tree
    has_python_files = any(f in file_tree for f in ["manage.py", "wsgi.py", "asgi.py", "requirements.txt", "setup.py", "pyproject.toml"])
    
    if (has_manage_py or has_wsgi_py or has_asgi_py) and "python" in languages_str:
        return "FastAPI" if has_asgi_py else "Django"
    
    if any(f in file_tree for f in ["requirements.txt", "setup.py", "pyproject.toml"]) and "python" in languages_str:
        return "Python"
    
    # Node.js frameworks
    if "package.json" in file_tree:
        if any(f in file_tree for f in ["next.config.js", "next.config.ts"]):
            return "Next.js"
        if "nuxt.config.js" in file_tree:
            return "Nuxt.js"
        if "angular.json" in file_tree:
            return "Angular"
        if "vue.config.js" in file_tree:
            return "Vue.js"
        return "Node.js"
    
    # Java
    if any(f in file_tree for f in ["pom.xml", "build.gradle"]):
        return "Java/Spring"
    
    # Rust
    if "cargo.toml" in file_tree:
        return "Rust"
    
    # Go
    if "go.mod" in file_tree:
        return "Go"
    
    # PHP
    if "composer.json" in file_tree:
        if any("artisan" in f for f in file_tree):
            return "PHP/Laravel"
        return "PHP/Composer"
    
    # Elixir
    if "mix.exs" in file_tree:
        return "Elixir/Phoenix"
    
    # .NET
    if any(f.endswith(".csproj") for f in file_tree):
        return ".NET"
    
    return "Unknown"


def _detect_database(file_tree: list, languages: dict) -> str:
    """
    Detect database technology from file_tree and languages.
    Uses partial matching and is case-insensitive.
    """
    languages_lower = " ".join(languages.keys()).lower()
    file_tree_str = " ".join(file_tree).lower()
    
    # PostgreSQL / SQL
    if any(term in file_tree_str for term in ["alembic", "migrations", "migrate"]):
        return "PostgreSQL/SQL"
    
    if "prisma" in file_tree_str:
        return "PostgreSQL (Prisma)"
    
    if "sequelize" in file_tree_str:
        return "PostgreSQL/MySQL (Sequelize)"
    
    # MongoDB
    if any(term in file_tree_str for term in ["mongoose", "mongo"]):
        return "MongoDB"
    
    # Redis
    if any("redis" in f for f in file_tree):
        return "Redis"
    
    # Firebase
    if any("firebase" in f for f in file_tree):
        return "Firebase"
    
    # Supabase
    if any("supabase" in f for f in file_tree):
        return "Supabase"
    
    # DynamoDB
    if any("dynamo" in f for f in file_tree):
        return "DynamoDB"
    
    # SQLAlchemy / SQL
    if any(term in file_tree_str for term in ["sqlalchemy", "models.py"]):
        return "SQL (SQLAlchemy)"
    
    # PHP likely uses MySQL
    if "php" in languages_lower:
        return "MySQL (likely)"
    
    return "Not detected"


def _detect_ci_cd(file_tree: list) -> str:
    """
    Detect CI/CD platform from file_tree.
    Uses partial matching and is case-insensitive.
    Returns descriptive string.
    """
    file_tree_str = " ".join(file_tree).lower()
    
    # GitHub Actions
    if ".github" in file_tree:
        return "GitHub Actions"
    
    # Travis CI
    if ".travis.yml" in file_tree:
        return "Travis CI"
    
    # CircleCI
    if ".circleci" in file_tree:
        return "CircleCI"
    
    # Jenkins
    if "jenkinsfile" in file_tree_str:
        return "Jenkins"
    
    # GitLab CI
    if ".gitlab-ci.yml" in file_tree:
        return "GitLab CI"
    
    # Azure Pipelines
    if "azure-pipelines.yml" in file_tree:
        return "Azure Pipelines"
    
    # Bitbucket Pipelines
    if "bitbucket-pipelines.yml" in file_tree:
        return "Bitbucket Pipelines"
    
    # Drone CI
    if ".drone.yml" in file_tree:
        return "Drone CI"
    
    # Vercel
    if any(f in file_tree for f in ["vercel.json", ".vercel"]):
        return "Vercel"
    
    # Netlify
    if any(f in file_tree for f in ["netlify.toml", ".netlify"]):
        return "Netlify"
    
    return "None detected"


def _detect_containerization(file_tree: list) -> str:
    """
    Detect containerization technology from file_tree.
    Returns descriptive string instead of boolean.
    """
    file_tree_lower = [f.lower() for f in file_tree]
    file_tree_str = " ".join(file_tree_lower)
    
    has_dockerfile = any("dockerfile" in f for f in file_tree_lower)
    has_docker_compose = any("docker-compose" in f for f in file_tree_lower)
    has_dockerignore = ".dockerignore" in file_tree_lower
    has_kubernetes = any(term in file_tree_str for term in ["kubernetes", "k8s"])
    has_helm = any("helm" in f for f in file_tree_lower)
    
    if has_docker_compose and has_dockerfile:
        return "Docker + Compose"
    elif has_dockerfile or has_dockerignore:
        return "Docker"
    elif has_kubernetes:
        return "Kubernetes"
    elif has_helm:
        return "Helm"
    
    return "Not detected"


def _detect_package_manager(file_tree: list) -> str:
    """
    Detect package manager from file_tree.
    """
    # Python
    if "requirements.txt" in file_tree:
        return "pip"
    if any(f in file_tree for f in ["pyproject.toml", "poetry.lock"]):
        return "Poetry"
    if "pipfile" in file_tree:
        return "Pipenv"
    
    # JavaScript/Node.js
    if "package-lock.json" in file_tree:
        return "npm"
    if "yarn.lock" in file_tree:
        return "Yarn"
    if "pnpm-lock.yaml" in file_tree:
        return "pnpm"
    
    # Rust
    if "cargo.lock" in file_tree:
        return "Cargo"
    
    # Go
    if "go.sum" in file_tree:
        return "Go Modules"
    
    # Ruby
    if "gemfile" in file_tree:
        return "Bundler (Ruby)"
    
    return "Not detected"


def _has_tests(file_tree: list) -> bool:
    test_indicators = ["test", "tests", "spec"]
    return any(indicator in file_tree for indicator in test_indicators)


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
