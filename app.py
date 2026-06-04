"""Flask application entry point for the OOP Purity Analyzer.

Provides routes for the landing page, analysis processing, results dashboard,
scoring rubric reference, CSV export, analysis history, and health checks.
"""

import json
import logging
import os
import sys
from datetime import datetime
from io import StringIO
from typing import Any

import pandas as pd
from flask import (
    Flask,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
    jsonify,
)
from flask_session import Session
from werkzeug.exceptions import HTTPException

import config
from core import scraper, scorer, chart_builder
from core.database import db, init_db, save_analysis, Analysis, RepoResult
from core.scores_db import (
    CATEGORY_LABELS,
    CATEGORY_MAX,
    LANGUAGE_SCORES,
    PURITY_TIERS,
)

# ---------------------------------------------------------------------------
# Logging configuration
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.DEBUG if config.FLASK_ENV == "development" else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger: logging.Logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Flask application setup
# ---------------------------------------------------------------------------
app: Flask = Flask(__name__)
app.secret_key = config.SECRET_KEY

# Flask-Session configuration (filesystem backend for large payloads)
app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_FILE_DIR"] = config.SESSION_FILE_DIR
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_USE_SIGNER"] = True

# SQLite database configuration
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///oop_analyzer.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

Session(app)
init_db(app)

from api.routes import api_bp
app.register_blueprint(api_bp)


# Validate GitHub token on startup
try:
    scraper._get_github_client()
except Exception as exc:
    logger.error("GitHub token validation failed: %s", exc)
    raise ValueError(
        "GitHub token is missing or invalid. Set GITHUB_TOKEN in your .env file."
    ) from exc


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/", methods=["GET"])
def index() -> str:
    """Render the main landing page with the analysis input form.

    Returns:
        Rendered index.html template.
    """
    return render_template(
        "index.html",
        category_labels=CATEGORY_LABELS,
    )


@app.route("/analyze", methods=["POST"])
def analyze() -> Any:
    """Process the analysis form inputs, scrape repositories, score them, and redirect.

    Reads form fields (mode, input_data, limit), runs the scraper and scorer,
    stores results in the Flask session, and redirects to /results.

    Returns:
        Redirect to /results on success, or rendered error.html on failure.
    """
    try:
        mode: str = request.form.get("mode", "").strip()
        input_data: str = request.form.get("input_data", "").strip()
        limit_str: str = request.form.get("limit", str(config.DEFAULT_LIMIT))

        try:
            limit: int = min(int(limit_str), config.MAX_REPOS)
        except (ValueError, TypeError):
            limit = config.DEFAULT_LIMIT

        if not mode or not input_data:
            return render_template(
                "error.html",
                error_message="Please provide a valid input mode and data.",
            )

        logger.info("Starting analysis — mode: %s, limit: %d", mode, limit)

        # Scrape
        repos: list[dict[str, Any]] = scraper.scrape(mode, input_data, limit)
        if not repos:
            return render_template(
                "error.html",
                error_message="No repositories found. Check your input and try again.",
            )

        # Score
        scored_repos, summary = scorer.score_all(repos)

        # Persist to database
        analysis_id = save_analysis(mode, input_data, scored_repos, summary)
        logger.info("Analysis persisted with ID: %d", analysis_id)

        # Store in session as JSON-serializable data
        session["scored_repos"] = scored_repos
        session["summary"] = summary
        session["analysis_id"] = analysis_id

        logger.info(
            "Analysis complete — %d repos scored, %d unscored",
            summary["scored_repos"],
            summary["unscored_repos"],
        )

        return redirect(url_for("results"))

    except (ValueError, RuntimeError) as exc:
        logger.error("Analysis error: %s", exc)
        return render_template("error.html", error_message=str(exc))
    except Exception as exc:
        logger.exception("Unexpected error during analysis")
        return render_template(
            "error.html",
            error_message="An unexpected error occurred. Please try again.",
        )


