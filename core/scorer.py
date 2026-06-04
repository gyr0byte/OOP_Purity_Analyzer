"""Score lookup, aggregation, and evaluation tier classification.

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
    """Determine the matching purity tier for a given total score.

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
    """Score a single repository based on all its supported languages.

    Calculates the weighted average OOP purity score of all supported languages
    found in the repository, based on their byte sizes. If no supported
    languages are found, marks the repository as unscored.

    Args:
        repo_data: Repository data dictionary from the scraper.

    Returns:
        The repo_data dictionary augmented with multi-language scoring fields.
    """
    result = dict(repo_data)
    languages_used = dict(repo_data.get("languages_used", {}))
    primary_lang = repo_data.get("primary_language", "Unknown")

    # Fallback to primary language if languages_used is empty
    if not languages_used and primary_lang != "Unknown":
        languages_used = {primary_lang: 1000}

    supported_langs = []
    file_metrics = repo_data.get("file_metrics", {})
    from core import code_scorer

    for lang_name, bytes_count in languages_used.items():
        matched_key = LANGUAGE_ALIASES.get(lang_name.lower())
        if matched_key and matched_key in LANGUAGE_SCORES:
            # Calculate category scores for this language
            sub_scores = LANGUAGE_SCORES[matched_key]
            cat_scores = {}
            for cat_key in CATEGORY_LABELS:
                cat_subs = sub_scores.get(cat_key, {})
                cat_scores[cat_key] = sum(cat_subs.values())
            lang_total_score = sum(cat_scores.values())

            # Fetch file metrics and calculate modifier
            lang_files = file_metrics.get(matched_key, [])
            mod_result = code_scorer.calculate_code_modifier(matched_key, lang_files)
            modifier = mod_result["modifier"]
            modifier_reason = mod_result["reason"]
            agg_metrics = mod_result["metrics"]

            # Apply modifier to the total score of this language
            adjusted_lang_total_score = int(round(lang_total_score * modifier))
            adjusted_lang_total_score = max(0, min(100, adjusted_lang_total_score))

            # Scale category scores by modifier
            adjusted_cat_scores = {}
            for cat_key, cat_val in cat_scores.items():
                adjusted_cat_scores[cat_key] = round(cat_val * modifier, 2)

            supported_langs.append({
                "language": matched_key,
                "bytes": bytes_count,
                "sub_scores": sub_scores,
                "category_scores": adjusted_cat_scores,
                "total_score": adjusted_lang_total_score,
                "base_score": lang_total_score,
                "modifier": modifier,
                "modifier_reason": modifier_reason,
                "metrics": agg_metrics,
            })

    if not supported_langs:
        result["scored"] = False
        result["reason"] = f"Unsupported language(s): {', '.join(languages_used.keys()) or primary_lang}"
        logger.info(
            "Repo '%s' skipped — unsupported languages: %s",
            repo_data.get("full_name", "unknown"),
            list(languages_used.keys()) or primary_lang,
        )
        return result

    # Sort supported languages by byte size descending
    supported_langs.sort(key=lambda x: x["bytes"], reverse=True)
    total_supported_bytes = sum(x["bytes"] for x in supported_langs)

    # Compute percentages of supported code
    for item in supported_langs:
        item["percentage"] = round((item["bytes"] / total_supported_bytes) * 100, 2)

    dominant_lang_key = supported_langs[0]["language"]

    # Compute weighted average category scores
    category_scores: dict[str, float] = {}
    category_percentages: dict[str, float] = {}
    for cat_key in CATEGORY_LABELS:
        weighted_sum = sum(x["category_scores"][cat_key] * x["bytes"] for x in supported_langs)
        cat_val = round(weighted_sum / total_supported_bytes, 2)
        category_scores[cat_key] = cat_val
        cat_max = CATEGORY_MAX.get(cat_key, 1)
        category_percentages[cat_key] = round((cat_val / cat_max) * 100, 2)

    # Compute weighted average total score
    weighted_total = sum(x["total_score"] * x["bytes"] for x in supported_langs) / total_supported_bytes
    total_score = int(round(weighted_total))
    total_percentage = round((total_score / 100) * 100, 2)
    tier_name, tier_color = _get_purity_tier(total_score)

    result["scored"] = True
    result["matched_language"] = dominant_lang_key  # dominant language for backward compatibility
    result["languages_scored"] = supported_langs
    result["sub_scores"] = supported_langs[0]["sub_scores"]  # dominant language fallback
    result["category_scores"] = category_scores
    result["category_percentages"] = category_percentages
    result["total_score"] = total_score
    result["total_percentage"] = total_percentage
    result["purity_tier"] = tier_name
    result["tier_color"] = tier_color

    logger.info(
        "Scored '%s' (%s dominant): %d/100 — %s",
        repo_data.get("full_name", "unknown"),
        dominant_lang_key,
        total_score,
        tier_name,
    )
    return result


def score_all(
    repos: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Score all listed repositories and generate consolidated summary statistics.

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

    # Language distribution (using the dominant language of each repository)
    language_distribution: dict[str, int] = {}
    for repo in scored_only:
        lang = repo.get("matched_language", "Unknown")
        language_distribution[lang] = language_distribution.get(lang, 0) + 1

    # Tier distribution
    tier_distribution: dict[str, int] = {}
    for repo in scored_only:
        tier = repo.get("purity_tier", "Unknown")
        tier_distribution[tier] = tier_distribution.get(tier, 0) + 1

    # Average score by language (computed across all repositories where the language was scored)
    lang_score_sums: dict[str, float] = {}
    lang_score_counts: dict[str, int] = {}
    for repo in scored_only:
        for item in repo.get("languages_scored", []):
            lang = item["language"]
            score = item["total_score"]
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
