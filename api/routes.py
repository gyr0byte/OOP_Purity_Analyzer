from flask import Blueprint, jsonify, request, url_for
from core import scraper, scorer
from core.database import db, save_analysis, Analysis, RepoResult
from core.scores_db import LANGUAGE_SCORES, CATEGORY_LABELS, CATEGORY_MAX

api_bp = Blueprint("api", __name__, url_prefix="/api/v1")

@api_bp.route("/languages", methods=["GET"])
def get_languages():
    """List all supported languages with their static base scores."""
    return jsonify({
        "languages": LANGUAGE_SCORES,
        "category_labels": CATEGORY_LABELS,
        "category_max": CATEGORY_MAX
    })

@api_bp.route("/history", methods=["GET"])
def get_history():
    """Get paginated list of past analyses."""
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 10, type=int)
    
    pagination = Analysis.query.order_by(Analysis.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    analyses_list = []
    for item in pagination.items:
        analyses_list.append(item.to_dict())

        
    return jsonify({
        "analyses": analyses_list,
        "page": page,
        "per_page": per_page,
        "total": pagination.total,
        "has_next": pagination.has_next,
        "has_prev": pagination.has_prev
    })

@api_bp.route("/analyze", methods=["POST"])
def analyze():
    """Submit an analysis query via JSON body."""
    data = request.get_json() or {}
    mode = data.get("mode")
    input_data = data.get("input_data")
    limit = data.get("limit", 20)

    if not mode or not input_data:
        return jsonify({"error": "Missing 'mode' or 'input_data' in request body."}), 400

    if mode not in ("urls", "search", "user"):
        return jsonify({"error": "Invalid mode. Must be 'urls', 'search', or 'user'."}), 400

    try:
        # Scrape and score
        repos = scraper.scrape(mode, input_data, limit)
        if not repos:
            return jsonify({"error": "No repositories found for input."}), 404

        scored_repos, summary = scorer.score_all(repos)
        analysis_id = save_analysis(mode, input_data, scored_repos, summary)

        return jsonify({
            "analysis_id": analysis_id,
            "total_repos": summary.get("total_repos", 0),
            "scored_repos": summary.get("scored_repos", 0),
            "unscored_repos": summary.get("unscored_repos", 0),
            "results": scored_repos
        })

    except Exception as exc:
        return jsonify({"error": str(exc)}), 500

@api_bp.route("/score/<path:repo_name>", methods=["GET"])
def score_repo(repo_name):
    """Quick-score a single repository."""
    url = f"https://github.com/{repo_name}"
    try:
        repos = scraper.scrape("urls", url)
        if not repos:
            return jsonify({"error": f"Repository '{repo_name}' not found."}), 404

        scored_repos, summary = scorer.score_all(repos)
        if not scored_repos:
            return jsonify({"error": "Repository could not be scored."}), 400

        # Save to database for history tracking
        analysis_id = save_analysis("urls", url, scored_repos, summary)
        
        result = scored_repos[0]
        result["analysis_id"] = analysis_id
        return jsonify(result)

    except Exception as exc:
        return jsonify({"error": str(exc)}), 500
