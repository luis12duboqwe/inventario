"""add cloud agent tasks table

Revision ID: 202512050001
Revises: 202511270002
Create Date: 2025-12-05 17:55:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '202512050001'
down_revision = '202511270002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Crear tabla cloud_agent_tasks para delegación de tareas al agente en la nube."""
    op.create_table(
        'cloud_agent_tasks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column(
            'task_type',
            sa.Enum(
                'SYNC_DATA', 'GENERATE_REPORT', 'PROCESS_BATCH',
                'ANALYZE_DATA', 'BACKUP_DATA', 'CUSTOM',
                name='cloudagenttasktype'
            ),
            nullable=False,
            comment='Tipo de tarea a ejecutar'
        ),
        sa.Column(
            'status',
            sa.Enum(
                'PENDING', 'IN_PROGRESS', 'COMPLETED', 'FAILED', 'CANCELLED',
                name='cloudagenttaskstatus'
            ),
            nullable=False,
            server_default='PENDING',
            comment='Estado actual de la tarea'
        ),
        sa.Column('title', sa.String(length=200), nullable=False, comment='Título descriptivo de la tarea'),
        sa.Column('description', sa.Text(), nullable=True, comment='Descripción detallada de la tarea'),
        sa.Column('input_data', sa.Text(), nullable=True, comment='Datos de entrada en formato JSON'),
        sa.Column('output_data', sa.Text(), nullable=True, comment='Resultado de la tarea en formato JSON'),
        sa.Column('error_message', sa.Text(), nullable=True, comment='Mensaje de error si la tarea falló'),
        sa.Column('created_by_id', sa.Integer(), nullable=True, comment='Usuario que creó la tarea'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP'), comment='Fecha y hora de creación'),
        sa.Column('started_at', sa.DateTime(), nullable=True, comment='Fecha y hora de inicio de procesamiento'),
        sa.Column('completed_at', sa.DateTime(), nullable=True, comment='Fecha y hora de completado'),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='5', comment='Prioridad de la tarea (1=alta, 10=baja)'),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0', comment='Número de reintentos realizados'),
        sa.Column('max_retries', sa.Integer(), nullable=False, server_default='3', comment='Número máximo de reintentos permitidos'),
        sa.ForeignKeyConstraint(['created_by_id'], ['usuarios.id_usuario'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Crear índices para mejorar el rendimiento de las consultas
    op.create_index(op.f('ix_cloud_agent_tasks_task_type'), 'cloud_agent_tasks', ['task_type'], unique=False)
    op.create_index(op.f('ix_cloud_agent_tasks_status'), 'cloud_agent_tasks', ['status'], unique=False)
    op.create_index(op.f('ix_cloud_agent_tasks_created_by_id'), 'cloud_agent_tasks', ['created_by_id'], unique=False)
    op.create_index(op.f('ix_cloud_agent_tasks_created_at'), 'cloud_agent_tasks', ['created_at'], unique=False)
    op.create_index(op.f('ix_cloud_agent_tasks_priority'), 'cloud_agent_tasks', ['priority'], unique=False)


def downgrade() -> None:
    """Eliminar tabla cloud_agent_tasks."""
    op.drop_index(op.f('ix_cloud_agent_tasks_priority'), table_name='cloud_agent_tasks')
    op.drop_index(op.f('ix_cloud_agent_tasks_created_at'), table_name='cloud_agent_tasks')
    op.drop_index(op.f('ix_cloud_agent_tasks_created_by_id'), table_name='cloud_agent_tasks')
    op.drop_index(op.f('ix_cloud_agent_tasks_status'), table_name='cloud_agent_tasks')
    op.drop_index(op.f('ix_cloud_agent_tasks_task_type'), table_name='cloud_agent_tasks')
    op.drop_table('cloud_agent_tasks')
    
    # Eliminar los tipos enum
    op.execute('DROP TYPE IF EXISTS cloudagenttasktype')
    op.execute('DROP TYPE IF EXISTS cloudagenttaskstatus')
