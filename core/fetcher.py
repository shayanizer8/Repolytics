import httpx
import asyncio
import os
import base64
import json
from typing import Tuple, Dict, Any, List
from dotenv import load_dotenv

from core.cache import get_cached, set_cached

# Load environment variables
load_dotenv()


# Custom exceptions
class GitHubAPIError(Exception):
    """Base exception for GitHub API errors"""
    pass


class RepoNotFoundError(GitHubAPIError):
    """Raised when a repository is not found (404)"""
    pass


class RateLimitedError(GitHubAPIError):
    """Raised when rate limited (403)"""
    pass


def parse_github_url(repo_url: str) -> Tuple[str, str]:
    """
    Parse GitHub URL and extract owner and repo name.
    
    Handles formats like:
    - https://github.com/owner/repo
    - github.com/owner/repo
    - http://github.com/owner/repo
    
    Args:
        repo_url: GitHub repository URL
    
    Returns:
        Tuple of (owner, repo)
    
    Raises:
        ValueError: If URL format is invalid
    """
    # Remove protocol and www
    url = repo_url.replace("https://", "").replace("http://", "").replace("www.", "")
    # Remove trailing slash and .git suffix
    url = url.rstrip("/").replace(".git", "")
    
    # Extract path after github.com/
    if "github.com/" in url:
        path = url.split("github.com/")[1]
    else:
        # Assume it's already in owner/repo format
        path = url
    
    # Split and get owner and repo
    parts = path.split("/")
    if len(parts) < 2:
        raise ValueError(f"Invalid GitHub URL format: {repo_url}")
    
    owner, repo = parts[0], parts[1]
    
    if not owner or not repo:
        raise ValueError(f"Invalid GitHub URL format: {repo_url}")
    
    return owner, repo


async def _fetch_with_retry(
    client: httpx.AsyncClient,
    url: str,
    max_retries: int = 3,
    initial_delay: float = 1.0,
) -> httpx.Response:
    """
    Fetch from URL with exponential backoff retry on 429 or 5xx.
    
    Args:
        client: httpx.AsyncClient instance
        url: URL to fetch
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay for exponential backoff (in seconds)
    
    Returns:
        Response object
    
    Raises:
        RepoNotFoundError: If repository not found (404)
        RateLimitedError: If rate limited (403)
        GitHubAPIError: On other API errors
    """
    delay = initial_delay
    
    for attempt in range(max_retries):
        response = await client.get(url)
        
        # Handle specific error codes that shouldn't retry
        if response.status_code == 404:
            raise RepoNotFoundError(f"Repository not found: {url}")
        elif response.status_code == 403:
            raise RateLimitedError(f"Rate limited or forbidden: {url}")
        
        # Check if we should retry (429 Too Many Requests or 5xx Server Errors)
        if response.status_code == 429 or response.status_code >= 500:
            if attempt < max_retries - 1:
                await asyncio.sleep(delay)
                delay *= 2  # Exponential backoff
                continue
        
        # For all other cases, ensure success and return
        response.raise_for_status()
        return response
    
    # If we exhausted retries, raise error from last attempt
    response.raise_for_status()
    return response


async def _fetch_subdirectory_contents(
    client: httpx.AsyncClient,
    base_url: str,
    subfolder: str,
) -> List[str]:
    """
    Fetch contents of a subdirectory and return as "{subfolder}/{filename}" list.
    Returns empty list on 404 or any other error (silently handles missing dirs).
    """
    try:
        url = f"{base_url}/contents/{subfolder}"
        response = await client.get(url)
        
        if response.status_code == 404:
            # Subdirectory doesn't exist — this is normal
            return []
        
        if response.status_code >= 400:
            # Other errors — silently skip
            return []
        
        data = response.json()
        if isinstance(data, list):
            return [f"{subfolder}/{item.get('name')}" for item in data if item.get("name")]
        else:
            # Single file response
            return [f"{subfolder}/{data.get('name')}"]
    except Exception:
        # Any error — just return empty list
        return []


