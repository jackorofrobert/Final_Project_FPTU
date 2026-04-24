"""
Prediction detail models for storing analysis breakdown.
"""
from app.db.session import get_db


class PredictionFeature:
    """Model for prediction features."""
    
    @staticmethod
    def create(prediction_id: int, links_count: int, has_attachment: int, 
               urgent_keywords: int, sender_domain: str, sender_risk: str) -> dict:
        """Create prediction features record."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''INSERT INTO prediction_features 
                   (prediction_id, links_count, has_attachment, urgent_keywords, sender_domain, sender_risk) 
                   VALUES (?, ?, ?, ?, ?, ?)''',
                (prediction_id, links_count, has_attachment, urgent_keywords, sender_domain, sender_risk)
            )
            feature_id = cursor.lastrowid
            cursor.execute('SELECT * FROM prediction_features WHERE id = ?', (feature_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    @staticmethod
    def get_by_prediction_id(prediction_id: int) -> dict | None:
        """Get features by prediction ID."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM prediction_features WHERE prediction_id = ?', (prediction_id,))
            row = cursor.fetchone()
            return dict(row) if row else None


class PredictionLink:
    """Model for prediction links analysis."""
    
    @staticmethod
    def create(prediction_id: int, url: str, domain: str, link_type: str, risk_score: float) -> dict:
        """Create prediction link record."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''INSERT INTO prediction_links 
                   (prediction_id, url, domain, link_type, risk_score) 
                   VALUES (?, ?, ?, ?, ?)''',
                (prediction_id, url, domain, link_type, risk_score)
            )
            link_id = cursor.lastrowid
            cursor.execute('SELECT * FROM prediction_links WHERE id = ?', (link_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    @staticmethod
    def create_batch(prediction_id: int, links: list) -> list[dict]:
        """Create multiple link records."""
        results = []
        for link in links:
            result = PredictionLink.create(
                prediction_id,
                link.get('url', ''),
                link.get('domain', ''),
                link.get('type', 'NORMAL'),
                link.get('risk', 0.0)
            )
            if result:
                results.append(result)
        return results
    
    @staticmethod
    def get_by_prediction_id(prediction_id: int) -> list[dict]:
        """Get all links for a prediction."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM prediction_links WHERE prediction_id = ?', (prediction_id,))
            return [dict(row) for row in cursor.fetchall()]


class SuspiciousSegment:
    """Model for suspicious text segments."""
    
    @staticmethod
    def create(prediction_id: int, text: str, score: float, severity: str, reasons: str) -> dict:
        """Create suspicious segment record."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''INSERT INTO suspicious_segments 
                   (prediction_id, text, score, severity, reasons) 
                   VALUES (?, ?, ?, ?, ?)''',
                (prediction_id, text, score, severity, reasons)
            )
            segment_id = cursor.lastrowid
            cursor.execute('SELECT * FROM suspicious_segments WHERE id = ?', (segment_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    @staticmethod
    def create_batch(prediction_id: int, segments: list) -> list[dict]:
        """Create multiple segment records."""
        results = []
        for segment in segments:
            result = SuspiciousSegment.create(
                prediction_id,
                segment.get('text', ''),
                segment.get('score', 0.0),
                segment.get('severity', 'LOW'),
                segment.get('reasons', '')
            )
            if result:
                results.append(result)
        return results
    
    @staticmethod
    def get_by_prediction_id(prediction_id: int) -> list[dict]:
        """Get all suspicious segments for a prediction."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT * FROM suspicious_segments WHERE prediction_id = ? ORDER BY score DESC',
                (prediction_id,)
            )
            return [dict(row) for row in cursor.fetchall()]
