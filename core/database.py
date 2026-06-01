"""Database models and initialization for the OOP Purity Analyzer.

Uses Flask-SQLAlchemy with SQLite to persist analysis runs and
individual repository results for history tracking and comparison.
"""

import json
from datetime import datetime, timezone
from typing import Any

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Analysis(db.Model):
    """A single analysis run submitted by the user."""

    __tablename__ = "analyses"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    mode = db.Column(db.String(20), nullable=False)
    input_data = db.Column(db.Text, nullable=False)
    total_repos = db.Column(db.Integer, default=0)
    scored_repos_count = db.Column(db.Integer, default=0)
    unscored_repos_count = db.Column(db.Integer, default=0)
    summary_json = db.Column(db.Text, default="{}")

    # Relationship to repo results
    repo_results = db.relationship(
        "RepoResult", backref="analysis", lazy=True, cascade="all, delete-orphan"
    )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a dictionary for template rendering."""
        return {
            "id": self.id,
            "created_at": self.created_at.isoformat() if self.created_at else "",
            "mode": self.mode,
            "input_data": self.input_data,
            "total_repos": self.total_repos,
            "scored_repos_count": self.scored_repos_count,
            "unscored_repos_count": self.unscored_repos_count,
            "summary": json.loads(self.summary_json) if self.summary_json else {},
        }


class RepoResult(db.Model):
    """Scored result for a single repository within an analysis."""

    __tablename__ = "repo_results"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    analysis_id = db.Column(
        db.Integer, db.ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False
    )
    full_name = db.Column(db.String(256), nullable=False)
    name = db.Column(db.String(128), default="")
    url = db.Column(db.String(512), default="")
    description = db.Column(db.Text, default="")
    primary_language = db.Column(db.String(64), default="Unknown")
    matched_language = db.Column(db.String(64), default="")
    total_score = db.Column(db.Integer, nullable=True)
    purity_tier = db.Column(db.String(32), default="")
    tier_color = db.Column(db.String(16), default="")
    scored = db.Column(db.Boolean, default=False)
    reason = db.Column(db.String(256), default="")
    stars = db.Column(db.Integer, default=0)
    forks = db.Column(db.Integer, default=0)
    open_issues = db.Column(db.Integer, default=0)
    created_at_repo = db.Column(db.String(64), default="")
    updated_at_repo = db.Column(db.String(64), default="")
    size_kb = db.Column(db.Integer, default=0)

    # JSON blobs for complex nested data
    category_scores_json = db.Column(db.Text, default="{}")
    category_percentages_json = db.Column(db.Text, default="{}")
    languages_scored_json = db.Column(db.Text, default="[]")
    languages_used_json = db.Column(db.Text, default="{}")
    sub_scores_json = db.Column(db.Text, default="{}")
    topics_json = db.Column(db.Text, default="[]")

    def to_dict(self) -> dict[str, Any]:
        """Reconstruct the full scored repo dictionary for template rendering."""
        return {
            "name": self.name,
            "full_name": self.full_name,
            "url": self.url,
            "description": self.description,
            "primary_language": self.primary_language,
            "matched_language": self.matched_language,
            "total_score": self.total_score,
            "total_percentage": round((self.total_score / 100) * 100, 2)
            if self.total_score
            else 0,
            "purity_tier": self.purity_tier,
            "tier_color": self.tier_color,
            "scored": self.scored,
            "reason": self.reason,
            "stars": self.stars,
            "forks": self.forks,
            "open_issues": self.open_issues,
            "created_at": self.created_at_repo,
            "updated_at": self.updated_at_repo,
            "size_kb": self.size_kb,
            "category_scores": json.loads(self.category_scores_json),
            "category_percentages": json.loads(self.category_percentages_json),
            "languages_scored": json.loads(self.languages_scored_json),
            "languages_used": json.loads(self.languages_used_json),
            "sub_scores": json.loads(self.sub_scores_json),
            "topics": json.loads(self.topics_json),
        }

    @classmethod
    def from_scored_repo(cls, analysis_id: int, repo: dict[str, Any]) -> "RepoResult":
        """Create a RepoResult from a scored repo dictionary."""
        return cls(
            analysis_id=analysis_id,
            full_name=repo.get("full_name", ""),
            name=repo.get("name", ""),
            url=repo.get("url", ""),
            description=repo.get("description", ""),
            primary_language=repo.get("primary_language", "Unknown"),
            matched_language=repo.get("matched_language", ""),
            total_score=repo.get("total_score"),
            purity_tier=repo.get("purity_tier", ""),
            tier_color=repo.get("tier_color", ""),
            scored=repo.get("scored", False),
            reason=repo.get("reason", ""),
            stars=repo.get("stars", 0),
            forks=repo.get("forks", 0),
            open_issues=repo.get("open_issues", 0),
            created_at_repo=repo.get("created_at", ""),
            updated_at_repo=repo.get("updated_at", ""),
            size_kb=repo.get("size_kb", 0),
            category_scores_json=json.dumps(repo.get("category_scores", {})),
            category_percentages_json=json.dumps(
                repo.get("category_percentages", {})
            ),
            languages_scored_json=json.dumps(repo.get("languages_scored", [])),
            languages_used_json=json.dumps(repo.get("languages_used", {})),
            sub_scores_json=json.dumps(repo.get("sub_scores", {})),
            topics_json=json.dumps(repo.get("topics", [])),
        )


def init_db(app):
    """Initialize the database and create all tables."""
    db.init_app(app)
    with app.app_context():
        db.create_all()


def save_analysis(
    mode: str,
    input_data: str,
    scored_repos: list[dict[str, Any]],
    summary: dict[str, Any],
) -> int:
    """Persist an analysis run and all its repo results to the database.

    Args:
        mode: The input mode ('urls', 'search', 'user').
        input_data: The raw input string.
        scored_repos: List of scored repo dictionaries.
        summary: The summary statistics dictionary.

    Returns:
        The ID of the newly created Analysis record.
    """
    analysis = Analysis(
        mode=mode,
        input_data=input_data,
        total_repos=summary.get("total_repos", 0),
        scored_repos_count=summary.get("scored_repos", 0),
        unscored_repos_count=summary.get("unscored_repos", 0),
        summary_json=json.dumps(summary),
    )
    db.session.add(analysis)
    db.session.flush()  # Get the ID before adding children

    for repo in scored_repos:
        repo_result = RepoResult.from_scored_repo(analysis.id, repo)
        db.session.add(repo_result)

    db.session.commit()
    return analysis.id
