"""Production platform: tenancy, billing, connectors, safety.

Revision ID: 20260724_0001
Revises:
Create Date: 2026-07-24
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260724_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("slug", sa.String(length=80), nullable=False),
        sa.Column("plan_code", sa.String(length=64), nullable=False, server_default="starter"),
        sa.Column("stripe_customer_id", sa.String(length=120), nullable=True),
        sa.Column("is_demo", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_organizations_slug", "organizations", ["slug"], unique=True)

    with op.batch_alter_table("users") as batch:
        batch.add_column(sa.Column("default_organization_id", sa.String(length=36), nullable=True))
        batch.create_foreign_key(
            "fk_users_default_org",
            "organizations",
            ["default_organization_id"],
            ["id"],
        )

    with op.batch_alter_table("buildings") as batch:
        batch.add_column(sa.Column("organization_id", sa.String(length=36), nullable=True))
        batch.add_column(sa.Column("connector_profile_id", sa.String(length=36), nullable=True))
        batch.add_column(sa.Column("shadow_mode", sa.Boolean(), server_default=sa.text("0")))
        batch.add_column(sa.Column("site_certified", sa.Boolean(), server_default=sa.text("0")))
        batch.add_column(sa.Column("write_enabled", sa.Boolean(), server_default=sa.text("0")))
        batch.add_column(sa.Column("onboarding_stage", sa.String(length=64), server_default="demo"))
        batch.create_foreign_key(
            "fk_buildings_organization",
            "organizations",
            ["organization_id"],
            ["id"],
        )

    op.create_table(
        "memberships",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("organization_id", sa.String(length=36), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("org_role", sa.String(length=64), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("organization_id", "user_id", name="uq_membership_org_user"),
    )

    op.create_table(
        "invitations",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("organization_id", sa.String(length=36), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("org_role", sa.String(length=64), nullable=False),
        sa.Column("token", sa.String(length=64), nullable=False),
        sa.Column("invited_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("status", sa.String(length=32), server_default="PENDING"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_invitations_token", "invitations", ["token"], unique=True)

    op.create_table(
        "subscriptions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("organization_id", sa.String(length=36), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("stripe_subscription_id", sa.String(length=120), nullable=True),
        sa.Column("plan_code", sa.String(length=64), server_default="starter"),
        sa.Column("status", sa.String(length=32), server_default="active"),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("entitlements_json", sa.JSON(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_subscriptions_organization_id", "subscriptions", ["organization_id"], unique=True)

    op.create_table(
        "entitlement_snapshots",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("organization_id", sa.String(length=36), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("plan_code", sa.String(length=64), nullable=False),
        sa.Column("entitlements_json", sa.JSON(), nullable=False),
        sa.Column("source", sa.String(length=64), server_default="stripe_webhook"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
    )

    op.create_table(
        "connector_profiles",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("organization_id", sa.String(length=36), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("building_id", sa.String(length=36), nullable=True),
        sa.Column("adapter_type", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("config_json", sa.JSON(), nullable=False),
        sa.Column("secret_ref", sa.String(length=255), nullable=True),
        sa.Column("site_token_hash", sa.String(length=128), nullable=True),
        sa.Column("status", sa.String(length=32), server_default="DISCONNECTED"),
        sa.Column("last_health_json", sa.JSON(), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
    )

    op.create_table(
        "point_mappings",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("building_id", sa.String(length=36), sa.ForeignKey("buildings.id"), nullable=False),
        sa.Column("connector_profile_id", sa.String(length=36), sa.ForeignKey("connector_profiles.id"), nullable=False),
        sa.Column("external_point_id", sa.String(length=255), nullable=False),
        sa.Column("external_point_name", sa.String(length=255), server_default=""),
        sa.Column("zone_id", sa.String(length=36), nullable=True),
        sa.Column("twinpilot_metric", sa.String(length=64), nullable=False),
        sa.Column("direction", sa.String(length=16), server_default="read"),
        sa.Column("unit", sa.String(length=32), server_default=""),
        sa.Column("scale", sa.Float(), server_default="1"),
        sa.Column("offset", sa.Float(), server_default="0"),
        sa.Column("deadband", sa.Float(), server_default="0.1"),
        sa.Column("enabled", sa.Boolean(), server_default=sa.text("1")),
        sa.Column("meta_json", sa.JSON(), nullable=False),
        sa.UniqueConstraint("building_id", "external_point_id", name="uq_point_building_external"),
    )

    op.create_table(
        "site_certifications",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("building_id", sa.String(length=36), sa.ForeignKey("buildings.id"), nullable=False),
        sa.Column("checklist_json", sa.JSON(), nullable=False),
        sa.Column("shadow_mode_complete", sa.Boolean(), server_default=sa.text("0")),
        sa.Column("guarded_pilot_complete", sa.Boolean(), server_default=sa.text("0")),
        sa.Column("autonomy_approved", sa.Boolean(), server_default=sa.text("0")),
        sa.Column("certified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("certified_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
    )
    op.create_index("ix_site_certifications_building_id", "site_certifications", ["building_id"], unique=True)

    op.create_table(
        "validation_nonces",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("nonce", sa.String(length=64), nullable=False),
        sa.Column("plan_id", sa.String(length=36), nullable=False),
        sa.Column("building_id", sa.String(length=36), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("nonce", name="uq_validation_nonce"),
    )

    op.create_table(
        "write_acknowledgements",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("building_id", sa.String(length=36), nullable=False),
        sa.Column("plan_id", sa.String(length=36), nullable=True),
        sa.Column("decision_id", sa.String(length=36), nullable=True),
        sa.Column("point_mapping_id", sa.String(length=36), nullable=True),
        sa.Column("requested_value", sa.Float(), nullable=False),
        sa.Column("readback_value", sa.Float(), nullable=True),
        sa.Column("success", sa.Boolean(), server_default=sa.text("0")),
        sa.Column("detail_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
    )

    op.create_table(
        "mv_baselines",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("building_id", sa.String(length=36), sa.ForeignKey("buildings.id"), nullable=False),
        sa.Column("name", sa.String(length=160), server_default="Default baseline"),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("baseline_energy_kwh", sa.Float(), server_default="0"),
        sa.Column("baseline_cost", sa.Float(), server_default="0"),
        sa.Column("baseline_carbon_kg", sa.Float(), server_default="0"),
        sa.Column("weather_normalized", sa.Boolean(), server_default=sa.text("1")),
        sa.Column("methodology", sa.String(length=64), server_default="IPMVP_Option_C"),
        sa.Column("meta_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
    )

    with op.batch_alter_table("audit_events") as batch:
        batch.add_column(sa.Column("organization_id", sa.String(length=36), nullable=True))
        batch.add_column(sa.Column("immutable", sa.Boolean(), server_default=sa.text("1")))


def downgrade() -> None:
    with op.batch_alter_table("audit_events") as batch:
        batch.drop_column("immutable")
        batch.drop_column("organization_id")
    op.drop_table("mv_baselines")
    op.drop_table("write_acknowledgements")
    op.drop_table("validation_nonces")
    op.drop_table("site_certifications")
    op.drop_table("point_mappings")
    op.drop_table("connector_profiles")
    op.drop_table("entitlement_snapshots")
    op.drop_table("subscriptions")
    op.drop_table("invitations")
    op.drop_table("memberships")
    with op.batch_alter_table("buildings") as batch:
        batch.drop_constraint("fk_buildings_organization", type_="foreignkey")
        batch.drop_column("onboarding_stage")
        batch.drop_column("write_enabled")
        batch.drop_column("site_certified")
        batch.drop_column("shadow_mode")
        batch.drop_column("connector_profile_id")
        batch.drop_column("organization_id")
    with op.batch_alter_table("users") as batch:
        batch.drop_constraint("fk_users_default_org", type_="foreignkey")
        batch.drop_column("default_organization_id")
    op.drop_table("organizations")
