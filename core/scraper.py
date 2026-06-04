"""GitHub API scraping logic via PyGithub.

Supports three input modes: repository URLs, topic/keyword search,
and GitHub username. Handles rate limiting and error recovery.
"""

import logging
import re
from datetime import datetime, timezone
from typing import Any

from github import Github, GithubException

from config import GITHUB_TOKEN

logger: logging.Logger = logging.getLogger(__name__)


def _get_github_client() -> Github | None:
    """Initialize and validate a new GitHub API client.

    Returns:
        Authenticated Github client instance or None in mock mode.

    Raises:
        ValueError: If the token is missing or invalid.
    """
    if not GITHUB_TOKEN:
        raise ValueError(
            "GitHub token is missing or invalid. "
            "Set GITHUB_TOKEN in your .env file."
        )
    if GITHUB_TOKEN == "mock":
        return None
    g = Github(GITHUB_TOKEN)
    try:
        g.get_user().login
    except GithubException as exc:
        raise ValueError(
            "GitHub token is missing or invalid. "
            "Set GITHUB_TOKEN in your .env file."
        ) from exc
    return g


def _check_rate_limit(g: Github) -> str | None:
    """Check remaining GitHub API rate limit before making calls.

    Args:
        g: Authenticated Github client.

    Returns:
        Error message string if rate limit is too low, None otherwise.
    """
    try:
        rate_limit = g.get_rate_limit()
        remaining = rate_limit.core.remaining
        if remaining < 10:
            reset_time = rate_limit.core.reset.replace(
                tzinfo=timezone.utc
            ).strftime("%Y-%m-%d %H:%M:%S UTC")
            return (
                f"GitHub API rate limit reached. "
                f"Resets at {reset_time}. Please wait and retry."
            )
    except GithubException as exc:
        logger.error("Failed to check rate limit: %s", exc)
        return "Unable to verify GitHub API rate limit."
    return None


def _fetch_repo_file_metrics(repo: Any, languages_used: dict[str, int]) -> dict[str, list[dict[str, Any]]]:
    """Fetch sample files for supported languages and run AST analysis.

    Returns a dictionary mapping language to list of file metrics.
    """
    from core.scores_db import LANGUAGE_ALIASES
    from core import ast_analyzer

    supported_langs = {}
    for lang_name in languages_used.keys():
        norm = LANGUAGE_ALIASES.get(lang_name.lower())
        if norm:
            supported_langs[norm] = lang_name

    if not supported_langs:
        return {}

    # Map normalized language to file extensions
    ext_map = {
        "Python": [".py"],
        "Java": [".java"],
        "JavaScript": [".js", ".jsx"],
        "TypeScript": [".ts", ".tsx"],
        "C++": [".cpp", ".h", ".hpp", ".cc"],
        "Ruby": [".rb"],
        "C#": [".cs"],
        "Kotlin": [".kt"]
    }

    file_metrics_by_lang = {lang: [] for lang in supported_langs}

    try:
        # Walk root directory
        root_contents = repo.get_contents("")
        queue = list(root_contents)
        file_items = []

        # Limit traversal depth and total files to avoid rate limits
        dirs_visited = 0
        while queue and len(file_items) < 30 and dirs_visited < 10:
            item = queue.pop(0)
            if item.type == "dir":
                # Only traverse folders like src, app, lib, core, source
                if item.name.lower() in ("src", "lib", "app", "core", "source", "kotlin", "java", "python"):
                    dirs_visited += 1
                    try:
                        queue.extend(repo.get_contents(item.path))
                    except Exception:
                        pass
            elif item.type == "file":
                file_items.append(item)

        # Group file items by supported language
        for item in file_items:
            matched_lang = None
            for norm_lang in supported_langs:
                exts = ext_map.get(norm_lang, [])
                if any(item.name.endswith(ext) for ext in exts):
                    matched_lang = norm_lang
                    break

            if matched_lang and len(file_metrics_by_lang[matched_lang]) < 10:
                try:
                    content_file = repo.get_contents(item.path)
                    if content_file.size > 0 and content_file.size < 500000:  # limit to < 500KB
                        decoded = content_file.decoded_content.decode("utf-8", errors="ignore")
                        metrics = ast_analyzer.analyze_code_content(matched_lang, decoded)
                        file_metrics_by_lang[matched_lang].append(metrics)
                except Exception as e:
                    logger.warning("Error fetching/analyzing file %s: %s", item.path, e)

    except Exception as exc:
        logger.warning("Error traversing repo %s for file metrics: %s", repo.full_name, exc)

    return file_metrics_by_lang


