"""Initial schema migration for SolutionBridge tables.

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-09-22 01:50:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Customers
    op.create_table(
        'customers',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('email', sa.String(length=150), nullable=False),
        sa.Column('environment', sa.String(length=50), nullable=False, server_default='production'),
        sa.Column('api_key_hash', sa.String(length=128), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='active'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )
    op.create_index('ix_customers_id', 'customers', ['id'])
    op.create_index('ix_customers_email', 'customers', ['email'])

    # 2. Products
    op.create_table(
        'products',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('sku', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('price', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0.00'),
        sa.Column('stock', sa.Integer(), nullable=False, server_default='100'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('sku')
    )
    op.create_index('ix_products_id', 'products', ['id'])
    op.create_index('ix_products_sku', 'products', ['sku'])

    # 3. API Endpoints
    op.create_table(
        'api_endpoints',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('method', sa.String(length=10), nullable=False),
        sa.Column('endpoint', sa.String(length=200), nullable=False),
        sa.Column('service', sa.String(length=100), nullable=False),
        sa.Column('expected_status', sa.Integer(), nullable=False, server_default='200'),
        sa.Column('max_response_time_ms', sa.Integer(), nullable=False, server_default='500'),
        sa.Column('active', sa.Boolean(), nullable=False, server_default='1'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_api_endpoints_id', 'api_endpoints', ['id'])

    # 4. API Test Runs
    op.create_table(
        'api_test_runs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('customer_id', sa.Integer(), nullable=True),
        sa.Column('endpoint_id', sa.Integer(), nullable=False),
        sa.Column('request_id', sa.String(length=100), nullable=False),
        sa.Column('status_code', sa.Integer(), nullable=False),
        sa.Column('response_time_ms', sa.Float(), nullable=False),
        sa.Column('test_status', sa.String(length=50), nullable=False),
        sa.Column('response_body', sa.Text(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['endpoint_id'], ['api_endpoints.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_api_test_runs_id', 'api_test_runs', ['id'])
    op.create_index('ix_api_test_runs_request_id', 'api_test_runs', ['request_id'])
    op.create_index('ix_api_test_runs_created_at', 'api_test_runs', ['created_at'])

    # 5. Orders
    op.create_table(
        'orders',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('customer_id', sa.Integer(), nullable=False),
        sa.Column('external_order_id', sa.String(length=100), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='PENDING'),
        sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_orders_id', 'orders', ['id'])
    op.create_index('ix_orders_customer_id', 'orders', ['customer_id'])
    op.create_index('ix_orders_external_order_id', 'orders', ['external_order_id'])
    op.create_index('ix_orders_created_at', 'orders', ['created_at'])

    # 6. Logs
    op.create_table(
        'logs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('level', sa.String(length=20), nullable=False),
        sa.Column('service', sa.String(length=100), nullable=False),
        sa.Column('customer_id', sa.Integer(), nullable=True),
        sa.Column('request_id', sa.String(length=100), nullable=False),
        sa.Column('endpoint', sa.String(length=200), nullable=True),
        sa.Column('status_code', sa.Integer(), nullable=True),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('error_code', sa.String(length=100), nullable=True),
        sa.Column('response_time_ms', sa.Float(), nullable=True),
        sa.Column('metadata_json', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_logs_id', 'logs', ['id'])
    op.create_index('ix_logs_timestamp', 'logs', ['timestamp'])
    op.create_index('ix_logs_level', 'logs', ['level'])
    op.create_index('ix_logs_service', 'logs', ['service'])
    op.create_index('ix_logs_request_id', 'logs', ['request_id'])
    op.create_index('ix_logs_error_code', 'logs', ['error_code'])
    op.create_index('idx_logs_req_level', 'logs', ['request_id', 'level'])
    op.create_index('idx_logs_cust_time', 'logs', ['customer_id', 'timestamp'])

    # 7. System Metrics
    op.create_table(
        'system_metrics',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('cpu_percent', sa.Float(), nullable=False),
        sa.Column('memory_percent', sa.Float(), nullable=False),
        sa.Column('db_latency_ms', sa.Float(), nullable=False),
        sa.Column('active_connections', sa.Integer(), nullable=False),
        sa.Column('request_rate', sa.Float(), nullable=False),
        sa.Column('error_rate', sa.Float(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_system_metrics_id', 'system_metrics', ['id'])
    op.create_index('ix_system_metrics_timestamp', 'system_metrics', ['timestamp'])

    # 8. Incidents
    op.create_table(
        'incidents',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('customer_id', sa.Integer(), nullable=True),
        sa.Column('request_id', sa.String(length=100), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('severity', sa.String(length=50), nullable=False, server_default='MEDIUM'),
        sa.Column('category', sa.String(length=100), nullable=False),
        sa.Column('predicted_root_cause', sa.Text(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='OPEN'),
        sa.Column('evidence_summary', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('request_id')
    )
    op.create_index('ix_incidents_id', 'incidents', ['id'])
    op.create_index('ix_incidents_request_id', 'incidents', ['request_id'])
    op.create_index('ix_incidents_created_at', 'incidents', ['created_at'])

    # 9. Incident Evidence
    op.create_table(
        'incident_evidence',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('incident_id', sa.Integer(), nullable=False),
        sa.Column('evidence_type', sa.String(length=50), nullable=False),
        sa.Column('source_id', sa.String(length=100), nullable=True),
        sa.Column('evidence_text', sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(['incident_id'], ['incidents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_incident_evidence_id', 'incident_evidence', ['id'])
    op.create_index('ix_incident_evidence_incident_id', 'incident_evidence', ['incident_id'])

    # 10. Troubleshooting Actions
    op.create_table(
        'troubleshooting_actions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('incident_id', sa.Integer(), nullable=False),
        sa.Column('action', sa.String(length=250), nullable=False),
        sa.Column('rationale', sa.Text(), nullable=False),
        sa.Column('result', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['incident_id'], ['incidents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_troubleshooting_actions_id', 'troubleshooting_actions', ['id'])
    op.create_index('ix_troubleshooting_actions_incident_id', 'troubleshooting_actions', ['incident_id'])

    # 11. Historical Incidents
    op.create_table(
        'historical_incidents',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('incident_id', sa.String(length=50), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('embedding_reference', sa.String(length=100), nullable=True),
        sa.Column('resolution', sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('incident_id')
    )
    op.create_index('ix_historical_incidents_id', 'historical_incidents', ['id'])
    op.create_index('ix_historical_incidents_incident_id', 'historical_incidents', ['incident_id'])


def downgrade() -> None:
    op.drop_table('historical_incidents')
    op.drop_table('troubleshooting_actions')
    op.drop_table('incident_evidence')
    op.drop_table('incidents')
    op.drop_table('system_metrics')
    op.drop_table('logs')
    op.drop_table('orders')
    op.drop_table('api_test_runs')
    op.drop_table('api_endpoints')
    op.drop_table('products')
    op.drop_table('customers')
