"""
Statistics endpoints.

All endpoints require authentication.
All responses use the standard {success, data, message} envelope.

Routes:
  GET /api/v1/stats/overview               - Dashboard overview
  GET /api/v1/stats/trend                  - Daily threat trend (?days=30)
  GET /api/v1/stats/classification         - Phishing/Suspicious/Legitimate breakdown
  GET /api/v1/stats/top-senders            - Top senders by threat count (?limit=10)
  GET /api/v1/stats/top-domains            - Top sender domains by threat (?limit=10)
  GET /api/v1/stats/features               - Aggregated ML feature stats
  GET /api/v1/stats/segments               - Suspicious segment severity breakdown
  GET /api/v1/stats/links                  - VirusTotal link stats (?top_n=10)
  GET /api/v1/stats/timeline               - Email volume per day (?days=90)
  GET /api/v1/stats/probability-dist       - ML probability score histogram
"""

from fastapi import APIRouter, Depends, Query, Request

from app.core.dependencies import get_current_user_dependency
from app.services.stats_service import StatsService
from app.utils.api_response import success_response, error_response
from app.utils.logger import get_logger

router = APIRouter(prefix="/stats")
logger = get_logger(__name__)

_TAG = "Statistics"


# ------------------------------------------------------------------ #
# 1. Overview                                                          #
# ------------------------------------------------------------------ #


@router.get(
    "/overview",
    summary="Dashboard overview",
    description=(
        "High-level summary of all emails and threats for the authenticated user: "
        "total/analyzed/unanalyzed email counts, phishing/suspicious/legitimate counts "
        "with threat rate, and VirusTotal link totals."
    ),
    tags=[_TAG],
)
async def overview(
    request: Request,
    user_id: int = Depends(get_current_user_dependency),
):
    request_id = getattr(request.state, "request_id", "unknown")
    try:
        data = StatsService.get_overview(user_id)
        logger.info(
            f"Stats overview served [user_id={user_id}] [request_id={request_id}]"
        )
        return success_response(data=data)
    except Exception as e:
        logger.error(f"Stats overview error [user_id={user_id}]: {e}", exc_info=True)
        return error_response(
            error=str(e), message="Error building overview stats", status_code=500
        )


# ------------------------------------------------------------------ #
# 2. Daily trend                                                       #
# ------------------------------------------------------------------ #


@router.get(
    "/trend",
    summary="Daily threat trend",
    description=(
        "Per-day count of emails broken down by classification "
        "(PHISHING / SUSPICIOUS / LEGITIMATE / UNANALYZED) "
        "for the last N days. Gaps (days with no emails) are omitted."
    ),
    tags=[_TAG],
)
async def trend(
    request: Request,
    days: int = Query(30, ge=1, le=365, description="Number of past days to include"),
    user_id: int = Depends(get_current_user_dependency),
):
    request_id = getattr(request.state, "request_id", "unknown")
    try:
        data = StatsService.get_daily_trend(user_id, days)
        logger.info(
            f"Stats trend served [user_id={user_id}] [days={days}] [request_id={request_id}]"
        )
        return success_response(data=data)
    except Exception as e:
        logger.error(f"Stats trend error [user_id={user_id}]: {e}", exc_info=True)
        return error_response(
            error=str(e), message="Error building trend stats", status_code=500
        )


# ------------------------------------------------------------------ #
# 3. Classification breakdown                                          #
# ------------------------------------------------------------------ #


@router.get(
    "/classification",
    summary="Classification breakdown",
    description=(
        "Count and percentage of emails per classification label "
        "(PHISHING / SUSPICIOUS / LEGITIMATE / UNANALYZED) with "
        "average probability and ensemble score."
    ),
    tags=[_TAG],
)
async def classification_breakdown(
    request: Request,
    user_id: int = Depends(get_current_user_dependency),
):
    request_id = getattr(request.state, "request_id", "unknown")
    try:
        data = StatsService.get_classification_breakdown(user_id)
        logger.info(
            f"Stats classification served [user_id={user_id}] [request_id={request_id}]"
        )
        return success_response(data=data)
    except Exception as e:
        logger.error(
            f"Stats classification error [user_id={user_id}]: {e}", exc_info=True
        )
        return error_response(
            error=str(e), message="Error building classification stats", status_code=500
        )


# ------------------------------------------------------------------ #
# 4. Top senders                                                       #
# ------------------------------------------------------------------ #


@router.get(
    "/top-senders",
    summary="Top senders by threat count",
    description=(
        "Most frequent senders ranked by phishing count (desc), then total email count. "
        "Includes per-sender phishing/suspicious/legitimate counts and max probability."
    ),
    tags=[_TAG],
)
async def top_senders(
    request: Request,
    limit: int = Query(10, ge=1, le=100, description="Number of senders to return"),
    user_id: int = Depends(get_current_user_dependency),
):
    request_id = getattr(request.state, "request_id", "unknown")
    try:
        data = StatsService.get_top_senders(user_id, limit)
        logger.info(
            f"Stats top-senders served [user_id={user_id}] [limit={limit}] [request_id={request_id}]"
        )
        return success_response(data=data)
    except Exception as e:
        logger.error(f"Stats top-senders error [user_id={user_id}]: {e}", exc_info=True)
        return error_response(
            error=str(e), message="Error building top-senders stats", status_code=500
        )


# ------------------------------------------------------------------ #
# 5. Top sender domains                                                #
# ------------------------------------------------------------------ #


