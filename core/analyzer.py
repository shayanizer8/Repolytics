import asyncio
from datetime import datetime
from typing import Dict, Any


def analyze_repo(repo_data: dict) -> dict:
    languages = _analyze_languages(repo_data.get("languages", {}))
    tech_stack = _analyze_tech_stack(
        repo_data.get("file_tree", []),
        repo_data.get("languages", {}),
        repo_data.get("package_json"),
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


def _analyze_tech_stack(file_tree: list, languages: dict, package_json: dict = None) -> dict:
    """
    Static analysis of tech stack - fast and reliable for obvious signals.
    LLM-based inference happens in full_analysis() for deeper insights.
    """
    if package_json is None:
        package_json = {}
    
    file_tree_lower = [f.lower() for f in file_tree]
    file_tree_str = " ".join(file_tree_lower)
    
    primary_language = _get_primary_language(languages)
    has_tests = _has_tests(file_tree_lower)
    has_ci = _has_ci_basic(file_tree_lower)
    containerized = _detect_containerization_basic(file_tree_lower)
    package_manager = _detect_package_manager(file_tree_lower)
    framework = _detect_framework(file_tree_lower, languages, package_json)
    database = _detect_database(file_tree, languages, package_json)
    ci_cd = _detect_ci_cd_patterns(file_tree_lower)
    containerization = _detect_containerization_patterns(file_tree_lower)
    
    # Get all languages as a formatted string
    all_languages = _get_all_languages(languages)
    
    return {
        "language": primary_language,
        "languages": all_languages,
        "has_tests": has_tests,
        "has_ci": has_ci,
        "containerized": containerized,
        "containerization": containerization,
        "package_manager": package_manager,
        "framework": framework,
        "database": database,
        "ci_cd": ci_cd,
    }


def _get_all_languages(languages: dict) -> str:
    """Get all language names as a comma-separated string."""
    if not languages:
        return "Unknown"
    
    langs = [lang for lang in sorted(languages.keys())]
    return ", ".join(langs)


def _get_primary_language(languages: dict) -> str:
    if not languages:
        return "Unknown"
    return max(languages.items(), key=lambda x: x[1])[0]


def _has_ci_basic(file_tree: list) -> bool:
    """Basic CI/CD detection - just check for presence."""
    ci_indicators = [".github", ".travis.yml", ".circleci", "jenkinsfile", 
                     ".gitlab-ci.yml", "azure-pipelines.yml", 
                     "bitbucket-pipelines.yml", ".drone.yml"]
    file_tree_lower = [f.lower() for f in file_tree]
    return any(indicator in file_tree_lower for indicator in ci_indicators)


def _detect_containerization_basic(file_tree: list) -> bool:
    """Basic containerization detection - just check for presence."""
    file_tree_lower = [f.lower() for f in file_tree]
    return any("dockerfile" in f or "docker-compose" in f for f in file_tree_lower)


def _detect_package_manager(file_tree: list) -> str:
    """Detect package manager from lock/manifest files."""
    file_tree_set = set(file_tree)
    file_tree_lower = [f.lower() for f in file_tree]
    
    # Python - check both root and subdirectories
    if any("requirements.txt" in f for f in file_tree):
        return "pip"
    if any("poetry.lock" in f or "pyproject.toml" in f for f in file_tree):
        return "Poetry"
    if any("pipfile" in f for f in file_tree):
        return "Pipenv"
    if any("setup.py" in f or "setup.cfg" in f for f in file_tree):
        return "setuptools"
    
    # JavaScript/Node.js - check both root and subdirectories
    if any("package.json" in f for f in file_tree):
        if any("pnpm-lock.yaml" in f for f in file_tree):
            return "pnpm"
        if any("yarn.lock" in f for f in file_tree):
            return "Yarn"
        if any("package-lock.json" in f for f in file_tree):
            return "npm"
        # If we found package.json but no lock file, default to npm
        return "npm"
    
    # Rust
    if any("cargo.lock" in f for f in file_tree):
        return "Cargo"
    
    # Go
    if any("go.mod" in f for f in file_tree):
        return "Go Modules"
    if any("go.sum" in f for f in file_tree):
        return "Go Modules"
    
    # Ruby
    if any("gemfile" in f.lower() for f in file_tree):
        return "Bundler (Ruby)"
    
    # PHP/Composer
    if any("composer.json" in f or "composer.lock" in f for f in file_tree):
        return "Composer"
    
    # .NET/NuGet
    if any(".csproj" in f or ".nuspec" in f for f in file_tree):
        return "NuGet"
    
    return "Not detected"


def _detect_framework(file_tree_lower: list, languages: dict, package_json: dict = None) -> str | None:
    """Detect web/app framework from package.json dependencies and file patterns."""
    if package_json is None:
        package_json = {}
    
    # Gather all dependencies from all package.json files
    all_deps = {}
    for path, pkg in package_json.items():
        deps = pkg.get("dependencies", {})
        dev_deps = pkg.get("devDependencies", {})
        all_deps.update(deps)
        all_deps.update(dev_deps)
    
    deps_str = " ".join(all_deps.keys()).lower()
    file_tree_str = " ".join(file_tree_lower)
    file_tree_str_no_slash = file_tree_str.replace("/", " ").replace("\\", " ")
    
    # Check package.json for clear indicators
    has_express = "express" in all_deps
    has_react = "react" in all_deps
    has_next = "next" in all_deps
    has_vite = "vite" in all_deps
    has_nuxt = "nuxt" in all_deps
    has_gatsby = "gatsby" in all_deps
    has_angular = "@angular/core" in all_deps or "angular" in all_deps
    has_vue = "vue" in all_deps
    has_django = "django" in all_deps
    has_flask = "flask" in all_deps
    has_fastapi = "fastapi" in all_deps
    
    # MERN Stack detection - needs both frontend (React) and backend (Express)
    if has_react and has_express:
        return "MERN Stack"
    
    # Full-stack frameworks
    if has_next:
        return "Next.js"
    if has_nuxt:
        return "Nuxt"
    if has_gatsby:
        return "Gatsby"
    
    # Frontend only
    if has_vite and has_vue:
        return "Vue.js + Vite"
    if has_vite and has_react:
        return "React + Vite"
    if has_vite:
        return "Vite"
    if has_angular:
        return "Angular"
    if has_vue:
        return "Vue.js"
    if has_react:
        return "React"
    
    # Python frameworks
    if has_django or "manage.py" in file_tree_lower:
        return "Django"
    if has_flask:
        return "Flask"
    if has_fastapi:
        return "FastAPI"
    
    # Node/Express backend only
    if has_express:
        return "Express"
    
    # Fallback to file pattern detection
    # JavaScript/TypeScript frameworks - check for backend first (Express/Node)
    has_express_file = "express" in file_tree_str_no_slash or "server.js" in file_tree_lower or "app.js" in file_tree_lower
    has_node = "node_modules" in file_tree_str or "server" in file_tree_lower or "routes" in file_tree_lower or "controllers" in file_tree_lower
    has_api_folder = "api" in file_tree_lower
    has_models_folder = "models" in file_tree_lower
    
    # MERN stack detection - both frontend and backend
    is_mern = False
    if ("react" in languages or "javascript" in languages or "typescript" in languages):
        if has_express_file or has_node or "server" in file_tree_lower or "backend" in file_tree_lower or has_api_folder or has_models_folder:
            is_mern = True
    
    if is_mern:
        return "MERN Stack"
    
    # Other JS frameworks
    if "next.config" in file_tree_str_no_slash or ("pages" in file_tree_lower and "app" in file_tree_lower):
        return "Next.js"
    if "nuxt.config" in file_tree_str_no_slash:
        return "Nuxt"
    if "gatsby-config" in file_tree_str_no_slash:
        return "Gatsby"
    if "vite.config" in file_tree_str_no_slash or "vite.config.js" in file_tree_lower:
        return "Vite"
    if "webpack.config" in file_tree_str_no_slash:
        return "Webpack"
    if "angular.json" in file_tree_str_no_slash:
        return "Angular"
    if "vue.config" in file_tree_str_no_slash:
        return "Vue.js"
    
    # React specific (if no other match)
    if "react" in languages or "jsx" in file_tree_str or "tsx" in file_tree_str:
        if "next" not in file_tree_str_no_slash and "nuxt" not in file_tree_str_no_slash:
            return "React"
    
    # Node.js/Express backend only
    if has_express_file:
        return "Express"
    
    # Vue with Vite
    if "vue" in languages and "vite" in file_tree_str_no_slash:
        return "Vue.js + Vite"
    
    return None
    
    # Java/Spring
    if "application.properties" in file_tree_str or "application.yml" in file_tree_str:
        if "spring" in file_tree_str:
            return "Spring Boot"
    
    # Go frameworks
    if "go.mod" in file_tree_str:
        if "gin" in file_tree_str:
            return "Gin"
        if "echo" in file_tree_str:
            return "Echo"
        if "fiber" in file_tree_str:
            return "Fiber"
    
    # Rust frameworks
    if "cargo.toml" in file_tree_str:
        if "actix" in file_tree_str:
            return "Actix"
        if "rocket" in file_tree_str:
            return "Rocket"
        if "axum" in file_tree_str:
            return "Axum"
    
    # PHP frameworks
    if "artisan" in file_tree_str:
        return "Laravel"
    if "composer.json" in file_tree_str:
        if "symfony" in file_tree_str or "symfony.lock" in file_tree_str:
            return "Symfony"
    
    return None


def _detect_database(file_tree: list, languages: dict = None, package_json: dict = None) -> str | None:
    """Detect database from package.json dependencies and file patterns."""
    if languages is None:
        languages = {}
    if package_json is None:
        package_json = {}
    
    # Gather all dependencies from all package.json files
    all_deps = {}
    for path, pkg in package_json.items():
        deps = pkg.get("dependencies", {})
        dev_deps = pkg.get("devDependencies", {})
        all_deps.update(deps)
        all_deps.update(dev_deps)
    
    file_tree_str = " ".join(file_tree).lower()
    file_tree_lower = [f.lower() for f in file_tree]
    
    databases = []
    
    # Check package.json dependencies FIRST (most reliable)
    dep_keys_lower = " ".join(all_deps.keys()).lower()
    
    if "mongoose" in all_deps or "mongodb" in all_deps:
        databases.append("MongoDB")
    if "pg" in all_deps or "pg-pool" in all_deps or "postgres" in all_deps or "pg-native" in all_deps:
        databases.append("PostgreSQL")
    if "mysql2" in all_deps or "mysql" in all_deps or "mariadb" in all_deps:
        databases.append("MySQL")
    if "better-sqlite3" in all_deps or "sqlite3" in all_deps or "sql.js" in all_deps:
        databases.append("SQLite")
    if "redis" in all_deps or "ioredis" in all_deps:
        databases.append("Redis")
    if "@prisma/client" in all_deps or "prisma" in all_deps:
        databases.append("PostgreSQL/MySQL/SQLite (via Prisma)")
    if "sequelize" in all_deps:
        databases.append("MySQL/PostgreSQL/SQLite (via Sequelize)")
    if "typeorm" in all_deps:
        databases.append("TypeORM (multiple DBs)")
    if "firebase" in all_deps or "@firebase/firestore" in all_deps:
        databases.append("Firebase Firestore")
    if "@aws-sdk/client-dynamodb" in all_deps or "dynamodb" in all_deps:
        databases.append("DynamoDB")
    if "cassandra-driver" in all_deps:
        databases.append("Cassandra")
    if "elasticsearch" in all_deps or "@elastic/elasticsearch" in all_deps:
        databases.append("Elasticsearch")
    if "knex" in all_deps:
        databases.append("PostgreSQL/MySQL/SQLite (via Knex)")
    if "bookshelf" in all_deps:
        databases.append("PostgreSQL/MySQL (via Bookshelf)")
    
    # Also check file tree for database files/patterns
    db_patterns = {
        "mongodb": "MongoDB",
        "mongoose": "MongoDB",
        "mongo": "MongoDB",
        "postgres": "PostgreSQL",
        "postgresql": "PostgreSQL",
        "mysql": "MySQL",
        "mariadb": "MariaDB",
        "sqlite": "SQLite",
        "redis": "Redis",
        "prisma": "PostgreSQL/MySQL/SQLite (via Prisma)",
        "sequelize": "MySQL/PostgreSQL/SQLite (via Sequelize)",
        "typeorm": "TypeORM (multiple DBs)",
        "dynamodb": "DynamoDB",
        "elasticsearch": "Elasticsearch",
        "cassandra": "Cassandra",
        "firebase": "Firebase Firestore",
        "firestore": "Firebase Firestore",
        "knex": "PostgreSQL/MySQL/SQLite (via Knex)",
    }
    
    for pattern, db_name in db_patterns.items():
        if pattern in file_tree_str:
            if db_name not in databases:
                databases.append(db_name)
    
    # Check for .env files that often contain database URLs
    env_files = [f for f in file_tree_lower if ".env" in f]
    for env_file in env_files:
        # This will be detected via package.json or file patterns
        # .env files themselves are not fetched, but the presence is a hint
        if "database" in env_file or "db" in env_file:
            if "MongoDB" not in databases:
                databases.append("MongoDB (inferred from .env)")
    
    # Check for database config files and folders
    db_config_patterns = ["database.js", "database.ts", "db.js", "db.ts", "connection.js", "config/database"]
    for pattern in db_config_patterns:
        if pattern in file_tree_lower:
            if "MongoDB" not in databases:
                databases.append("MongoDB (inferred from config)")
    
    # Check for common database folder patterns
    db_folders = ["models", "schemas", "db", "database", "migrations", "seeds"]
    for folder in db_folders:
        if any(folder in f.lower() for f in file_tree):
            # Try to infer which database based on other indicators
            if "mongo" in file_tree_str or "mongoose" in file_tree_str:
                if "MongoDB" not in databases:
                    databases.append("MongoDB")
            elif "postgres" in file_tree_str or "postgresql" in file_tree_str:
                if "PostgreSQL" not in databases:
                    databases.append("PostgreSQL")
    
    if len(databases) > 0:
        # Deduplicate while preserving order
        seen = set()
        unique_dbs = []
        for db in databases:
            if db not in seen:
                seen.add(db)
                unique_dbs.append(db)
        return "+".join(unique_dbs)
    
    return None


def _has_tests(file_tree: list) -> bool:
    test_indicators = ["test", "tests", "spec"]
    file_tree_lower = [f.lower() for f in file_tree]
    return any(indicator in f for f in file_tree_lower for indicator in test_indicators)


def _get_dependency_files(file_tree: list) -> Dict[str, str]:
    """
    Return a dict of dependency file contents for LLM analysis.
    Each file is truncated to 1000 chars.
    Returns empty dict if files not found.
    """
    # This will be populated in full_analysis() with actual file contents
    # For now, return empty dict as placeholder
    return {}


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
    file_tree = repo_data.get("file_tree", [])
    file_tree_str = " ".join(file_tree).lower()
    
    project_type = _detect_project_type(file_tree, tech_stack)
    project_maturity = _detect_project_maturity(activity, repo_data)
    
    weights = _get_scoring_weights(project_type, project_maturity)
    
    score = 0
    
    # Tests - but don't penalize documentation repos
    if project_type != "documentation":
        if tech_stack.get("has_tests"):
            score += weights["tests"]
        elif weights["tests"] > 15:
            score += weights["tests"] // 2
    
    # CI/CD - important for apps, less for small libs
    if tech_stack.get("has_ci"):
        score += weights["ci_cd"]
    elif project_type == "application" and weights["ci_cd"] > 10:
        score += weights["ci_cd"] // 2
    
    # Activity - adjust threshold based on maturity
    is_active = activity.get("is_active", False)
    if project_maturity == "mature":
        score += weights["activity"] if is_active else weights["activity"] // 2
    elif project_maturity == "stable":
        score += weights["activity"] // 2 if is_active else 0
    else:
        score += weights["activity"] if is_active else 0
    
    # Stars - lower threshold for small libraries
    stars = activity.get("stars", 0)
    if project_type == "library":
        threshold = 10
    elif project_type == "documentation":
        threshold = 5
    else:
        threshold = 50
    if stars >= threshold:
        score += weights["stars"]
    elif stars >= threshold // 2:
        score += weights["stars"] // 2
    
    # Forks - important for libraries
    forks = activity.get("forks", 0)
    if project_type == "library":
        threshold = 5
    else:
        threshold = 10
    if forks >= threshold:
        score += weights["forks"]
    
    # License - check if it exists (only important for libraries/public repos)
    if repo_data.get("license") and project_type == "library":
        score += weights["license"]
    
    # Contributors - adjust based on project type
    contributors = activity.get("contributor_count", 0)
    if project_type == "library":
        threshold = 1
    elif project_type == "documentation":
        threshold = 1
    else:
        threshold = 2
    if contributors > threshold:
        score += weights["contributors"]
    elif contributors > threshold:
        score += weights["contributors"] // 2
    
    # Documentation bonus for libraries
    if project_type == "library":
        readme = repo_data.get("readme", "")
        if readme and len(readme) > 500:
            score += 5
    
    return min(score, 100)


def _detect_project_type(file_tree: list, tech_stack: dict) -> str:
    """Detect the type of project (library, application, documentation, etc.)"""
    file_tree_str = " ".join(file_tree).lower()
    
    # Check for application indicators (deployment, docker, etc.)
    app_indicators = ["dockerfile", "docker-compose", "kubernetes", ".github/workflows", 
                      "jenkinsfile", "deploy", "deployment", "terraform", "helm"]
    if any(ind in file_tree_str for ind in app_indicators):
        return "application"
    
    # Check for library indicators (package.json at root, setup.py, etc.)
    lib_indicators = ["package.json", "setup.py", "cargo.toml", "composer.json", 
                      "gemfile", "pyproject.toml", "requirements.txt"]
    if any(ind in file_tree_str for ind in lib_indicators):
        return "library"
    
    # Check for documentation indicators
    doc_indicators = ["readme", "docs/", "documentation/", ".md"]
    doc_count = sum(1 for ind in doc_indicators if ind in file_tree_str)
    if doc_count >= 2 and len(file_tree) < 20:
        return "documentation"
    
    # Check for CLI tool
    if "cli" in file_tree_str or "bin/" in file_tree_str or "cmd/" in file_tree_str:
        return "cli"
    
    return "application"


def _detect_project_maturity(activity: dict, repo_data: dict) -> str:
    """Detect project maturity (new, mature, stable)"""
    stars = activity.get("stars", 0)
    forks = activity.get("forks", 0)
    days_since = activity.get("days_since_commit")
    
    # High engagement = mature
    if stars > 1000 or forks > 100:
        return "mature"
    
    # Recent with low engagement = new
    if stars < 50 and forks < 10:
        if days_since is not None and days_since < 30:
            return "new"
        elif days_since is not None and days_since > 180:
            return "stable"
        return "new"
    
    # Otherwise = growing
    return "growing"


def _get_scoring_weights(project_type: str, maturity: str) -> dict:
    """Get scoring weights based on project type and maturity"""
    
    base_weights = {
        "library": {
            "tests": 15,
            "ci_cd": 10,
            "activity": 15,
            "stars": 15,
            "forks": 15,
            "license": 15,
            "contributors": 15,
        },
        "application": {
            "tests": 25,
            "ci_cd": 25,
            "activity": 20,
            "stars": 10,
            "forks": 5,
            "license": 5,
            "contributors": 10,
        },
        "documentation": {
            "tests": 5,
            "ci_cd": 10,
            "activity": 20,
            "stars": 20,
            "forks": 15,
            "license": 10,
            "contributors": 20,
        },
        "cli": {
            "tests": 20,
            "ci_cd": 20,
            "activity": 20,
            "stars": 15,
            "forks": 10,
            "license": 5,
            "contributors": 10,
        },
    }
    
    weights = base_weights.get(project_type, base_weights["application"])
    
    # Adjust for mature projects - less emphasis on activity
    if maturity == "mature":
        weights["activity"] = weights["activity"] // 2
        weights["stars"] = weights["stars"] + 5
        weights["forks"] = weights["forks"] + 5
    
    # Adjust for stable projects - less emphasis on everything
    elif maturity == "stable":
        weights["activity"] = 5
        weights["tests"] = weights["tests"] + 5
    
    return weights


def _detect_ci_cd_patterns(file_tree: list) -> str | None:
    """
    Detect CI/CD from file patterns.
    """
    file_tree_lower = [f.lower() for f in file_tree]
    file_tree_str = " ".join(file_tree_lower)
    
    if ".github" in file_tree_lower:
        return "GitHub Actions"
    if ".github/workflows" in file_tree_lower:
        return "GitHub Actions"
    if ".travis.yml" in file_tree_lower:
        return "Travis CI"
    if ".circleci" in file_tree_lower:
        return "CircleCI"
    if any("jenkinsfile" in f for f in file_tree_lower):
        return "Jenkins"
    if ".gitlab-ci.yml" in file_tree_lower:
        return "GitLab CI"
    if "azure-pipelines.yml" in file_tree_lower:
        return "Azure Pipelines"
    if "bitbucket-pipelines.yml" in file_tree_lower:
        return "Bitbucket Pipelines"
    if ".drone.yml" in file_tree_lower:
        return "Drone"
    
    return None


def _detect_containerization_patterns(file_tree: list) -> str | None:
    """
    Detect containerization from file patterns.
    """
    file_tree_lower = [f.lower() for f in file_tree]
    file_tree_str = " ".join(file_tree_lower)
    
    has_dockerfile = any("dockerfile" in f for f in file_tree_lower)
    has_docker_compose = any("docker-compose" in f for f in file_tree_lower)
    has_dockerignore = ".dockerignore" in file_tree_lower
    has_kubernetes = any(term in file_tree_str for term in ["kubernetes", "k8s"])
    
    if has_docker_compose and has_dockerfile:
        return "Docker + Compose"
    elif has_dockerfile or has_dockerignore:
        return "Docker"
    elif has_kubernetes:
        return "Kubernetes"
    
    return None


async def full_analysis(repo_url: str, use_cache: bool = True) -> dict:
    from core.fetcher import get_repo
    from core.llm import summarize_readme, detect_code_smells, infer_tech_stack
    
    repo_data = await get_repo(repo_url, use_cache=use_cache)
    analysis = analyze_repo(repo_data)
    
    # Get static analysis tech stack (already has framework, database, ci_cd, containerization)
    tech_stack = analysis.get("tech_stack", {})
    
    # Call LLM functions concurrently
    readme_summary, code_smells, llm_tech_stack = await asyncio.gather(
        summarize_readme(repo_data.get("readme", "")),
        detect_code_smells(
            repo_data.get("file_tree", []),
            analysis.get("languages", {}),
            tech_stack,
            analysis.get("activity", {}),
        ),
        infer_tech_stack(
            repo_data.get("file_tree", []),
            repo_data.get("languages", {}),
        ),
    )
    
    # Only use LLM values if static analysis didn't detect them
    # This ensures static analysis takes precedence for detected values
    if not tech_stack.get("framework") and llm_tech_stack.get("framework"):
        tech_stack["framework"] = llm_tech_stack["framework"]
    
    if not tech_stack.get("database") and llm_tech_stack.get("database"):
        tech_stack["database"] = llm_tech_stack["database"]
    
    # For ci_cd and containerization, use static analysis if LLM returned null or same as has_ci/has_containerized
    if not tech_stack.get("ci_cd") and llm_tech_stack.get("ci_cd"):
        tech_stack["ci_cd"] = llm_tech_stack["ci_cd"]
    elif not tech_stack.get("ci_cd") and tech_stack.get("has_ci"):
        detected_ci_cd = _detect_ci_cd_patterns(repo_data.get("file_tree", []))
        tech_stack["ci_cd"] = detected_ci_cd if detected_ci_cd else "GitHub Actions"
    
    if not tech_stack.get("containerization") and llm_tech_stack.get("containerization"):
        tech_stack["containerization"] = llm_tech_stack["containerization"]
    elif not tech_stack.get("containerization") and tech_stack.get("containerized"):
        detected_containerization = _detect_containerization_patterns(repo_data.get("file_tree", []))
        tech_stack["containerization"] = detected_containerization if detected_containerization else "Docker"
    
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
        "tech_stack": tech_stack,
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
