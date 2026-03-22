"""Initial blacklistify schema

Revision ID: 001
Revises:
Create Date: 2026-03-23

Real Ripefy DB structure:
  ripe_accounts -> ip_prefixes (/22) -> ip_blocks (/24) -> ip_leases -> customers
  77 prefixes, 308 blocks, ~78K IPs
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import INET, JSONB

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS blacklistify")

    # scan_jobs
    op.create_table(
        "scan_jobs",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("job_type", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("total_subnets", sa.Integer, server_default="0"),
        sa.Column("total_ips", sa.Integer, server_default="0"),
        sa.Column("scanned_ips", sa.Integer, server_default="0"),
        sa.Column("blacklisted_ips", sa.Integer, server_default="0"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        schema="blacklistify",
    )

    # scan_results — one row per IP per scan
    op.create_table(
        "scan_results",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("scan_job_id", sa.BigInteger, sa.ForeignKey("blacklistify.scan_jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("block_id", sa.String(36), nullable=True),         # Ripefy ip_blocks.id (soft FK)
        sa.Column("block_cidr", sa.String(43), nullable=False),       # e.g. "185.87.120.0/24"
        sa.Column("prefix_id", sa.String(36), nullable=True),         # Ripefy ip_prefixes.id (soft FK)
        sa.Column("prefix_cidr", sa.String(43), nullable=True),       # e.g. "185.87.120.0/22"
        sa.Column("ip_address", INET, nullable=False),
        sa.Column("is_blacklisted", sa.Boolean, server_default="false"),
        sa.Column("providers_detected", JSONB, server_default="'[]'"),
        sa.Column("providers_total", sa.Integer, server_default="0"),
        sa.Column("checked_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        schema="blacklistify",
    )
    op.create_index("idx_sr_block_id", "scan_results", ["block_id"], schema="blacklistify")
    op.create_index("idx_sr_block_cidr", "scan_results", ["block_cidr"], schema="blacklistify")
    op.create_index("idx_sr_prefix_id", "scan_results", ["prefix_id"], schema="blacklistify")
    op.create_index("idx_sr_ip", "scan_results", ["ip_address"], schema="blacklistify")
    op.create_index("idx_sr_blacklisted", "scan_results", ["is_blacklisted"], schema="blacklistify", postgresql_where=sa.text("is_blacklisted = TRUE"))
    op.create_index("idx_sr_checked", "scan_results", [sa.text("checked_at DESC")], schema="blacklistify")
    op.create_index("idx_sr_job", "scan_results", ["scan_job_id"], schema="blacklistify")

    # block_status — aggregate cache per /24 block (maps to Ripefy ip_blocks)
    op.create_table(
        "block_status",
        sa.Column("block_id", sa.String(36), primary_key=True),      # Ripefy ip_blocks.id
        sa.Column("block_cidr", sa.String(43), nullable=False),
        sa.Column("prefix_id", sa.String(36), nullable=True),
        sa.Column("prefix_cidr", sa.String(43), nullable=True),
        sa.Column("customer_name", sa.String(255), nullable=True),
        sa.Column("total_ips", sa.Integer, server_default="0"),
        sa.Column("blacklisted_ips", sa.Integer, server_default="0"),
        sa.Column("clean_ips", sa.Integer, server_default="0"),
        sa.Column("blacklist_rate", sa.Numeric(5, 4), server_default="0"),
        sa.Column("worst_providers", JSONB, server_default="'[]'"),
        sa.Column("last_scan_job_id", sa.BigInteger, nullable=True),
        sa.Column("last_scanned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status_changed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        schema="blacklistify",
    )
    op.create_index("idx_bs_prefix", "block_status", ["prefix_id"], schema="blacklistify")

    # api_keys
    op.create_table(
        "api_keys",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("key_prefix", sa.String(8), nullable=False),
        sa.Column("key_hash", sa.String(128), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("scopes", JSONB, server_default='\'["read"]\''),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        schema="blacklistify",
    )
    op.create_index("idx_api_keys_prefix", "api_keys", ["key_prefix"], schema="blacklistify")

    # webhooks
    op.create_table(
        "webhooks",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("url", sa.String(500), nullable=False),
        sa.Column("events", JSONB, nullable=False),
        sa.Column("secret", sa.String(128), nullable=False),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("last_triggered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failure_count", sa.Integer, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        schema="blacklistify",
    )

    # alert_rules
    op.create_table(
        "alert_rules",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("condition_type", sa.String(30), nullable=False),
        sa.Column("threshold", sa.Numeric, nullable=True),
        sa.Column("subnet_filter", sa.String(43), nullable=True),
        sa.Column("webhook_id", sa.BigInteger, sa.ForeignKey("blacklistify.webhooks.id", ondelete="SET NULL"), nullable=True),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        schema="blacklistify",
    )


def downgrade() -> None:
    op.drop_table("alert_rules", schema="blacklistify")
    op.drop_table("webhooks", schema="blacklistify")
    op.drop_table("api_keys", schema="blacklistify")
    op.drop_table("block_status", schema="blacklistify")
    op.drop_table("scan_results", schema="blacklistify")
    op.drop_table("scan_jobs", schema="blacklistify")
    op.execute("DROP SCHEMA IF EXISTS blacklistify CASCADE")
