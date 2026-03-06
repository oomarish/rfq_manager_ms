"""
Shared pytest fixtures for rfq_manager_ms tests.

Provides:
- db_session   — in-memory SQLite session with tables created from Base.metadata
- test_client  — FastAPI TestClient wired with the test db_session
- sample_rfq   — factory fixture for creating test RFQ records
- auth_headers — dict with a valid test JWT Bearer token
"""