async def _fetch_file_content(
    client: httpx.AsyncClient,
    base_url: str,
    file_path: str,
) -> str | None:
    """
    Fetch content of a specific file (like package.json).
    Returns decoded content or None on error.
    """
    try:
        url = f"{base_url}/contents/{file_path}"
        response = await client.get(url)
        
        if response.status_code != 200:
            return None
        
        data = response.json()
        if data.get("encoding") == "base64":
            content = data.get("content", "")
            return base64.b64decode(content).decode("utf-8")
        return data.get("content", "")
    except Exception:
        return None


async def fetch_repo(repo_url: str) -> Dict[str, Any]:
    """
    Fetch comprehensive data from a GitHub repository.
    
    Makes concurrent API calls to gather:
    - Repository metadata
    - Language breakdown
    - Top contributors
    - Root file tree
    - README content
    
    Args:
        repo_url: GitHub repository URL (e.g., https://github.com/owner/repo)
    
    Returns:
        Dictionary with keys:
        - name, full_name, description, stars, forks, open_issues
        - license, last_commit, default_branch, languages, contributors
        - file_tree (list of filenames), readme (raw text), url
    
    Raises:
        RepoNotFoundError: If repository not found (404)
        RateLimitedError: If rate limited (403)
        GitHubAPIError: On other API errors
        ValueError: If URL format is invalid or GITHUB_TOKEN not set
    """
    # Parse URL to get owner and repo
    owner, repo = parse_github_url(repo_url)
    print(f"DEBUG - Owner: {owner}, Repo: {repo}")
    
    # Get GitHub token from environment
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise ValueError("GITHUB_TOKEN environment variable not set")
    
    # Set up headers with authentication
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    
    # Base URL for API calls
    base_url = f"https://api.github.com/repos/{owner}/{repo}"
    print(f"DEBUG - API URL: {base_url}")
    
    async with httpx.AsyncClient(headers=headers, timeout=30.0, follow_redirects=True) as client:
        # STEP 1: Fetch and verify main repo metadata first
        # If this returns 404, the repo truly doesn't exist
        repo_response = await _fetch_with_retry(client, f"{base_url}")
        repo_json = repo_response.json()
        
        # STEP 2: Fetch other required data concurrently (safe calls)
        tasks = [
            _fetch_with_retry(client, f"{base_url}/languages"),  # Languages
            _fetch_with_retry(client, f"{base_url}/contributors?per_page=5"),  # Top contributors
            _fetch_with_retry(client, f"{base_url}/contents"),  # Root file tree
        ]
        
        responses = await asyncio.gather(*tasks)
        languages_response, contributors_response, tree_response = responses
        
        # Parse languages
        languages = languages_response.json()
        
        # Parse contributors
        contributors_data = contributors_response.json()
        contributors_list: List[Dict[str, Any]] = []
        if isinstance(contributors_data, list):
            contributors_list = [
                {
                    "login": c.get("login"),
                    "contributions": c.get("contributions"),
                    "avatar": c.get("avatar_url"),
                }
                for c in contributors_data
            ]
        
        # Parse file tree
        tree_data = tree_response.json()
        file_tree: List[str] = []
        if isinstance(tree_data, list):
            file_tree = [item.get("name") for item in tree_data if item.get("name")]
        
        # STEP 2B: Fetch subdirectories to find Dockerfiles and other config files
        subfolders_to_check = [
            "scripts", "docker", "containers", "deploy", "deployment",
            "devops", "infra", "infrastructure", ".github", "config",
            "backend", "frontend", "server", "client", "src", "app",
            "worker", "workers", "tests", "__tests__", "configs",
            "environments", "helm", "terraform", "ansible", "kubernetes",
            "api", "models", "routes", "controllers", "services", "middleware",
            "schemas", "db", "database", "lib", "utils", "helpers",
            "components", "pages", "hooks", "context", "store", "redux",
            "public", "static", "assets", "styles", "css", "images",
            "core", "shared", "common", "packages", "packages/server",
            "packages/client", "apps", "apps/server", "apps/client",
            "functions", "lambda", "src/api", "src/backend", "src/frontend",
            "src/db", "data", "storage", "migrations", "seeds",
        ]
        
        # Only fetch subdirectories that exist in root file_tree
        subfolders_to_fetch = [
            sf for sf in subfolders_to_check 
            if any(sf.lower() == name.lower() for name in file_tree)
        ]
        
        # Fetch all subdirectories concurrently
        if subfolders_to_fetch:
            subfolder_tasks = [
                _fetch_subdirectory_contents(client, base_url, sf)
                for sf in subfolders_to_fetch
            ]
            subfolder_results = await asyncio.gather(*subfolder_tasks)
            
            # Extend file_tree with subdirectory contents
            for subfolder_files in subfolder_results:
                file_tree.extend(subfolder_files)
        
        # STEP 2C: Fetch package.json from root and any subdirectories we fetched
        # First, look for any package.json in the file_tree (from subdirectories we fetched)
        package_json_paths = ["package.json"]
        
        # Also add package.json from any subdirectory that appears in file_tree
        for f in file_tree:
            if "package.json" in f.lower():
                package_json_paths.append(f)
        
        # Also check the predefined subfolders (in case we missed any)
        for sf in subfolders_to_check:
            pkg_path = f"{sf}/package.json"
            if pkg_path not in package_json_paths:
                package_json_paths.append(pkg_path)
        
        # Deduplicate paths
        package_json_paths = list(set(package_json_paths))
        
        package_json_tasks = [
            _fetch_file_content(client, base_url, path)
            for path in package_json_paths
        ]
        package_json_results = await asyncio.gather(*package_json_tasks)
        
        # Store all package.json contents for analysis
        package_json_contents = {}
        for path, content in zip(package_json_paths, package_json_results):
            if content:
                try:
                    pkg_data = json.loads(content)
                    package_json_contents[path] = pkg_data
                except:
                    pass
        
        # STEP 3: Fetch README separately with graceful 404 handling
        # A 404 on README is normal and expected (not all repos have a README)
        readme_text = ""
        try:
            readme_response = await client.get(f"{base_url}/readme")
            if readme_response.status_code == 404:
                # No README file exists — this is normal
                readme_text = ""
            elif readme_response.status_code >= 400:
                # Other errors are still errors, but README is optional
                readme_text = ""
            else:
                # Successfully got README
                readme_json = readme_response.json()
                if readme_json.get("encoding") == "base64":
                    readme_content = readme_json.get("content", "")
                    readme_text = base64.b64decode(readme_content).decode("utf-8")
                else:
                    readme_text = readme_json.get("content", "")
        except Exception as e:
            # README fetch failed for any reason — just leave it empty
            readme_text = ""
        
        # Construct and return result dictionary
        return {
            "name": repo_json.get("name"),
            "full_name": repo_json.get("full_name"),
            "description": repo_json.get("description"),
            "stars": repo_json.get("stargazers_count"),
            "forks": repo_json.get("forks_count"),
            "open_issues": repo_json.get("open_issues_count"),
            "license": repo_json.get("license", {}).get("name") if repo_json.get("license") else None,
            "last_commit": repo_json.get("pushed_at"),
            "default_branch": repo_json.get("default_branch"),
            "languages": languages,
            "contributors": contributors_list,
            "file_tree": file_tree,
            "readme": readme_text,
            "url": repo_json.get("html_url"),
            "package_json": package_json_contents,
        }


async def get_repo(repo_url: str, use_cache: bool = True) -> Dict[str, Any]:
    """
    Fetch repository data with optional caching
    
    If use_cache is True:
    - Attempts to retrieve from Redis cache first
    - Falls back to fetch_repo() on cache miss
    - Stores result in cache after fetching
    
    If use_cache is False:
    - Skips cache read
    - Still stores result in cache after fetching
    
    Args:
        repo_url: GitHub repository URL
        use_cache: Whether to use caching (default True)
    
    Returns:
        Dictionary with repository data
    
    Raises:
        RepoNotFoundError: If repository not found (404)
        RateLimitedError: If rate limited (403)
        GitHubAPIError: On other API errors
        ValueError: If URL format is invalid or GITHUB_TOKEN not set
    """
    # Try to get from cache if enabled
    if use_cache:
        cached_data = await get_cached(repo_url)
        if cached_data is not None:
            return cached_data
    
    # Cache miss or caching disabled — fetch fresh data
    data = await fetch_repo(repo_url)
    
    # Store in cache for future requests
    await set_cached(repo_url, data)
    
    return data