@app.route("/results", methods=["GET"])
def results() -> Any:
    """Render the results dashboard with all charts and summary stats.

    Returns:
        Rendered results.html template, or redirect to / if no data.
    """
    scored_repos: list[dict[str, Any]] | None = session.get("scored_repos")
    summary: dict[str, Any] | None = session.get("summary")

    if not scored_repos or not summary:
        return redirect(url_for("index"))

    scored_only = [r for r in scored_repos if r.get("scored")]

    # Get unique languages for radar charts
    unique_languages = list(dict.fromkeys(
        r["matched_language"] for r in scored_only
    ))

    # Build all charts
    charts: dict[str, Any] = {
        "bar_total": chart_builder.bar_chart_total_scores(scored_repos),
        "heatmap": chart_builder.heatmap_subcriteria(scored_repos),
        "grouped_bar": chart_builder.grouped_bar_category_comparison(scored_repos),
        "treemap": chart_builder.treemap_repos_by_tier(scored_repos),
        "scatter": chart_builder.scatter_score_vs_stars(scored_repos),
        "donut": chart_builder.donut_tier_distribution(scored_repos),
        "timeline": chart_builder.line_chart_score_over_time(scored_repos),
        "stacked_bar": chart_builder.stacked_bar_category_contribution(scored_repos),
    }

    # Radar charts per language
    radar_charts: dict[str, str] = {}
    for lang in unique_languages:
        radar_charts[lang] = chart_builder.radar_chart_by_language(lang)

    # Find most common tier
    tier_dist = summary.get("tier_distribution", {})
    most_common_tier = max(
        tier_dist, key=tier_dist.get) if tier_dist else "N/A"

    return render_template(
        "results.html",
        scored_repos=scored_repos,
        summary=summary,
        charts=charts,
        radar_charts=radar_charts,
        most_common_tier=most_common_tier,
        category_labels=CATEGORY_LABELS,
        analysis_id=session.get("analysis_id"),
    )



@app.route("/rubric", methods=["GET"])
def rubric() -> str:
    """Render the complete OOP purity scoring rubric reference page.

    Returns:
        Rendered rubric.html template.
    """
    return render_template(
        "rubric.html",
        language_scores=LANGUAGE_SCORES,
        category_labels=CATEGORY_LABELS,
        category_max=CATEGORY_MAX,
        purity_tiers=PURITY_TIERS,
    )


@app.route("/export/csv", methods=["GET"])
def export_csv() -> Any:
    """Export successfully scored repos as a downloadable CSV file.

    Returns:
        CSV file attachment, or redirect to / if no data.
    """
    scored_repos: list[dict[str, Any]] | None = session.get("scored_repos")
    if not scored_repos:
        return redirect(url_for("index"))

    rows: list[dict[str, Any]] = []
    for repo in scored_repos:
        row: dict[str, Any] = {
            "name": repo.get("name", ""),
            "full_name": repo.get("full_name", ""),
            "url": repo.get("url", ""),
            "language": repo.get("matched_language", repo.get("primary_language", "")),
            "total_score": repo.get("total_score", ""),
            "purity_tier": repo.get("purity_tier", ""),
            "stars": repo.get("stars", ""),
            "forks": repo.get("forks", ""),
            "created_at": repo.get("created_at", ""),
        }
        # Add category scores
        cat_scores = repo.get("category_scores", {})
        for cat in CATEGORY_LABELS:
            row[cat] = cat_scores.get(cat, "")
        rows.append(row)

    df = pd.DataFrame(rows)
    # Replace NaN with empty string
    df = df.fillna("")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"oop_purity_results_{timestamp}.csv"

    csv_buffer = StringIO()
    df.to_csv(csv_buffer, index=False)
    csv_buffer.seek(0)

    from io import BytesIO
    bytes_buffer = BytesIO(csv_buffer.getvalue().encode("utf-8"))
    bytes_buffer.seek(0)

    return send_file(
        bytes_buffer,
        mimetype="text/csv",
        as_attachment=True,
        download_name=filename,
    )


@app.route("/export/pdf", methods=["GET"])
def export_active_pdf() -> Any:
    """Generate and download a PDF report for the active session's analysis."""
    analysis_id = session.get("analysis_id")
    if not analysis_id:
        return redirect(url_for("index"))
    return redirect(url_for("export_analysis_pdf", analysis_id=analysis_id))


@app.route("/history/<int:analysis_id>/export/pdf", methods=["GET"])
def export_analysis_pdf(analysis_id: int) -> Any:
    """Generate and download a PDF report for a specific saved analysis by ID."""
    analysis = Analysis.query.get_or_404(analysis_id)
    analysis_dict = analysis.to_dict()
    repos = [r.to_dict() for r in analysis.repo_results]

    from core.report_generator import generate_pdf_report
    pdf_bytes = generate_pdf_report(analysis_dict, repos)

    from io import BytesIO
    filename = f"oop_purity_report_analysis_{analysis_id}.pdf"
    return send_file(
        BytesIO(pdf_bytes),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=filename,
    )



