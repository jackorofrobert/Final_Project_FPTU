"""
FastAPI Application Package
Re-exports the FastAPI app from app.main for backward compatibility.
"""
from app.main import create_app, app

__all__ = ['create_app', 'app']