@router.get(
    "/top-domains",
    summary="Top sender domains by threat count",
    description=(
        "Most frequent sender domains (from ML-extracted prediction_features.sender_domain) "
        "ranked by phishing count. Includes dominant sender risk label."
    ),
    tags=[_TAG],
)
async def top_domains(
    request: Request,
    limit: int = Query(10, ge=1, le=100, description="Number of domains to return"),
    user_id: int = Depends(get_current_user_dependency),
):
    request_id = getattr(request.state, "request_id", "unknown")
    try:
        data = StatsService.get_top_domains(user_id, limit)
        logger.info(
            f"Stats top-domains served [user_id={user_id}] [limit={limit}] [request_id={request_id}]"
        )
        return success_response(data=data)
    except Exception as e:
        logger.error(f"Stats top-domains error [user_id={user_id}]: {e}", exc_info=True)
        return error_response(
            error=str(e), message="Error building top-domains stats", status_code=500
        )


# ------------------------------------------------------------------ #
# 6. ML feature stats                                                  #
# ------------------------------------------------------------------ #


@router.get(
    "/features",
    summary="ML feature statistics",
    description=(
        "Aggregate statistics of ML-extracted email features across all analyzed emails: "
        "average/max link count, attachment rate, urgent-keyword rate, "
        "sender-risk breakdown, and links-count distribution buckets."
    ),
    tags=[_TAG],
)
async def feature_stats(
    request: Request,
    user_id: int = Depends(get_current_user_dependency),
):
    request_id = getattr(request.state, "request_id", "unknown")
    try:
        data = StatsService.get_feature_stats(user_id)
        logger.info(
            f"Stats features served [user_id={user_id}] [request_id={request_id}]"
        )
        return success_response(data=data)
    except Exception as e:
        logger.error(f"Stats features error [user_id={user_id}]: {e}", exc_info=True)
        return error_response(
            error=str(e), message="Error building feature stats", status_code=500
        )


# ------------------------------------------------------------------ #
# 7. Suspicious segments                                               #
# ------------------------------------------------------------------ #


@router.get(
    "/segments",
    summary="Suspicious segment severity breakdown",
    description=(
        "Count and average score of suspicious text segments grouped by severity "
        "(HIGH / MEDIUM / LOW), plus the top 10 highest-scoring segments with "
        "their parent email subject."
    ),
    tags=[_TAG],
)
async def segment_stats(
    request: Request,
    user_id: int = Depends(get_current_user_dependency),
):
    request_id = getattr(request.state, "request_id", "unknown")
    try:
        data = StatsService.get_segment_stats(user_id)
        logger.info(
            f"Stats segments served [user_id={user_id}] [request_id={request_id}]"
        )
        return success_response(data=data)
    except Exception as e:
        logger.error(f"Stats segments error [user_id={user_id}]: {e}", exc_info=True)
        return error_response(
            error=str(e), message="Error building segment stats", status_code=500
        )


# ------------------------------------------------------------------ #
# 8. VirusTotal link stats                                             #
# ------------------------------------------------------------------ #


@router.get(
    "/links",
    summary="VirusTotal link statistics",
    description=(
        "Total links scanned, malicious/suspicious/clean counts, "
        "total malicious detection votes, and the top N most malicious URLs."
    ),
    tags=[_TAG],
)
async def link_stats(
    request: Request,
    top_n: int = Query(
        10, ge=1, le=50, description="Number of top malicious URLs to return"
    ),
    user_id: int = Depends(get_current_user_dependency),
):
    request_id = getattr(request.state, "request_id", "unknown")
    try:
        data = StatsService.get_link_stats(user_id, top_n)
        logger.info(
            f"Stats links served [user_id={user_id}] [top_n={top_n}] [request_id={request_id}]"
        )
        return success_response(data=data)
    except Exception as e:
        logger.error(f"Stats links error [user_id={user_id}]: {e}", exc_info=True)
        return error_response(
            error=str(e), message="Error building link stats", status_code=500
        )


# ------------------------------------------------------------------ #
# 9. Receive-volume timeline                                           #
# ------------------------------------------------------------------ #


@router.get(
    "/timeline",
    summary="Email receive-volume timeline",
    description=(
        "Number of emails received per calendar day for the last N days. "
        "Useful for plotting activity charts. Days with zero emails are omitted."
    ),
    tags=[_TAG],
)
async def timeline(
    request: Request,
    days: int = Query(90, ge=1, le=365, description="Number of past days to include"),
    user_id: int = Depends(get_current_user_dependency),
):
    request_id = getattr(request.state, "request_id", "unknown")
    try:
        data = StatsService.get_timeline(user_id, days)
        logger.info(
            f"Stats timeline served [user_id={user_id}] [days={days}] [request_id={request_id}]"
        )
        return success_response(data=data)
    except Exception as e:
        logger.error(f"Stats timeline error [user_id={user_id}]: {e}", exc_info=True)
        return error_response(
            error=str(e), message="Error building timeline stats", status_code=500
        )


# ------------------------------------------------------------------ #
# 10. Probability score distribution                                   #
# ------------------------------------------------------------------ #


@router.get(
    "/probability-dist",
    summary="ML probability score distribution",
    description=(
        "Histogram of phishing-probability scores (from the latest prediction per email) "
        "grouped into 0.1-wide buckets (0.0-0.1, 0.1-0.2, ..., 0.9-1.0). "
        "Includes count and percentage per bucket."
    ),
    tags=[_TAG],
)
async def probability_distribution(
    request: Request,
    user_id: int = Depends(get_current_user_dependency),
):
    request_id = getattr(request.state, "request_id", "unknown")
    try:
        data = StatsService.get_probability_distribution(user_id)
        logger.info(
            f"Stats prob-dist served [user_id={user_id}] [request_id={request_id}]"
        )
        return success_response(data=data)
    except Exception as e:
        logger.error(f"Stats prob-dist error [user_id={user_id}]: {e}", exc_info=True)
        return error_response(
            error=str(e),
            message="Error building probability distribution",
            status_code=500,
        )
