import httpx
import asyncio
import os
import base64
from typing import Tuple, Dict, Any, List
from dotenv import load_dotenv

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
    
    async with httpx.AsyncClient(headers=headers, timeout=30.0) as client:
        # Define all the API calls as tasks
        tasks = [
            _fetch_with_retry(client, f"{base_url}"),  # Main repo metadata
            _fetch_with_retry(client, f"{base_url}/languages"),  # Languages
            _fetch_with_retry(client, f"{base_url}/contributors?per_page=5"),  # Top contributors
            _fetch_with_retry(client, f"{base_url}/contents"),  # Root file tree
            _fetch_with_retry(client, f"{base_url}/readme"),  # README
        ]
        
        # Execute all requests concurrently
        responses = await asyncio.gather(*tasks)
        
        repo_response, languages_response, contributors_response, tree_response, readme_response = responses
        
        # Parse main repo data
        repo_json = repo_response.json()
        
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
        
        # Parse README (base64 encoded)
        readme_text = ""
        try:
            readme_json = readme_response.json()
            if readme_json.get("encoding") == "base64":
                readme_content = readme_json.get("content", "")
                readme_text = base64.b64decode(readme_content).decode("utf-8")
            else:
                readme_text = readme_json.get("content", "")
        except Exception:
            # README may not exist or be in an unexpected format
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
        }
