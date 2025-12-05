"""Pruebas para el módulo de delegación al agente en la nube."""
import json
import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app import models
from backend.app.core.roles import ADMIN
from backend.app.services import cloud_agent


def _auth_headers(client: TestClient) -> dict[str, str]:
    """Crear headers de autenticación con usuario admin."""
    payload = {
        "username": "admin",
        "password": "MuySegura123",
        "full_name": "Admin General",
        "roles": [ADMIN],
    }
    response = client.post("/auth/bootstrap", json=payload)
    assert response.status_code == status.HTTP_201_CREATED

    token_response = client.post(
        "/auth/token",
        data={"username": payload["username"], "password": payload["password"]},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert token_response.status_code == status.HTTP_200_OK
    token = token_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}", "X-Reason": "Operacion de prueba"}


def _get_admin_user(db_session: Session) -> models.User:
    """Obtener el usuario admin de la base de datos."""
    return db_session.query(models.User).filter(
        models.User.username == "admin"
    ).first()


def test_cloud_agent_feature_flag_disabled(client: TestClient):
    """Verificar que el servicio retorna 503 cuando el flag está deshabilitado."""
    admin_headers = _auth_headers(client)
    
    # Simular que el flag está deshabilitado
    from backend.app.config import settings
    original_value = settings.enable_cloud_agent
    settings.enable_cloud_agent = False
    
    try:
        response = client.get("/cloud/tasks", headers=admin_headers)
        assert response.status_code == 503
        assert "no está habilitado" in response.json()["detail"]
    finally:
        settings.enable_cloud_agent = original_value


def test_create_cloud_agent_task(db_session: Session, client: TestClient):
    """Verificar la creación de una tarea del agente en la nube."""
    admin_headers = _auth_headers(client)
    admin_user = _get_admin_user(db_session)
    
    task = cloud_agent.create_task(
        db=db_session,
        task_type=models.CloudAgentTaskType.SYNC_DATA,
        title="Sincronizar datos de prueba",
        description="Esta es una tarea de prueba",
        input_data={"test_key": "test_value"},
        priority=3,
        max_retries=5,
        created_by_id=admin_user.id,
    )
    
    assert task.id is not None
    assert task.task_type == models.CloudAgentTaskType.SYNC_DATA
    assert task.title == "Sincronizar datos de prueba"
    assert task.status == models.CloudAgentTaskStatus.PENDING
    assert task.created_by_id == admin_user.id
    assert task.priority == 3
    assert task.max_retries == 5
    assert task.retry_count == 0
    
    # Verificar que input_data se almacenó como JSON
    input_data = json.loads(task.input_data)
    assert input_data["test_key"] == "test_value"


def test_list_cloud_agent_tasks(db_session: Session, client: TestClient):
    """Verificar el listado de tareas con filtros."""
    admin_headers = _auth_headers(client)
    admin_user = _get_admin_user(db_session)
    
    # Crear varias tareas
    task1 = cloud_agent.create_task(
        db=db_session,
        task_type=models.CloudAgentTaskType.GENERATE_REPORT,
        title="Generar reporte 1",
        created_by_id=admin_user.id,
        priority=1,
    )
    
    task2 = cloud_agent.create_task(
        db=db_session,
        task_type=models.CloudAgentTaskType.SYNC_DATA,
        title="Sincronizar datos",
        created_by_id=admin_user.id,
        priority=5,
    )
    
    # Actualizar el estado de task2
    cloud_agent.update_task_status(
        db=db_session,
        task_id=task2.id,
        status=models.CloudAgentTaskStatus.IN_PROGRESS,
    )
    
    # Listar todas las tareas
    tasks, total = cloud_agent.list_tasks(db=db_session)
    assert total >= 2
    assert any(t.id == task1.id for t in tasks)
    assert any(t.id == task2.id for t in tasks)
    
    # Filtrar por estado PENDING
    pending_tasks, pending_total = cloud_agent.list_tasks(
        db=db_session,
        status=models.CloudAgentTaskStatus.PENDING,
    )
    assert pending_total >= 1
    assert all(t.status == models.CloudAgentTaskStatus.PENDING for t in pending_tasks)
    
    # Filtrar por tipo
    report_tasks, report_total = cloud_agent.list_tasks(
        db=db_session,
        task_type=models.CloudAgentTaskType.GENERATE_REPORT,
    )
    assert report_total >= 1
    assert all(t.task_type == models.CloudAgentTaskType.GENERATE_REPORT for t in report_tasks)


