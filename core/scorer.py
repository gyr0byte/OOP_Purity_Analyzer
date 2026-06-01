"""Score lookup, aggregation, and tier classification.

Given repository data from the scraper, this module looks up pre-defined
OOP purity scores, computes category totals and percentages, assigns
purity tiers, and generates summary statistics.
"""

import logging
from typing import Any

from core.scores_db import (
    CATEGORY_LABELS,
    CATEGORY_MAX,
    LANGUAGE_ALIASES,
    LANGUAGE_SCORES,
    PURITY_TIERS,
)

logger: logging.Logger = logging.getLogger(__name__)


def _get_purity_tier(total_score: int) -> tuple[str, str]:
    """Look up the purity tier for a given total score.

    Args:
        total_score: The total OOP purity score (0–100).

    Returns:
        Tuple of (tier_name, tier_hex_color).
    """
    for low, high, tier_name, color in PURITY_TIERS:
        if low <= total_score <= high:
            return tier_name, color
    return "Unknown", "#999999"


def score_repo(repo_data: dict[str, Any]) -> dict[str, Any]:
    """Score a single repository based on its primary language.

    Looks up the primary language in LANGUAGE_ALIASES (case-insensitive).
    If no match is found, marks the repo as unscored. Otherwise, computes
    all category scores, percentages, total score, and purity tier.

    Args:
        repo_data: Repository data dictionary from the scraper.

    Returns:
        The repo_data dictionary augmented with scoring fields.
    """
    result = dict(repo_data)
    primary_lang = repo_data.get("primary_language", "Unknown")
    matched_key = LANGUAGE_ALIASES.get(primary_lang.lower())

    if not matched_key or matched_key not in LANGUAGE_SCORES:
        result["scored"] = False
        result["reason"] = f"Unsupported language: {primary_lang}"
        logger.info(
            "Repo '%s' skipped — unsupported language: %s",
            repo_data.get("full_name", "unknown"),
            primary_lang,
        )
        return result

    sub_scores = LANGUAGE_SCORES[matched_key]

    category_scores: dict[str, int] = {}
    category_percentages: dict[str, float] = {}

    for cat_key in CATEGORY_LABELS:
        cat_subs = sub_scores.get(cat_key, {})
        cat_total = sum(cat_subs.values())
        category_scores[cat_key] = cat_total
        cat_max = CATEGORY_MAX.get(cat_key, 1)
        category_percentages[cat_key] = round(
            (cat_total / cat_max) * 100, 2
        )

    total_score = sum(category_scores.values())
    total_percentage = round((total_score / 100) * 100, 2)
    tier_name, tier_color = _get_purity_tier(total_score)

    result["scored"] = True
    result["matched_language"] = matched_key
    result["sub_scores"] = sub_scores
    result["category_scores"] = category_scores
    result["category_percentages"] = category_percentages
    result["total_score"] = total_score
    result["total_percentage"] = total_percentage
    result["purity_tier"] = tier_name
    result["tier_color"] = tier_color

    logger.info(
        "Scored '%s' (%s): %d/100 — %s",
        repo_data.get("full_name", "unknown"),
        matched_key,
        total_score,
        tier_name,
    )
    return result


def score_all(
    repos: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Score all repositories and generate summary statistics.

    Args:
        repos: List of repository data dictionaries from the scraper.

    Returns:
        Tuple of (scored_repos_list, summary_dict).
        scored_repos_list includes both scored and unscored repos.
        summary_dict contains aggregate statistics.
    """
    scored_repos: list[dict[str, Any]] = []
    for repo in repos:
        scored_repos.append(score_repo(repo))

    scored_only = [r for r in scored_repos if r.get("scored")]
    unscored_only = [r for r in scored_repos if not r.get("scored")]

    # Language distribution
    language_distribution: dict[str, int] = {}
    for repo in scored_only:
        lang = repo.get("matched_language", "Unknown")
        language_distribution[lang] = language_distribution.get(lang, 0) + 1

    # Tier distribution
    tier_distribution: dict[str, int] = {}
    for repo in scored_only:
        tier = repo.get("purity_tier", "Unknown")
        tier_distribution[tier] = tier_distribution.get(tier, 0) + 1

    # Average score by language
    lang_score_sums: dict[str, float] = {}
    lang_score_counts: dict[str, int] = {}
    for repo in scored_only:
        lang = repo.get("matched_language", "Unknown")
        score = repo.get("total_score", 0)
        lang_score_sums[lang] = lang_score_sums.get(lang, 0) + score
        lang_score_counts[lang] = lang_score_counts.get(lang, 0) + 1

    avg_score_by_language: dict[str, float] = {}
    for lang in lang_score_sums:
        avg_score_by_language[lang] = round(
            lang_score_sums[lang] / lang_score_counts[lang], 2
        )

    summary: dict[str, Any] = {
        "total_repos": len(repos),
        "scored_repos": len(scored_only),
        "unscored_repos": len(unscored_only),
        "language_distribution": language_distribution,
        "tier_distribution": tier_distribution,
        "avg_score_by_language": avg_score_by_language,
    }

    return scored_repos, summary
