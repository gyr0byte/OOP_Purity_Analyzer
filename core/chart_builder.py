"""All Plotly chart generation functions for the OOP Purity Analyzer dashboard.

Each function accepts scored repository data and returns a Plotly figure
serialized to JSON via plotly.io.to_json(). All charts use the 'plotly_dark'
template for a consistent dark theme. Empty data is handled gracefully with
a 'No data available' annotation.
"""

import logging
from typing import Any

import numpy as np
import plotly.graph_objects as go
import plotly.io as pio

from core.scores_db import CATEGORY_LABELS, CATEGORY_MAX

logger: logging.Logger = logging.getLogger(__name__)

# Consistent layout defaults
_TEMPLATE = "plotly_dark"
_FONT = dict(family="Inter, sans-serif", size=13)
_MARGIN = dict(l=60, r=40, t=60, b=60)


def _empty_figure(message: str = "No data available") -> str:
    """Create a Plotly figure with a centered message for empty data.

    Args:
        message: The message to display.

    Returns:
        JSON string of the Plotly figure.
    """
    fig = go.Figure()
    fig.update_layout(
        template=_TEMPLATE,
        font=_FONT,
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        annotations=[
            dict(
                text=message,
                xref="paper", yref="paper",
                x=0.5, y=0.5,
                showarrow=False,
                font=dict(size=20, color="#888888"),
            )
        ],
    )
    return pio.to_json(fig)


