"""
Stats model — raw aggregation queries for the statistics endpoints.

All methods accept user_id so data is always scoped to one user.
The "latest prediction per email" CTE pattern is used throughout:
    latest_preds AS (
        SELECT MAX(id) AS id, email_id FROM predictions GROUP BY email_id
    )
This gives one prediction row per email (the most recent analysis).
"""

from app.db.session import get_db


# ---------------------------------------------------------------------------
# Helper CTE strings (composed into each query below)
# ---------------------------------------------------------------------------

# Latest *original* prediction id per email  →  join on p.id = lp.id
# Excludes input_source='translated_body' so dashboard stats stay in sync
# with the inbox view, which also shows the original-body prediction
# (see Prediction.get_latest_original_by_email_id).
_LATEST_PRED_CTE = """
    WITH latest_preds AS (
        SELECT MAX(id) AS id, email_id
        FROM predictions
        WHERE input_source != 'translated_body'
        GROUP BY email_id
    )
"""


class StatsModel:
    """Aggregation queries for statistics endpoints."""

    # ------------------------------------------------------------------ #
    # 1. Overview                                                          #
    # ------------------------------------------------------------------ #

    @staticmethod
    def get_overview(user_id: int) -> dict:
        """
        Return a high-level summary for *user_id*:
          total_emails, phishing_count, suspicious_count, legitimate_count,
          unanalyzed_count, threat_rate (phishing+suspicious / total * 100)
        """
        sql = (
            _LATEST_PRED_CTE
            + """
        SELECT
            COUNT(e.id)                                                         AS total_emails,
            SUM(CASE WHEN p.classification = 'PHISHING'   THEN 1 ELSE 0 END)  AS phishing_count,
            SUM(CASE WHEN p.classification = 'SUSPICIOUS' THEN 1 ELSE 0 END)  AS suspicious_count,
            SUM(CASE WHEN p.classification = 'LEGITIMATE' THEN 1 ELSE 0 END)  AS legitimate_count,
            SUM(CASE WHEN lp.id IS NULL                   THEN 1 ELSE 0 END)  AS unanalyzed_count,
            ROUND(
                100.0 * SUM(CASE WHEN p.classification IN ('PHISHING','SUSPICIOUS') THEN 1 ELSE 0 END)
                / NULLIF(COUNT(CASE WHEN lp.id IS NOT NULL THEN 1 END), 0),
                2
            )                                                                   AS threat_rate
        FROM emails e
        LEFT JOIN latest_preds lp ON e.id = lp.email_id
        LEFT JOIN predictions p   ON lp.id = p.id
        WHERE e.user_id = ?
        """
        )
        with get_db() as conn:
            row = conn.execute(sql, (user_id,)).fetchone()
            if not row:
                return {}
            d = dict(row)
            # Fill None → 0 for numeric fields
            for k in (
                "phishing_count",
                "suspicious_count",
                "legitimate_count",
                "unanalyzed_count",
            ):
                d[k] = d[k] or 0
            d["threat_rate"] = d.get("threat_rate") or 0.0
            return d

    @staticmethod
    def get_vt_overview(user_id: int) -> dict:
        """Link risk summary derived from prediction_links (risk_score thresholds)."""
        sql = """
        SELECT
            COUNT(*)                                                                     AS total_links,
            SUM(CASE WHEN pl.risk_score >= 0.7 THEN 1 ELSE 0 END)                      AS malicious_links,
            SUM(CASE WHEN pl.risk_score >= 0.5 AND pl.risk_score < 0.7 THEN 1 ELSE 0 END) AS suspicious_links,
            COALESCE(SUM(CASE WHEN pl.risk_score >= 0.7 THEN ROUND(pl.risk_score * 10) ELSE 0 END), 0) AS total_malicious_votes,
            COALESCE(AVG(CASE WHEN pl.risk_score >= 0.7 THEN pl.risk_score END), 0.0)  AS avg_malicious_votes
        FROM prediction_links pl
        JOIN predictions p ON pl.prediction_id = p.id
        JOIN emails e      ON p.email_id = e.id
        WHERE e.user_id = ?
        """
        with get_db() as conn:
            row = conn.execute(sql, (user_id,)).fetchone()
            return dict(row) if row else {}

    # ------------------------------------------------------------------ #
    # 2. Daily trend                                                       #
    # ------------------------------------------------------------------ #

    @staticmethod
    def get_daily_trend(user_id: int, days: int = 30) -> list[dict]:
        """
        Per-day breakdown of emails by classification for the last *days* days.
        Returns list sorted by date ASC, with zero-fill gaps omitted
        (front-end should fill missing dates with zeros).
        """
        sql = (
            _LATEST_PRED_CTE
            + """
        SELECT
            date(e.received_at)                                                AS date,
            COUNT(e.id)                                                        AS total,
            SUM(CASE WHEN p.classification = 'PHISHING'   THEN 1 ELSE 0 END) AS phishing,
            SUM(CASE WHEN p.classification = 'SUSPICIOUS' THEN 1 ELSE 0 END) AS suspicious,
            SUM(CASE WHEN p.classification = 'LEGITIMATE' THEN 1 ELSE 0 END) AS legitimate,
            SUM(CASE WHEN lp.id IS NULL                   THEN 1 ELSE 0 END) AS unanalyzed
        FROM emails e
        LEFT JOIN latest_preds lp ON e.id = lp.email_id
        LEFT JOIN predictions p   ON lp.id = p.id
        WHERE e.user_id = ?
          AND date(e.received_at) >= date('now', ? || ' days')
        GROUP BY date(e.received_at)
        ORDER BY date ASC
        """
        )
        with get_db() as conn:
            rows = conn.execute(sql, (user_id, f"-{days}")).fetchall()
            return [dict(r) for r in rows]

    # ------------------------------------------------------------------ #
    # 3. Classification breakdown                                          #
    # ------------------------------------------------------------------ #

    @staticmethod
    def get_classification_breakdown(user_id: int) -> list[dict]:
        """
        Counts and average probability per classification label.
        Returns list of {classification, count, avg_probability, avg_ensemble_score}.
        """
        sql = (
            _LATEST_PRED_CTE
            + """
        SELECT
            COALESCE(p.classification, 'UNANALYZED')  AS classification,
            COUNT(e.id)                                AS count,
            ROUND(AVG(p.probability), 4)               AS avg_probability,
            ROUND(AVG(p.ensemble_score), 4)            AS avg_ensemble_score
        FROM emails e
        LEFT JOIN latest_preds lp ON e.id = lp.email_id
        LEFT JOIN predictions p   ON lp.id = p.id
        WHERE e.user_id = ?
        GROUP BY p.classification
        ORDER BY count DESC
        """
        )
        with get_db() as conn:
            rows = conn.execute(sql, (user_id,)).fetchall()
            return [dict(r) for r in rows]

    # ------------------------------------------------------------------ #
    # 4. Top senders                                                       #
    # ------------------------------------------------------------------ #

    @staticmethod
    def get_top_senders(user_id: int, limit: int = 10) -> list[dict]:
        """
        Top email senders ranked by (phishing_count DESC, total DESC).
        Returns {sender, total_emails, phishing_count, suspicious_count,
                 legitimate_count, max_probability}.
        """
        sql = (
            _LATEST_PRED_CTE
            + """
        SELECT
            e.sender,
            COUNT(e.id)                                                        AS total_emails,
            SUM(CASE WHEN p.classification = 'PHISHING'   THEN 1 ELSE 0 END) AS phishing_count,
            SUM(CASE WHEN p.classification = 'SUSPICIOUS' THEN 1 ELSE 0 END) AS suspicious_count,
            SUM(CASE WHEN p.classification = 'LEGITIMATE' THEN 1 ELSE 0 END) AS legitimate_count,
            ROUND(MAX(p.probability), 4)                                       AS max_probability
        FROM emails e
        LEFT JOIN latest_preds lp ON e.id = lp.email_id
        LEFT JOIN predictions p   ON lp.id = p.id
        WHERE e.user_id = ?
          AND e.sender IS NOT NULL AND e.sender != ''
        GROUP BY e.sender
        ORDER BY phishing_count DESC, suspicious_count DESC, total_emails DESC
        LIMIT ?
        """
        )
        with get_db() as conn:
            rows = conn.execute(sql, (user_id, limit)).fetchall()
            return [dict(r) for r in rows]

    # ------------------------------------------------------------------ #
    # 5. Top sender domains                                                #
    # ------------------------------------------------------------------ #

    @staticmethod
    def get_top_domains(user_id: int, limit: int = 10) -> list[dict]:
        """
        Top sender domains extracted from prediction_features.sender_domain.
        Returns {sender_domain, total, phishing_count, suspicious_count,
                 legitimate_count, dominant_risk}.
        """
        sql = (
            _LATEST_PRED_CTE
            + """
        SELECT
            pf.sender_domain,
            COUNT(*)                                                           AS total,
            SUM(CASE WHEN p.classification = 'PHISHING'   THEN 1 ELSE 0 END) AS phishing_count,
            SUM(CASE WHEN p.classification = 'SUSPICIOUS' THEN 1 ELSE 0 END) AS suspicious_count,
            SUM(CASE WHEN p.classification = 'LEGITIMATE' THEN 1 ELSE 0 END) AS legitimate_count,
            -- most common sender_risk for this domain
            (
                SELECT pf2.sender_risk
                FROM prediction_features pf2
                JOIN predictions p2 ON pf2.prediction_id = p2.id
                JOIN emails e2 ON p2.email_id = e2.id
                WHERE e2.user_id = ? AND pf2.sender_domain = pf.sender_domain
                GROUP BY pf2.sender_risk
                ORDER BY COUNT(*) DESC
                LIMIT 1
            ) AS dominant_risk
        FROM prediction_features pf
        JOIN predictions p  ON pf.prediction_id = p.id
        JOIN latest_preds lp ON p.email_id = lp.email_id AND p.id = lp.id
        JOIN emails e       ON p.email_id = e.id
        WHERE e.user_id = ?
          AND pf.sender_domain IS NOT NULL AND pf.sender_domain != ''
        GROUP BY pf.sender_domain
        ORDER BY phishing_count DESC, suspicious_count DESC, total DESC
        LIMIT ?
        """
        )
        with get_db() as conn:
            rows = conn.execute(sql, (user_id, user_id, limit)).fetchall()
            return [dict(r) for r in rows]

    # ------------------------------------------------------------------ #
    # 6. Feature statistics                                                #
    # ------------------------------------------------------------------ #

    @staticmethod
    def get_feature_stats(user_id: int) -> dict:
        """
        Aggregate ML feature values across all latest predictions.
        Returns {total_analyzed, avg_links_count, max_links_count,
                 emails_with_attachment, emails_with_urgent_keywords,
                 emails_with_attachment_pct, emails_with_urgent_keywords_pct,
                 sender_risk_breakdown: [{sender_risk, count}]}
        """
        agg_sql = (
            _LATEST_PRED_CTE
            + """
        SELECT
            COUNT(*)                              AS total_analyzed,
            ROUND(AVG(pf.links_count), 2)         AS avg_links_count,
            MAX(pf.links_count)                   AS max_links_count,
            SUM(pf.has_attachment)                AS emails_with_attachment,
            SUM(pf.urgent_keywords)               AS emails_with_urgent_keywords
        FROM prediction_features pf
        JOIN predictions p   ON pf.prediction_id = p.id
        JOIN latest_preds lp ON p.email_id = lp.email_id AND p.id = lp.id
        JOIN emails e        ON p.email_id = e.id
        WHERE e.user_id = ?
        """
        )

        risk_sql = (
            _LATEST_PRED_CTE
            + """
        SELECT
            pf.sender_risk,
            COUNT(*) AS count
        FROM prediction_features pf
        JOIN predictions p   ON pf.prediction_id = p.id
        JOIN latest_preds lp ON p.email_id = lp.email_id AND p.id = lp.id
        JOIN emails e        ON p.email_id = e.id
        WHERE e.user_id = ?
          AND pf.sender_risk IS NOT NULL AND pf.sender_risk != ''
        GROUP BY pf.sender_risk
        ORDER BY count DESC
        """
        )

        # links_count distribution buckets (0, 1-3, 4-10, 10+)
        links_dist_sql = (
            _LATEST_PRED_CTE
            + """
        SELECT
            CASE
                WHEN pf.links_count = 0           THEN '0'
                WHEN pf.links_count BETWEEN 1 AND 3 THEN '1-3'
                WHEN pf.links_count BETWEEN 4 AND 10 THEN '4-10'
                ELSE '10+'
            END AS bucket,
            COUNT(*) AS count
        FROM prediction_features pf
        JOIN predictions p   ON pf.prediction_id = p.id
        JOIN latest_preds lp ON p.email_id = lp.email_id AND p.id = lp.id
        JOIN emails e        ON p.email_id = e.id
        WHERE e.user_id = ?
        GROUP BY bucket
        ORDER BY MIN(pf.links_count)
        """
        )

        with get_db() as conn:
            agg = dict(conn.execute(agg_sql, (user_id,)).fetchone() or {})
            risk_rows = conn.execute(risk_sql, (user_id,)).fetchall()
            links_rows = conn.execute(links_dist_sql, (user_id,)).fetchall()

        total = agg.get("total_analyzed") or 0
        agg["sender_risk_breakdown"] = [dict(r) for r in risk_rows]
        agg["links_count_distribution"] = [dict(r) for r in links_rows]

        # Percentage helpers
        att = agg.get("emails_with_attachment") or 0
        urg = agg.get("emails_with_urgent_keywords") or 0
        agg["emails_with_attachment_pct"] = (
            round(att / total * 100, 2) if total else 0.0
        )
        agg["emails_with_urgent_keywords_pct"] = (
            round(urg / total * 100, 2) if total else 0.0
        )

        return agg

    # ------------------------------------------------------------------ #
    # 7. Suspicious segments                                               #
    # ------------------------------------------------------------------ #

    @staticmethod
    def get_segment_stats(user_id: int) -> dict:
        """
        Suspicious segment severity breakdown and top-scoring segments.
        Returns {severity_breakdown: [{severity, count, avg_score, max_score}],
                 top_segments: [{text, score, severity, reasons, email_id}]}
        """
        breakdown_sql = (
            _LATEST_PRED_CTE
            + """
        SELECT
            ss.severity,
            COUNT(*)               AS count,
            ROUND(AVG(ss.score), 2) AS avg_score,
            ROUND(MAX(ss.score), 2) AS max_score
        FROM suspicious_segments ss
        JOIN predictions p   ON ss.prediction_id = p.id
        JOIN latest_preds lp ON p.email_id = lp.email_id AND p.id = lp.id
        JOIN emails e        ON p.email_id = e.id
        WHERE e.user_id = ?
        GROUP BY ss.severity
        ORDER BY
            CASE ss.severity
                WHEN 'HIGH'   THEN 1
                WHEN 'MEDIUM' THEN 2
                WHEN 'LOW'    THEN 3
                ELSE 4
            END
        """
        )

        top_sql = (
            _LATEST_PRED_CTE
            + """
        SELECT
            ss.text,
            ROUND(ss.score, 2) AS score,
            ss.severity,
            ss.reasons,
            e.id AS email_id,
            e.subject
        FROM suspicious_segments ss
        JOIN predictions p   ON ss.prediction_id = p.id
        JOIN latest_preds lp ON p.email_id = lp.email_id AND p.id = lp.id
        JOIN emails e        ON p.email_id = e.id
        WHERE e.user_id = ?
        ORDER BY ss.score DESC
        LIMIT 10
        """
        )

        with get_db() as conn:
            b_rows = conn.execute(breakdown_sql, (user_id,)).fetchall()
            t_rows = conn.execute(top_sql, (user_id,)).fetchall()

        return {
            "severity_breakdown": [dict(r) for r in b_rows],
            "top_segments": [dict(r) for r in t_rows],
        }

    # ------------------------------------------------------------------ #
    # 8. VirusTotal link stats                                             #
    # ------------------------------------------------------------------ #

    @staticmethod
    def get_link_stats(user_id: int, top_n: int = 10) -> dict:
        """
        Link risk aggregates from prediction_links (risk_score thresholds).
        Returns {total_links, malicious_links, suspicious_links,
                 clean_links, total_malicious_votes, top_malicious: [...]}
        malicious  → risk_score >= 0.7
        suspicious → 0.5 <= risk_score < 0.7
        clean      → risk_score < 0.5
        """
        agg_sql = """
        SELECT
            COUNT(*)                                                                          AS total_links,
            SUM(CASE WHEN pl.risk_score >= 0.7 THEN 1 ELSE 0 END)                           AS malicious_links,
            SUM(CASE WHEN pl.risk_score >= 0.5 AND pl.risk_score < 0.7 THEN 1 ELSE 0 END)  AS suspicious_links,
            SUM(CASE WHEN pl.risk_score < 0.5 THEN 1 ELSE 0 END)                            AS clean_links,
            COALESCE(SUM(CASE WHEN pl.risk_score >= 0.7 THEN ROUND(pl.risk_score * 10) ELSE 0 END), 0) AS total_malicious_votes
        FROM prediction_links pl
        JOIN predictions p ON pl.prediction_id = p.id
        JOIN emails e      ON p.email_id = e.id
        WHERE e.user_id = ?
        """

        top_sql = """
        SELECT
            pl.url,
            pl.domain,
            pl.link_type,
            ROUND(pl.risk_score, 3) AS risk_score,
            pl.created_at           AS last_checked_at
        FROM prediction_links pl
        JOIN predictions p ON pl.prediction_id = p.id
        JOIN emails e      ON p.email_id = e.id
        WHERE e.user_id = ? AND pl.risk_score >= 0.7
        ORDER BY pl.risk_score DESC
        LIMIT ?
        """

        with get_db() as conn:
            agg = dict(conn.execute(agg_sql, (user_id,)).fetchone() or {})
            top_rows = conn.execute(top_sql, (user_id, top_n)).fetchall()

        agg["top_malicious"] = [dict(r) for r in top_rows]
        return agg

    # ------------------------------------------------------------------ #
    # 9. Receive-volume timeline                                           #
    # ------------------------------------------------------------------ #

    @staticmethod
    def get_timeline(user_id: int, days: int = 90) -> list[dict]:
        """
        Email receive-volume per day for the last *days* days.
        Returns [{date, email_count}] sorted ASC.
        """
        sql = """
        SELECT
            date(received_at) AS date,
            COUNT(*)          AS email_count
        FROM emails
        WHERE user_id = ?
          AND date(received_at) >= date('now', ? || ' days')
        GROUP BY date(received_at)
        ORDER BY date ASC
        """
        with get_db() as conn:
            rows = conn.execute(sql, (user_id, f"-{days}")).fetchall()
            return [dict(r) for r in rows]

    # ------------------------------------------------------------------ #
    # 10. Probability score distribution                                   #
    # ------------------------------------------------------------------ #

    @staticmethod
    def get_probability_distribution(user_id: int) -> list[dict]:
        """
        Histogram of ML probability scores in 0.1-wide buckets.
        Returns [{bucket_label, count, pct}] (e.g. '0.0-0.1', '0.1-0.2', ...).
        """
        sql = (
            _LATEST_PRED_CTE
            + """
        SELECT
            CASE
                WHEN p.probability < 0.1 THEN '0.0-0.1'
                WHEN p.probability < 0.2 THEN '0.1-0.2'
                WHEN p.probability < 0.3 THEN '0.2-0.3'
                WHEN p.probability < 0.4 THEN '0.3-0.4'
                WHEN p.probability < 0.5 THEN '0.4-0.5'
                WHEN p.probability < 0.6 THEN '0.5-0.6'
                WHEN p.probability < 0.7 THEN '0.6-0.7'
                WHEN p.probability < 0.8 THEN '0.7-0.8'
                WHEN p.probability < 0.9 THEN '0.8-0.9'
                ELSE '0.9-1.0'
            END AS bucket,
            COUNT(*) AS count
        FROM predictions p
        JOIN latest_preds lp ON p.email_id = lp.email_id AND p.id = lp.id
        JOIN emails e        ON p.email_id = e.id
        WHERE e.user_id = ?
        GROUP BY bucket
        ORDER BY MIN(p.probability)
        """
        )
        with get_db() as conn:
            rows = conn.execute(sql, (user_id,)).fetchall()
            total = sum(r["count"] for r in rows)
            return [
                {**dict(r), "pct": round(r["count"] / total * 100, 2) if total else 0.0}
                for r in rows
            ]