@app.route("/history", methods=["GET"])
def history() -> str:
    """Render the analysis history page with all past runs.

    Returns:
        Rendered history.html template.
    """
    page = request.args.get("page", 1, type=int)
    per_page = 12
    pagination = Analysis.query.order_by(Analysis.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    analyses = pagination.items
    return render_template(
        "history.html",
        analyses=analyses,
        pagination=pagination,
    )


@app.route("/history/<int:analysis_id>", methods=["GET"])
def history_detail(analysis_id: int) -> Any:
    """Load a past analysis from the database and render its results dashboard.

    Args:
        analysis_id: The ID of the analysis to view.

    Returns:
        Rendered results.html template, or 404 error.
    """
    analysis = Analysis.query.get_or_404(analysis_id)
    scored_repos = [r.to_dict() for r in analysis.repo_results]
    import json
    summary = json.loads(analysis.summary_json) if analysis.summary_json else {}

    scored_only = [r for r in scored_repos if r.get("scored")]

    # Get unique languages for radar charts
    unique_languages = list(dict.fromkeys(
        r["matched_language"] for r in scored_only
    ))

    # Build all charts
    charts: dict[str, Any] = {
        "bar_total": chart_builder.bar_chart_total_scores(scored_repos),
        "heatmap": chart_builder.heatmap_subcriteria(scored_repos),
        "grouped_bar": chart_builder.grouped_bar_category_comparison(scored_repos),
        "treemap": chart_builder.treemap_repos_by_tier(scored_repos),
        "scatter": chart_builder.scatter_score_vs_stars(scored_repos),
        "donut": chart_builder.donut_tier_distribution(scored_repos),
        "timeline": chart_builder.line_chart_score_over_time(scored_repos),
        "stacked_bar": chart_builder.stacked_bar_category_contribution(scored_repos),
    }

    # Radar charts per language
    radar_charts: dict[str, str] = {}
    for lang in unique_languages:
        radar_charts[lang] = chart_builder.radar_chart_by_language(lang)

    # Find most common tier
    tier_dist = summary.get("tier_distribution", {})
    most_common_tier = max(
        tier_dist, key=tier_dist.get) if tier_dist else "N/A"

    return render_template(
        "results.html",
        scored_repos=scored_repos,
        summary=summary,
        charts=charts,
        radar_charts=radar_charts,
        most_common_tier=most_common_tier,
        category_labels=CATEGORY_LABELS,
        analysis_id=analysis_id,
    )


@app.route("/compare", methods=["GET"])
def compare() -> Any:
    """Compare selected repositories side-by-side."""
    ids_str = request.args.get("ids", "")
    if not ids_str:
        return redirect(url_for("history"))

    try:
        repo_ids = [int(i.strip()) for i in ids_str.split(",") if i.strip()]
    except ValueError:
        return render_template(
            "error.html",
            error_message="Invalid repository IDs specified for comparison.",
        )

    if len(repo_ids) < 2 or len(repo_ids) > 4:
        return render_template(
            "error.html",
            error_message="Please select between 2 and 4 repositories to compare.",
        )

    repos = []
    for rid in repo_ids:
        repo_obj = RepoResult.query.get(rid)
        if repo_obj:
            repos.append(repo_obj.to_dict())

    if len(repos) < 2:
        return render_template(
            "error.html",
            error_message="Some of the selected repositories could not be loaded from the database.",
        )

    compare_radar = chart_builder.compare_repositories_radar(repos)
    compare_bar = chart_builder.compare_repositories_bar(repos)

    return render_template(
        "compare.html",
        repos=repos,
        compare_radar=compare_radar,
        compare_bar=compare_bar,
    )



@app.route("/health", methods=["GET"])
def health() -> Any:
    """Health check endpoint for deployment monitoring.

    Returns:
        JSON response with status 'ok'.
    """
    return jsonify({"status": "ok"})


@app.route("/favicon.ico", methods=["GET"])
def favicon() -> tuple[str, int]:
    """Return empty response for browser favicon requests."""
    return "", 204


# ---------------------------------------------------------------------------
# Global error handler
# ---------------------------------------------------------------------------

@app.errorhandler(Exception)
def handle_exception(exc: Exception) -> tuple[str, int]:
    """Catch all unhandled exceptions and render a user-friendly error page.

    Args:
        exc: The unhandled exception.

    Returns:
        Tuple of (rendered error page, HTTP status code).
    """
    if isinstance(exc, HTTPException):
        # Preserve HTTP error codes like 404 instead of converting them to 500.
        return render_template(
            "error.html",
            error_message=exc.description,
        ), exc.code or 500

    logger.exception("Unhandled exception: %s", exc)
    return render_template(
        "error.html",
        error_message="An unexpected error occurred. Please try again later.",
    ), 500


# ---------------------------------------------------------------------------
# Application entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app.run(
        debug=(config.FLASK_ENV == "development"),
        host="0.0.0.0",
        port=5000,
    )