def test_update_task_status(db_session: Session, client: TestClient):
    """Verificar la actualización del estado de una tarea."""
    admin_headers = _auth_headers(client)
    admin_user = _get_admin_user(db_session)
    
    task = cloud_agent.create_task(
        db=db_session,
        task_type=models.CloudAgentTaskType.PROCESS_BATCH,
        title="Procesar lote",
        created_by_id=admin_user.id,
    )
    
    assert task.status == models.CloudAgentTaskStatus.PENDING
    assert task.started_at is None
    assert task.completed_at is None
    
    # Actualizar a IN_PROGRESS
    updated_task = cloud_agent.update_task_status(
        db=db_session,
        task_id=task.id,
        status=models.CloudAgentTaskStatus.IN_PROGRESS,
    )
    
    assert updated_task.status == models.CloudAgentTaskStatus.IN_PROGRESS
    assert updated_task.started_at is not None
    assert updated_task.completed_at is None
    
    # Actualizar a COMPLETED con output_data
    completed_task = cloud_agent.update_task_status(
        db=db_session,
        task_id=task.id,
        status=models.CloudAgentTaskStatus.COMPLETED,
        output_data={"result": "success", "records_processed": 100},
    )
    
    assert completed_task.status == models.CloudAgentTaskStatus.COMPLETED
    assert completed_task.completed_at is not None
    
    output_data = json.loads(completed_task.output_data)
    assert output_data["result"] == "success"
    assert output_data["records_processed"] == 100


def test_cancel_task(db_session: Session, client: TestClient):
    """Verificar la cancelación de una tarea."""
    admin_headers = _auth_headers(client)
    admin_user = _get_admin_user(db_session)

    """Verificar la cancelación de una tarea."""
    task = cloud_agent.create_task(
        db=db_session,
        task_type=models.CloudAgentTaskType.BACKUP_DATA,
        title="Respaldar datos",
        created_by_id=admin_user.id,
    )
    
    # Cancelar tarea pendiente
    cancelled_task = cloud_agent.cancel_task(db=db_session, task_id=task.id)
    assert cancelled_task is not None
    assert cancelled_task.status == models.CloudAgentTaskStatus.CANCELLED
    assert cancelled_task.completed_at is not None
    assert "cancelada" in cancelled_task.error_message.lower()
    
    # Intentar cancelar una tarea ya cancelada (debe fallar)
    result = cloud_agent.cancel_task(db=db_session, task_id=task.id)
    assert result is None


def test_get_task_stats(db_session: Session, client: TestClient):
    """Verificar el cálculo de estadísticas de tareas."""
    admin_headers = _auth_headers(client)
    admin_user = _get_admin_user(db_session)

    """Verificar el cálculo de estadísticas de tareas."""
    # Crear tareas con diferentes estados
    task1 = cloud_agent.create_task(
        db=db_session,
        task_type=models.CloudAgentTaskType.ANALYZE_DATA,
        title="Analizar datos 1",
        created_by_id=admin_user.id,
    )
    
    task2 = cloud_agent.create_task(
        db=db_session,
        task_type=models.CloudAgentTaskType.ANALYZE_DATA,
        title="Analizar datos 2",
        created_by_id=admin_user.id,
    )
    
    cloud_agent.update_task_status(
        db=db_session,
        task_id=task2.id,
        status=models.CloudAgentTaskStatus.COMPLETED,
    )
    
    stats = cloud_agent.get_task_stats(db=db_session)
    
    assert stats["total_tasks"] >= 2
    assert stats["pending_tasks"] >= 1
    assert stats["completed_tasks"] >= 1


def test_retry_failed_tasks(db_session: Session, client: TestClient):
    """Verificar el reintento de tareas fallidas."""
    admin_headers = _auth_headers(client)
    admin_user = _get_admin_user(db_session)

    """Verificar el reintento de tareas fallidas."""
    # Crear una tarea y marcarla como fallida
    task = cloud_agent.create_task(
        db=db_session,
        task_type=models.CloudAgentTaskType.CUSTOM,
        title="Tarea personalizada",
        created_by_id=admin_user.id,
        max_retries=3,
    )
    
    cloud_agent.update_task_status(
        db=db_session,
        task_id=task.id,
        status=models.CloudAgentTaskStatus.FAILED,
        error_message="Error simulado",
    )
    
    # Reintentar tareas fallidas
    retried = cloud_agent.retry_failed_tasks(db=db_session)
    
    assert len(retried) >= 1
    assert any(t.id == task.id for t in retried)
    
    # Verificar que la tarea fue reintentada
    db_session.refresh(task)
    assert task.status == models.CloudAgentTaskStatus.PENDING
    assert task.retry_count == 1
    assert task.error_message is None