def _extract_repo_data(repo: Any) -> dict[str, Any]:
    """Extract standardized repository data fields from a GitHub repository object.

    Args:
        repo: A PyGithub Repository object.

    Returns:
        Dictionary with all required repository fields.
    """
    try:
        topics = repo.get_topics()
    except GithubException:
        topics = []
        logger.warning("Could not fetch topics for %s", repo.full_name)

    try:
        languages_used = repo.get_languages()
    except GithubException:
        languages_used = {}
        logger.warning("Could not fetch languages for %s", repo.full_name)

    dict_langs = dict(languages_used)
    file_metrics = _fetch_repo_file_metrics(repo, dict_langs)

    return {
        "name": repo.name,
        "full_name": repo.full_name,
        "url": repo.html_url,
        "description": repo.description or "",
        "primary_language": repo.language or "Unknown",
        "languages_used": dict_langs,
        "stars": repo.stargazers_count,
        "forks": repo.forks_count,
        "open_issues": repo.open_issues_count,
        "topics": list(topics),
        "created_at": repo.created_at.isoformat() if repo.created_at else "",
        "updated_at": repo.updated_at.isoformat() if repo.updated_at else "",
        "size_kb": repo.size,
        "file_metrics": file_metrics,
    }


def _parse_repo_url(url: str) -> str | None:
    """Extract the owner/repo path from a GitHub URL.

    Args:
        url: Full GitHub URL (e.g. https://github.com/django/django).

    Returns:
        'owner/repo' string, or None if the URL is invalid.
    """
    url = url.strip().rstrip("/")
    match = re.match(
        r"https?://github\.com/([^/]+/[^/]+)/?.*", url
    )
    if match:
        return match.group(1)
    return None


def _scrape_by_urls(g: Github, input_data: str) -> list[dict[str, Any]]:
    """Scrape repository data from a newline-separated list of GitHub URLs.

    Args:
        g: Authenticated Github client.
        input_data: Newline-separated GitHub repository URLs.

    Returns:
        List of repository data dictionaries.
    """
    repos: list[dict[str, Any]] = []
    urls = [line.strip() for line in input_data.strip().split("\n") if line.strip()]

    for url in urls:
        rate_error = _check_rate_limit(g)
        if rate_error:
            raise RuntimeError(rate_error)

        repo_path = _parse_repo_url(url)
        if not repo_path:
            logger.warning("Invalid GitHub URL skipped: %s", url)
            continue

        try:
            repo = g.get_repo(repo_path)
            repos.append(_extract_repo_data(repo))
            logger.info("Scraped repository: %s", repo.full_name)
        except GithubException as exc:
            logger.error("Failed to fetch repo '%s': %s", repo_path, exc)
            continue

    return repos


def _scrape_by_search(
    g: Github, query: str, limit: int
) -> list[dict[str, Any]]:
    """Scrape repositories matching a topic or keyword search.

    Args:
        g: Authenticated Github client.
        query: Search query string (e.g. 'machine learning').
        limit: Maximum number of repos to return.

    Returns:
        List of repository data dictionaries.
    """
    repos: list[dict[str, Any]] = []

    rate_error = _check_rate_limit(g)
    if rate_error:
        raise RuntimeError(rate_error)

    try:
        results = g.search_repositories(
            query=query, sort="stars", order="desc"
        )
        for i, repo in enumerate(results):
            if i >= limit:
                break
            rate_error = _check_rate_limit(g)
            if rate_error:
                raise RuntimeError(rate_error)
            repos.append(_extract_repo_data(repo))
            logger.info("Scraped repository: %s", repo.full_name)
    except GithubException as exc:
        logger.error("Search failed for query '%s': %s", query, exc)
        raise RuntimeError(f"GitHub search failed: {exc}") from exc

    return repos


