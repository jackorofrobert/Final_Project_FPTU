"""
Statistics service — orchestrates aggregation queries and enriches results.
"""

from app.models.stats import StatsModel
from app.utils.logger import get_logger

logger = get_logger(__name__)


class StatsService:
    """Service layer for all statistics endpoints."""

    # ------------------------------------------------------------------ #
    # Overview                                                             #
    # ------------------------------------------------------------------ #

    @staticmethod
    def get_overview(user_id: int) -> dict:
        """
        Full dashboard overview combining email stats + VT summary.
        """
        logger.debug(f"Building overview stats [user_id={user_id}]")
        email_stats = StatsModel.get_overview(user_id)
        vt_stats = StatsModel.get_vt_overview(user_id)

        total = email_stats.get("total_emails", 0)
        analyzed = total - email_stats.get("unanalyzed_count", 0)

        return {
            "emails": {
                "total": total,
                "analyzed": analyzed,
                "unanalyzed": email_stats.get("unanalyzed_count", 0),
                "analysis_rate": round(analyzed / total * 100, 2) if total else 0.0,
            },
            "threats": {
                "phishing": email_stats.get("phishing_count", 0),
                "suspicious": email_stats.get("suspicious_count", 0),
                "legitimate": email_stats.get("legitimate_count", 0),
                "threat_rate": email_stats.get("threat_rate", 0.0),
            },
            "virustotal": {
                "total_links": vt_stats.get("total_links", 0) or 0,
                "malicious_links": vt_stats.get("malicious_links", 0) or 0,
                "suspicious_links": vt_stats.get("suspicious_links", 0) or 0,
                "total_malicious_votes": vt_stats.get("total_malicious_votes", 0) or 0,
            },
        }

    # ------------------------------------------------------------------ #
    # Trend                                                                #
    # ------------------------------------------------------------------ #

    @staticmethod
    def get_daily_trend(user_id: int, days: int = 30) -> dict:
        """Daily email counts by classification, capped to 365 days."""
        days = min(max(days, 1), 365)
        logger.debug(f"Building daily trend [user_id={user_id}] [days={days}]")
        rows = StatsModel.get_daily_trend(user_id, days)
        return {"days": days, "data": rows}

    # ------------------------------------------------------------------ #
    # Classification breakdown                                             #
    # ------------------------------------------------------------------ #

    @staticmethod
    def get_classification_breakdown(user_id: int) -> dict:
        """Phishing / Suspicious / Legitimate / Unanalyzed breakdown."""
        logger.debug(f"Building classification breakdown [user_id={user_id}]")
        rows = StatsModel.get_classification_breakdown(user_id)
        total = sum(r["count"] for r in rows)

        # Attach percentage
        for r in rows:
            r["pct"] = round(r["count"] / total * 100, 2) if total else 0.0

        return {"total": total, "breakdown": rows}

    # ------------------------------------------------------------------ #
    # Top senders                                                          #
    # ------------------------------------------------------------------ #

    @staticmethod
    def get_top_senders(user_id: int, limit: int = 10) -> dict:
        """Top senders ranked by threat count."""
        limit = min(max(limit, 1), 100)
        logger.debug(f"Building top senders [user_id={user_id}] [limit={limit}]")
        rows = StatsModel.get_top_senders(user_id, limit)
        return {"limit": limit, "senders": rows}

    # ------------------------------------------------------------------ #
    # Top domains                                                          #
    # ------------------------------------------------------------------ #

    @staticmethod
    def get_top_domains(user_id: int, limit: int = 10) -> dict:
        """Top sender domains ranked by threat count."""
        limit = min(max(limit, 1), 100)
        logger.debug(f"Building top domains [user_id={user_id}] [limit={limit}]")
        rows = StatsModel.get_top_domains(user_id, limit)
        return {"limit": limit, "domains": rows}

    # ------------------------------------------------------------------ #
    # ML feature stats                                                     #
    # ------------------------------------------------------------------ #

    @staticmethod
    def get_feature_stats(user_id: int) -> dict:
        """Aggregate ML-extracted feature metrics."""
        logger.debug(f"Building feature stats [user_id={user_id}]")
        return StatsModel.get_feature_stats(user_id)

    # ------------------------------------------------------------------ #
    # Suspicious segments                                                  #
    # ------------------------------------------------------------------ #

    @staticmethod
    def get_segment_stats(user_id: int) -> dict:
        """Suspicious segment severity breakdown + top scoring segments."""
        logger.debug(f"Building segment stats [user_id={user_id}]")
        return StatsModel.get_segment_stats(user_id)

    # ------------------------------------------------------------------ #
    # VT link stats                                                        #
    # ------------------------------------------------------------------ #

    @staticmethod
    def get_link_stats(user_id: int, top_n: int = 10) -> dict:
        """VirusTotal link aggregates + top malicious URLs."""
        top_n = min(max(top_n, 1), 50)
        logger.debug(f"Building link stats [user_id={user_id}] [top_n={top_n}]")
        return StatsModel.get_link_stats(user_id, top_n)

    # ------------------------------------------------------------------ #
    # Timeline                                                             #
    # ------------------------------------------------------------------ #

    @staticmethod
    def get_timeline(user_id: int, days: int = 90) -> dict:
        """Email receive-volume per day over the last N days."""
        days = min(max(days, 1), 365)
        logger.debug(f"Building timeline [user_id={user_id}] [days={days}]")
        rows = StatsModel.get_timeline(user_id, days)
        return {"days": days, "data": rows}

    # ------------------------------------------------------------------ #
    # Probability distribution                                             #
    # ------------------------------------------------------------------ #

    @staticmethod
    def get_probability_distribution(user_id: int) -> dict:
        """Histogram of ML probability scores in 0.1-wide buckets."""
        logger.debug(f"Building probability distribution [user_id={user_id}]")
        buckets = StatsModel.get_probability_distribution(user_id)
        return {"buckets": buckets}