def test_api_delegate_task(client: TestClient):
    """Verificar el endpoint POST /cloud/delegate."""
    admin_headers = _auth_headers(client)

    """Verificar el endpoint POST /cloud/delegate."""
    from backend.app.config import settings
    if not settings.enable_cloud_agent:
        pytest.skip("Cloud agent deshabilitado")
    
    response = client.post(
        "/cloud/delegate",
        json={
            "task_type": "generate_report",
            "title": "Generar reporte mensual",
            "description": "Reporte de ventas del mes",
            "input_data": {"month": "2025-12", "format": "PDF"},
            "priority": 2,
            "max_retries": 3,
        },
        headers=admin_headers,
    )
    
    if response.status_code != 201:
        print(f"Response status: {response.status_code}")
        print(f"Response body: {response.json()}")
    assert response.status_code == 201
    data = response.json()
    assert data["task_type"] == "generate_report"
    assert data["title"] == "Generar reporte mensual"
    assert data["status"] == "pending"
    assert data["priority"] == 2


def test_api_list_tasks(client: TestClient):
    """Verificar el endpoint GET /cloud/tasks."""
    admin_headers = _auth_headers(client)

    """Verificar el endpoint GET /cloud/tasks."""
    from backend.app.config import settings
    if not settings.enable_cloud_agent:
        pytest.skip("Cloud agent deshabilitado")
    
    # Crear una tarea primero
    client.post(
        "/cloud/delegate",
        json={
            "task_type": "sync_data",
            "title": "Sincronizar inventario",
        },
        headers=admin_headers,
    )
    
    response = client.get("/cloud/tasks", headers=admin_headers)
    
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "size" in data
    assert isinstance(data["items"], list)


def test_api_get_task(client: TestClient):
    """Verificar el endpoint GET /cloud/tasks/{task_id}."""
    admin_headers = _auth_headers(client)

    """Verificar el endpoint GET /cloud/tasks/{task_id}."""
    from backend.app.config import settings
    if not settings.enable_cloud_agent:
        pytest.skip("Cloud agent deshabilitado")
    
    # Crear una tarea
    create_response = client.post(
        "/cloud/delegate",
        json={
            "task_type": "backup_data",
            "title": "Respaldar base de datos",
        },
        headers=admin_headers,
    )
    task_id = create_response.json()["id"]
    
    # Obtener la tarea
    response = client.get(f"/cloud/tasks/{task_id}", headers=admin_headers)
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == task_id
    assert data["task_type"] == "backup_data"


def test_api_cancel_task(client: TestClient):
    """Verificar el endpoint DELETE /cloud/tasks/{task_id}."""
    admin_headers = _auth_headers(client)

    """Verificar el endpoint DELETE /cloud/tasks/{task_id}."""
    from backend.app.config import settings
    if not settings.enable_cloud_agent:
        pytest.skip("Cloud agent deshabilitado")
    
    # Crear una tarea
    create_response = client.post(
        "/cloud/delegate",
        json={
            "task_type": "process_batch",
            "title": "Procesar importación",
        },
        headers=admin_headers,
    )
    task_id = create_response.json()["id"]
    
    # Cancelar la tarea
    response = client.delete(f"/cloud/tasks/{task_id}", headers=admin_headers)
    
    assert response.status_code == 204
    
    # Verificar que fue cancelada
    get_response = client.get(f"/cloud/tasks/{task_id}", headers=admin_headers)
    assert get_response.json()["status"] == "cancelled"


def test_api_get_stats(client: TestClient):
    """Verificar el endpoint GET /cloud/stats."""
    admin_headers = _auth_headers(client)

    """Verificar el endpoint GET /cloud/stats."""
    from backend.app.config import settings
    if not settings.enable_cloud_agent:
        pytest.skip("Cloud agent deshabilitado")
    
    response = client.get("/cloud/stats", headers=admin_headers)
    
    assert response.status_code == 200
    data = response.json()
    assert "total_tasks" in data
    assert "pending_tasks" in data
    assert "completed_tasks" in data
    assert isinstance(data["total_tasks"], int)