def _scrape_by_user(
    g: Github, username: str, limit: int
) -> list[dict[str, Any]]:
    """Scrape repositories from a specified GitHub user's public profile.

    Args:
        g: Authenticated Github client.
        username: GitHub username.
        limit: Maximum number of repos to return.

    Returns:
        List of repository data dictionaries.
    """
    repos: list[dict[str, Any]] = []

    rate_error = _check_rate_limit(g)
    if rate_error:
        raise RuntimeError(rate_error)

    try:
        user = g.get_user(username)
        user_repos = user.get_repos(type="public", sort="updated")
        for i, repo in enumerate(user_repos):
            if i >= limit:
                break
            rate_error = _check_rate_limit(g)
            if rate_error:
                raise RuntimeError(rate_error)
            repos.append(_extract_repo_data(repo))
            logger.info("Scraped repository: %s", repo.full_name)
    except GithubException as exc:
        logger.error("Failed to fetch repos for user '%s': %s", username, exc)
        raise RuntimeError(
            f"Failed to fetch repositories for user '{username}': {exc}"
        ) from exc

    return repos


def _generate_mock_repos(mode: str, input_data: str, limit: int) -> list[dict[str, Any]]:
    """Generate high-fidelity mock repository data representing supported OOP languages."""
    all_mocks = [
        {
            "name": "pharo",
            "full_name": "pharo-project/pharo",
            "url": "https://github.com/pharo-project/pharo",
            "description": "Pharo is a pure object-oriented programming language and environment.",
            "primary_language": "Smalltalk",
            "languages_used": {"Smalltalk": 100000},
            "stars": 3200,
            "forks": 800,
            "open_issues": 150,
            "topics": ["smalltalk", "pharo", "pure-oop"],
            "created_at": "2009-08-20T00:00:00Z",
            "updated_at": "2026-05-20T00:00:00Z",
            "size_kb": 150000,
            "file_metrics": {
                "Smalltalk": [{"class_count": 8, "private_members": 0, "protected_members": 0, "public_members": 20, "inheritance_count": 5, "polymorphism_count": 0, "total_lines": 400, "total_functions": 0}]
            },
        },
        {
            "name": "spring-framework",
            "full_name": "spring-projects/spring-framework",
            "url": "https://github.com/spring-projects/spring-framework",
            "description": "Spring Framework",
            "primary_language": "Java",
            "languages_used": {"Java": 98000, "Kotlin": 2000},
            "stars": 55000,
            "forks": 38000,
            "open_issues": 350,
            "topics": ["spring", "framework", "java"],
            "created_at": "2010-06-15T00:00:00Z",
            "updated_at": "2026-05-29T00:00:00Z",
            "size_kb": 250000,
            "file_metrics": {
                "Java": [{"class_count": 6, "private_members": 15, "protected_members": 8, "public_members": 12, "inheritance_count": 4, "polymorphism_count": 6, "total_lines": 450, "total_functions": 12}],
                "Kotlin": [{"class_count": 2, "private_members": 4, "protected_members": 2, "public_members": 8, "inheritance_count": 1, "polymorphism_count": 2, "total_lines": 120, "total_functions": 4}]
            },
        },
        {
            "name": "django",
            "full_name": "django/django",
            "url": "https://github.com/django/django",
            "description": "A high-level Python web framework.",
            "primary_language": "Python",
            "languages_used": {"Python": 95000, "HTML": 3000, "JavaScript": 2000},
            "stars": 75000,
            "forks": 30000,
            "open_issues": 120,
            "topics": ["web", "framework", "python", "django"],
            "created_at": "2012-04-28T00:00:00Z",
            "updated_at": "2026-05-30T00:00:00Z",
            "size_kb": 120000,
            "file_metrics": {
                "Python": [{"class_count": 10, "private_members": 12, "protected_members": 8, "public_members": 24, "inheritance_count": 5, "polymorphism_count": 0, "total_lines": 700, "total_functions": 20}]
            },
        },
        {
            "name": "react",
            "full_name": "facebook/react",
            "url": "https://github.com/facebook/react",
            "description": "A declarative, efficient frontend library.",
            "primary_language": "JavaScript",
            "languages_used": {"JavaScript": 99000, "HTML": 1000},
            "stars": 220000,
            "forks": 45000,
            "open_issues": 800,
            "topics": ["react", "javascript", "library"],
            "created_at": "2013-05-24T00:00:00Z",
            "updated_at": "2026-05-31T00:00:00Z",
            "size_kb": 320000,
            "file_metrics": {
                "JavaScript": [{"class_count": 0, "private_members": 0, "protected_members": 0, "public_members": 0, "inheritance_count": 0, "polymorphism_count": 0, "total_lines": 500, "total_functions": 45}]
            },
        },
        {
            "name": "tensorflow",
            "full_name": "tensorflow/tensorflow",
            "url": "https://github.com/tensorflow/tensorflow",
            "description": "An Open Source Machine Learning Framework",
            "primary_language": "C++",
            "languages_used": {"C++": 60000, "Python": 35000},
            "stars": 180000,
            "forks": 89000,
            "open_issues": 1500,
            "topics": ["tensorflow", "machine-learning"],
            "created_at": "2015-11-07T00:00:00Z",
            "updated_at": "2026-05-30T00:00:00Z",
            "size_kb": 950000,
            "file_metrics": {
                "C++": [{"class_count": 7, "private_members": 22, "protected_members": 8, "public_members": 14, "inheritance_count": 3, "polymorphism_count": 7, "total_lines": 550, "total_functions": 10}],
                "Python": [{"class_count": 4, "private_members": 8, "protected_members": 6, "public_members": 12, "inheritance_count": 2, "polymorphism_count": 0, "total_lines": 300, "total_functions": 8}]
            },
        },
        {
            "name": "rails",
            "full_name": "rails/rails",
            "url": "https://github.com/rails/rails",
            "description": "Ruby on Rails",
            "primary_language": "Ruby",
            "languages_used": {"Ruby": 92000, "JavaScript": 5000},
            "stars": 53000,
            "forks": 21000,
            "open_issues": 210,
            "topics": ["rails", "framework", "ruby"],
            "created_at": "2008-04-11T00:00:00Z",
            "updated_at": "2026-05-28T00:00:00Z",
            "size_kb": 180000,
            "file_metrics": {
                "Ruby": [{"class_count": 8, "private_members": 10, "protected_members": 4, "public_members": 16, "inheritance_count": 4, "polymorphism_count": 0, "total_lines": 500, "total_functions": 14}]
            },
        },
        {
            "name": "roslyn",
            "full_name": "dotnet/roslyn",
            "url": "https://github.com/dotnet/roslyn",
            "description": "The Roslyn .NET compiler platform.",
            "primary_language": "C#",
            "languages_used": {"C#": 97000, "TypeScript": 3000},
            "stars": 17000,
            "forks": 4200,
            "open_issues": 400,
            "topics": ["dotnet", "roslyn", "compiler"],
            "created_at": "2011-12-02T00:00:00Z",
            "updated_at": "2026-05-25T00:00:00Z",
            "size_kb": 450000,
            "file_metrics": {
                "C#": [{"class_count": 12, "private_members": 30, "protected_members": 15, "public_members": 25, "inheritance_count": 8, "polymorphism_count": 12, "total_lines": 900, "total_functions": 24}]
            },
        },
        {
            "name": "kotlin",
            "full_name": "JetBrains/kotlin",
            "url": "https://github.com/JetBrains/kotlin",
            "description": "The Kotlin Programming Language.",
            "primary_language": "Kotlin",
            "languages_used": {"Kotlin": 90000, "Java": 10000},
            "stars": 46000,
            "forks": 5500,
            "open_issues": 90,
            "topics": ["kotlin", "language"],
            "created_at": "2012-02-13T00:00:00Z",
            "updated_at": "2026-05-29T00:00:00Z",
            "size_kb": 620000,
            "file_metrics": {
                "Kotlin": [{"class_count": 8, "private_members": 16, "protected_members": 10, "public_members": 20, "inheritance_count": 5, "polymorphism_count": 8, "total_lines": 600, "total_functions": 18}],
                "Java": [{"class_count": 4, "private_members": 8, "protected_members": 4, "public_members": 10, "inheritance_count": 2, "polymorphism_count": 4, "total_lines": 350, "total_functions": 8}]
            },
        },
        {
            "name": "linux",
            "full_name": "torvalds/linux",
            "url": "https://github.com/torvalds/linux",
            "description": "Linux kernel source tree",
            "primary_language": "C",
            "languages_used": {"C": 100000},
            "stars": 160000,
            "forks": 49000,
            "open_issues": 0,
            "topics": ["linux", "kernel"],
            "created_at": "2011-09-04T00:00:00Z",
            "updated_at": "2026-05-31T00:00:00Z",
            "size_kb": 1200000,
            "file_metrics": {},
        }
    ]

    if mode == "urls":
        urls = [line.strip().lower() for line in input_data.strip().split("\n") if line.strip()]
        result = []
        for url in urls:
            matched = False
            for m in all_mocks:
                if m["name"] in url or m["full_name"].lower() in url:
                    result.append(m)
                    matched = True
                    break
            if not matched:
                name = url.split("/")[-1] or "custom-repo"
                result.append({
                    "name": name,
                    "full_name": f"custom/{name}",
                    "url": url,
                    "description": "Ad-hoc mock repository for testing.",
                    "primary_language": "Python",
                    "languages_used": {"Python": 100000},
                    "stars": 100,
                    "forks": 10,
                    "open_issues": 1,
                    "topics": [],
                    "created_at": "2020-01-01T00:00:00Z",
                    "updated_at": "2026-01-01T00:00:00Z",
                    "size_kb": 1000,
                    "file_metrics": {
                        "Python": [{"class_count": 5, "private_members": 5, "protected_members": 2, "public_members": 10, "inheritance_count": 2, "polymorphism_count": 0, "total_lines": 300, "total_functions": 10}]
                    },
                })
        return result
    else:
        return all_mocks[:limit]


def scrape(
    mode: str, input_data: str, limit: int = 20
) -> list[dict[str, Any]]:
    """Main scraping dispatcher routing requests based on input mode.

    Args:
        mode: One of 'urls', 'search', or 'user'.
        input_data: The raw text input (URLs, keyword, or username).
        limit: Maximum number of repos to fetch (for search and user modes).

    Returns:
        List of repository data dictionaries.

    Raises:
        ValueError: If mode is invalid or input is empty.
        RuntimeError: If a GitHub API error or rate limit issue occurs.
    """
    if not input_data or not input_data.strip():
        raise ValueError("Input data cannot be empty.")

    if GITHUB_TOKEN == "mock":
        return _generate_mock_repos(mode, input_data, limit)

    g = _get_github_client()

    if mode == "urls":
        return _scrape_by_urls(g, input_data)
    elif mode == "search":
        return _scrape_by_search(g, input_data.strip(), limit)
    elif mode == "user":
        return _scrape_by_user(g, input_data.strip(), limit)
    else:
        raise ValueError(f"Invalid scraping mode: '{mode}'. Use 'urls', 'search', or 'user'.")
