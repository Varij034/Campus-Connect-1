"""Add candidate profile fields

Revision ID: 009_profile
Revises: 008_messages
Create Date: 2026-08-23

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "009_profile"
down_revision = "008_messages"
branch_labels = None
depends_on = None

def _candidates_columns(conn):
    inspector = inspect(conn)
    return {c["name"] for c in inspector.get_columns("candidates")}

def upgrade() -> None:
    conn = op.get_bind()
    existing = _candidates_columns(conn)
    
    columns_to_add = [
        ("linkedin_url", sa.String(length=500)),
        ("location", sa.String(length=255)),
        ("education", sa.String(length=255)),
        ("college", sa.String(length=255)),
        ("branch", sa.String(length=255)),
        ("graduation_year", sa.String(length=20)),
        ("cgpa", sa.String(length=20)),
        ("bio", sa.Text()),
        ("experience", sa.String(length=255)),
    ]
    
    for col_name, col_type in columns_to_add:
        if col_name not in existing:
            op.add_column("candidates", sa.Column(col_name, col_type, nullable=True))

def downgrade() -> None:
    conn = op.get_bind()
    existing = _candidates_columns(conn)
    
    columns_to_drop = [
        "linkedin_url", "location", "education", "college", 
        "branch", "graduation_year", "cgpa", "bio", "experience"
    ]
    
    for col_name in columns_to_drop:
        if col_name in existing:
            op.drop_column("candidates", col_name)