def _get_scored_only(scored_repos: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Filter to only scored repos.

    Args:
        scored_repos: List of all repo dicts (scored and unscored).

    Returns:
        List of repo dicts that have scored=True.
    """
    return [r for r in scored_repos if r.get("scored")]


def _format_languages_scored(repo: dict[str, Any]) -> str:
    """Format the list of scored languages into a single string with percentages.

    E.g. "Java (98%), Kotlin (2%)"
    """
    langs = repo.get("languages_scored", [])
    if not langs:
        return repo.get("matched_language", "Unknown")
    parts = []
    for l in langs:
        pct = l['percentage']
        pct_str = f"{int(pct)}" if pct.is_integer() else f"{pct:.2f}"
        parts.append(f"{l['language']} ({pct_str}%)")
    return ", ".join(parts)


def bar_chart_total_scores(scored_repos: list[dict[str, Any]]) -> str:
    """Horizontal bar chart of total OOP purity scores by repository.

    Args:
        scored_repos: List of scored repo dictionaries.

    Returns:
        JSON string of the Plotly figure.
    """
    repos = _get_scored_only(scored_repos)
    if not repos:
        return _empty_figure("No scored repositories to display")

    # Sort by score ascending (Plotly renders bottom-to-top)
    repos_sorted = sorted(repos, key=lambda r: r["total_score"])

    names = [r["full_name"] for r in repos_sorted]
    scores = [r["total_score"] for r in repos_sorted]
    colors = [r["tier_color"] for r in repos_sorted]
    hover_texts = [
        f"Languages: {_format_languages_scored(r)}<br>"
        f"Score: {r['total_score']}/100<br>"
        f"Tier: {r['purity_tier']}<br>"
        f"Stars: {r['stars']:,}"
        for r in repos_sorted
    ]

    fig = go.Figure(
        go.Bar(
            x=scores,
            y=names,
            orientation="h",
            marker=dict(color=colors, line=dict(width=0)),
            hovertext=hover_texts,
            hoverinfo="text",
        )
    )
    fig.update_layout(
        title="OOP Purity Scores by Repository",
        xaxis_title="Total OOP Purity Score (0–100)",
        xaxis=dict(range=[0, 105]),
        template=_TEMPLATE,
        font=_FONT,
        margin=dict(l=200, r=40, t=60, b=60),
        height=max(400, len(repos_sorted) * 35 + 100),
    )
    return pio.to_json(fig)


def radar_chart_by_language(language: str) -> str:
    """Spider/radar chart for a single language showing C1–C7 category percentages.

    Args:
        language: The canonical language name (e.g. 'Java').

    Returns:
        JSON string of the Plotly figure.
    """
    from core.scores_db import LANGUAGE_SCORES

    if language not in LANGUAGE_SCORES:
        return _empty_figure(f"No data for language: {language}")

    lang_scores = LANGUAGE_SCORES[language]
    categories = list(CATEGORY_LABELS.keys())
    labels = [CATEGORY_LABELS[c] for c in categories]

    percentages = []
    for cat in categories:
        cat_subs = lang_scores.get(cat, {})
        cat_total = sum(cat_subs.values())
        cat_max = CATEGORY_MAX.get(cat, 1)
        percentages.append(round((cat_total / cat_max) * 100, 2))

    # Close the polygon
    labels_closed = labels + [labels[0]]
    percentages_closed = percentages + [percentages[0]]

    fig = go.Figure(
        go.Scatterpolar(
            r=percentages_closed,
            theta=labels_closed,
            fill="toself",
            fillcolor="rgba(74, 144, 226, 0.3)",
            line=dict(color="#4a90e2", width=2),
            marker=dict(size=6),
            hovertemplate="%{theta}: %{r:.1f}%<extra></extra>",
        )
    )
    fig.update_layout(
        title=f"OOP Category Profile — {language}",
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 100]),
            bgcolor="rgba(0,0,0,0)",
        ),
        template=_TEMPLATE,
        font=_FONT,
        showlegend=False,
        height=450,
    )
    return pio.to_json(fig)


def heatmap_subcriteria(scored_repos: list[dict[str, Any]]) -> str:
    """Heatmap of sub-criterion scores by language.

    Args:
        scored_repos: List of scored repo dictionaries.

    Returns:
        JSON string of the Plotly figure.
    """
    repos = _get_scored_only(scored_repos)
    if not repos:
        return _empty_figure("No scored repositories for heatmap")

    # Get unique languages
    languages = list(dict.fromkeys(r["matched_language"] for r in repos))

    from core.scores_db import LANGUAGE_SCORES

    # Build sub-criteria labels
    categories = sorted(CATEGORY_LABELS.keys())
    sub_labels: list[str] = []
    for cat in categories:
        first_lang = languages[0]
        subs = LANGUAGE_SCORES.get(first_lang, {}).get(cat, {})
        for sub_key in sorted(subs.keys()):
            sub_labels.append(sub_key)

    # Build the z matrix
    z_matrix: list[list[int]] = []
    for lang in languages:
        row: list[int] = []
        for cat in categories:
            subs = LANGUAGE_SCORES.get(lang, {}).get(cat, {})
            for sub_key in sorted(subs.keys()):
                row.append(subs.get(sub_key, 0))
        z_matrix.append(row)

    fig = go.Figure(
        go.Heatmap(
            z=z_matrix,
            x=sub_labels,
            y=languages,
            colorscale="RdYlGn",
            text=z_matrix,
            texttemplate="%{text}",
            textfont=dict(size=11),
            hovertemplate=(
                "Language: %{y}<br>"
                "Sub-criterion: %{x}<br>"
                "Score: %{z}<extra></extra>"
            ),
        )
    )
    fig.update_layout(
        title="Sub-Criterion Score Heatmap by Language",
        xaxis_title="Sub-Criteria",
        yaxis_title="Language",
        template=_TEMPLATE,
        font=_FONT,
        height=max(350, len(languages) * 50 + 150),
        margin=dict(l=100, r=40, t=60, b=80),
    )
    return pio.to_json(fig)


def grouped_bar_category_comparison(scored_repos: list[dict[str, Any]]) -> str:
    """Grouped bar chart comparing category percentages across languages.

    Args:
        scored_repos: List of scored repo dictionaries.

    Returns:
        JSON string of the Plotly figure.
    """
    repos = _get_scored_only(scored_repos)
    if not repos:
        return _empty_figure("No scored repositories for comparison")

    languages = list(dict.fromkeys(r["matched_language"] for r in repos))
    categories = list(CATEGORY_LABELS.keys())
    cat_labels = [CATEGORY_LABELS[c] for c in categories]

    from core.scores_db import LANGUAGE_SCORES

    traces: list[go.Bar] = []
    colors = [
        "#4a90e2", "#e74c3c", "#2ecc71", "#f39c12",
        "#9b59b6", "#1abc9c", "#e67e22", "#3498db",
    ]

    for i, lang in enumerate(languages):
        percentages = []
        for cat in categories:
            cat_subs = LANGUAGE_SCORES.get(lang, {}).get(cat, {})
            cat_total = sum(cat_subs.values())
            cat_max = CATEGORY_MAX.get(cat, 1)
            percentages.append(round((cat_total / cat_max) * 100, 2))

        traces.append(
            go.Bar(
                name=lang,
                x=cat_labels,
                y=percentages,
                marker_color=colors[i % len(colors)],
                hovertemplate=(
                    f"{lang}<br>"
                    "%{x}: %{y:.1f}%<extra></extra>"
                ),
            )
        )

    fig = go.Figure(data=traces)
    fig.update_layout(
        title="Category-Level OOP Purity Comparison by Language",
        xaxis_title="Category",
        yaxis_title="Category Percentage Score (0–100%)",
        yaxis=dict(range=[0, 105]),
        barmode="group",
        template=_TEMPLATE,
        font=_FONT,
        height=500,
        margin=_MARGIN,
    )
    return pio.to_json(fig)


def treemap_repos_by_tier(scored_repos: list[dict[str, Any]]) -> str:
    """Treemap of repositories organized by purity tier and language.

    Args:
        scored_repos: List of scored repo dictionaries.

    Returns:
        JSON string of the Plotly figure.
    """
    repos = _get_scored_only(scored_repos)
    if not repos:
        return _empty_figure("No scored repositories for treemap")

    labels: list[str] = []
    parents: list[str] = []
    values: list[int] = []
    colors: list[str] = []
    hover_texts: list[str] = []

    # Pre-compute totals so parent nodes have valid values.
    tier_totals: dict[str, int] = {}
    tier_lang_totals: dict[str, int] = {}
    total_value = 0

    for repo in repos:
        tier = repo["purity_tier"]
        lang = repo["matched_language"]
        tier_lang_key = f"{tier} — {lang}"
        star_val = max(repo.get("stars", 0), 1)

        total_value += star_val
        tier_totals[tier] = tier_totals.get(tier, 0) + star_val
        tier_lang_totals[tier_lang_key] = tier_lang_totals.get(
            tier_lang_key, 0) + star_val

    # Root
    labels.append("All Repositories")
    parents.append("")
    values.append(total_value)
    colors.append("#1a1a2e")
    hover_texts.append("All Repositories")

    tier_set: set[str] = set()
    lang_tier_set: set[str] = set()

    for repo in repos:
        tier = repo["purity_tier"]
        lang = repo["matched_language"]
        tier_lang_key = f"{tier} — {lang}"

        # Add tier node
        if tier not in tier_set:
            tier_set.add(tier)
            labels.append(tier)
            parents.append("All Repositories")
            values.append(tier_totals.get(tier, 0))
            colors.append(repo["tier_color"])
            hover_texts.append(tier)

        # Add language node under tier
        if tier_lang_key not in lang_tier_set:
            lang_tier_set.add(tier_lang_key)
            labels.append(tier_lang_key)
            parents.append(tier)
            values.append(tier_lang_totals.get(tier_lang_key, 0))
            colors.append(repo["tier_color"])
            hover_texts.append(f"{lang} ({tier})")

        # Add repo node
        star_val = max(repo.get("stars", 0), 1)
        labels.append(repo["full_name"])
        parents.append(tier_lang_key)
        values.append(star_val)
        colors.append(repo["tier_color"])
        hover_texts.append(
            f"{repo['full_name']}<br>"
            f"Language: {lang}<br>"
            f"Score: {repo['total_score']}/100<br>"
            f"Stars: {repo['stars']:,}"
        )

    fig = go.Figure(
        go.Treemap(
            labels=labels,
            parents=parents,
            values=values,
            marker=dict(colors=colors, line=dict(width=1, color="#1a1a2e")),
            hovertext=hover_texts,
            hoverinfo="text",
            branchvalues="total",
            textinfo="label",
        )
    )
    fig.update_layout(
        title="Repository OOP Purity Treemap",
        template=_TEMPLATE,
        font=_FONT,
        height=550,
        margin=dict(l=10, r=10, t=60, b=10),
    )
    return pio.to_json(fig)


def scatter_score_vs_stars(scored_repos: list[dict[str, Any]]) -> str:
    """Scatter plot of OOP purity score vs GitHub stars with OLS trendline.

    Args:
        scored_repos: List of scored repo dictionaries.

    Returns:
        JSON string of the Plotly figure.
    """
    repos = _get_scored_only(scored_repos)
    if not repos:
        return _empty_figure("No scored repositories for scatter plot")

    languages = list(dict.fromkeys(r["matched_language"] for r in repos))
    colors = [
        "#4a90e2", "#e74c3c", "#2ecc71", "#f39c12",
        "#9b59b6", "#1abc9c", "#e67e22", "#3498db",
    ]

    fig = go.Figure()

    all_scores: list[float] = []
    all_stars: list[float] = []

    for i, lang in enumerate(languages):
        lang_repos = [r for r in repos if r["matched_language"] == lang]
        scores = [r["total_score"] for r in lang_repos]
        stars = [max(r["stars"], 1) for r in lang_repos]
        forks = [r["forks"] for r in lang_repos]
        sizes = [max(f * 0.5, 8) for f in forks]
        sizes = [min(s, 50) for s in sizes]

        all_scores.extend(scores)
        all_stars.extend(stars)

        hover_texts = [
            f"{r['full_name']}<br>"
            f"Language: {lang}<br>"
            f"Score: {r['total_score']}<br>"
            f"Stars: {r['stars']:,}<br>"
            f"Forks: {r['forks']:,}"
            for r in lang_repos
        ]

        fig.add_trace(
            go.Scatter(
                x=scores,
                y=stars,
                mode="markers",
                name=lang,
                marker=dict(
                    color=colors[i % len(colors)],
                    size=sizes,
                    line=dict(width=1, color="#ffffff"),
                    opacity=0.8,
                ),
                hovertext=hover_texts,
                hoverinfo="text",
            )
        )

    # OLS trendline
    if len(all_scores) >= 2:
        x_arr = np.array(all_scores, dtype=float)
        y_arr = np.array(all_stars, dtype=float)
        try:
            coeffs = np.polyfit(x_arr, y_arr, 1)
            x_line = np.linspace(x_arr.min(), x_arr.max(), 50)
            y_line = np.polyval(coeffs, x_line)
            fig.add_trace(
                go.Scatter(
                    x=x_line.tolist(),
                    y=y_line.tolist(),
                    mode="lines",
                    name="Trendline (OLS)",
                    line=dict(color="#ffffff", dash="dash", width=2),
                    hoverinfo="skip",
                )
            )
        except (np.linalg.LinAlgError, ValueError):
            logger.warning("Could not compute OLS trendline")

    max_stars = max(all_stars) if all_stars else 100
    use_log = max_stars > 10000

    fig.update_layout(
        title="OOP Purity Score vs. Repository Popularity",
        xaxis_title="Total OOP Purity Score",
        yaxis_title="GitHub Stars" + (" (log scale)" if use_log else ""),
        yaxis=dict(type="log" if use_log else "linear"),
        template=_TEMPLATE,
        font=_FONT,
        height=500,
        margin=_MARGIN,
    )
    return pio.to_json(fig)


def donut_tier_distribution(scored_repos: list[dict[str, Any]]) -> str:
    """Donut chart showing repository distribution by purity tier.

    Args:
        scored_repos: List of scored repo dictionaries.

    Returns:
        JSON string of the Plotly figure.
    """
    repos = _get_scored_only(scored_repos)
    if not repos:
        return _empty_figure("No scored repositories for distribution chart")

    from core.scores_db import PURITY_TIERS

    tier_counts: dict[str, int] = {}
    tier_colors_map: dict[str, str] = {}
    for repo in repos:
        tier = repo["purity_tier"]
        tier_counts[tier] = tier_counts.get(tier, 0) + 1
        tier_colors_map[tier] = repo["tier_color"]

    # Order by tier definition
    ordered_tiers: list[str] = []
    ordered_counts: list[int] = []
    ordered_colors: list[str] = []
    for _, _, tier_name, color in PURITY_TIERS:
        if tier_name in tier_counts:
            ordered_tiers.append(tier_name)
            ordered_counts.append(tier_counts[tier_name])
            ordered_colors.append(color)

    fig = go.Figure(
        go.Pie(
            labels=ordered_tiers,
            values=ordered_counts,
            hole=0.4,
            marker=dict(colors=ordered_colors, line=dict(
                width=2, color="#1a1a2e")),
            hovertemplate=(
                "%{label}<br>"
                "Count: %{value}<br>"
                "Percentage: %{percent}<extra></extra>"
            ),
            textinfo="label+percent",
            textfont=dict(size=12),
        )
    )
    fig.update_layout(
        title="Repository Distribution by OOP Purity Tier",
        template=_TEMPLATE,
        font=_FONT,
        height=450,
        margin=dict(l=40, r=40, t=60, b=40),
    )
    return pio.to_json(fig)


def line_chart_score_over_time(scored_repos: list[dict[str, Any]]) -> str:
    """Line chart of average OOP purity score by year of repo creation.

    Args:
        scored_repos: List of scored repo dictionaries.

    Returns:
        JSON string of the Plotly figure.
    """
    repos = _get_scored_only(scored_repos)
    if not repos:
        return _empty_figure("No scored repositories for timeline chart")

    # Group by language and year
    lang_year_data: dict[str, dict[int, list[int]]] = {}
    for repo in repos:
        lang = repo["matched_language"]
        created = repo.get("created_at", "")
        if not created:
            continue
        try:
            year = int(created[:4])
        except (ValueError, IndexError):
            continue

        if lang not in lang_year_data:
            lang_year_data[lang] = {}
        if year not in lang_year_data[lang]:
            lang_year_data[lang][year] = []
        lang_year_data[lang][year].append(repo["total_score"])

    if not lang_year_data:
        return _empty_figure("No valid creation dates for timeline chart")

    colors = [
        "#4a90e2", "#e74c3c", "#2ecc71", "#f39c12",
        "#9b59b6", "#1abc9c", "#e67e22", "#3498db",
    ]

    fig = go.Figure()
    for i, (lang, year_data) in enumerate(sorted(lang_year_data.items())):
        years = sorted(year_data.keys())
        avg_scores = [
            round(sum(year_data[y]) / len(year_data[y]), 2) for y in years
        ]

        fig.add_trace(
            go.Scatter(
                x=years,
                y=avg_scores,
                mode="lines+markers",
                name=lang,
                line=dict(color=colors[i % len(colors)], width=2),
                marker=dict(size=8),
                hovertemplate=(
                    f"{lang}<br>"
                    "Year: %{x}<br>"
                    "Avg Score: %{y:.1f}<extra></extra>"
                ),
            )
        )

    fig.update_layout(
        title="Average OOP Purity Score by Year of Repo Creation",
        xaxis_title="Year of Creation",
        yaxis_title="Average OOP Purity Score",
        yaxis=dict(range=[0, 105]),
        template=_TEMPLATE,
        font=_FONT,
        height=450,
        margin=_MARGIN,
    )
    return pio.to_json(fig)


def stacked_bar_category_contribution(scored_repos: list[dict[str, Any]]) -> str:
    """Stacked horizontal bar chart showing category contribution per repo.

    Args:
        scored_repos: List of scored repo dictionaries.

    Returns:
        JSON string of the Plotly figure.
    """
    repos = _get_scored_only(scored_repos)
    if not repos:
        return _empty_figure("No scored repositories for stacked chart")

    # Sort by total score descending (rendered bottom-to-top)
    repos_sorted = sorted(repos, key=lambda r: r["total_score"])
    repo_names = [r["full_name"] for r in repos_sorted]

    categories = list(CATEGORY_LABELS.keys())
    cat_colors = [
        "#4a90e2", "#e74c3c", "#2ecc71", "#f39c12",
        "#9b59b6", "#1abc9c", "#e67e22",
    ]

    fig = go.Figure()
    for i, cat in enumerate(categories):
        cat_label = CATEGORY_LABELS[cat]
        cat_max = CATEGORY_MAX[cat]
        values = [r["category_scores"].get(cat, 0) for r in repos_sorted]
        percentages = [
            round((v / cat_max) * 100, 1) for v in values
        ]

        fig.add_trace(
            go.Bar(
                name=f"{cat}: {cat_label}",
                y=repo_names,
                x=values,
                orientation="h",
                marker_color=cat_colors[i % len(cat_colors)],
                hovertemplate=(
                    f"{cat_label}<br>"
                    "Score: %{x}/" + str(cat_max) + "<br>"
                    "Percentage: %{customdata:.1f}%<extra></extra>"
                ),
                customdata=percentages,
            )
        )

    fig.update_layout(
        title="Category Contribution to Total OOP Purity Score per Repository",
        xaxis_title="Score",
        barmode="stack",
        template=_TEMPLATE,
        font=_FONT,
        height=max(400, len(repos_sorted) * 35 + 100),
        margin=dict(l=200, r=40, t=60, b=60),
    )
    return pio.to_json(fig)
