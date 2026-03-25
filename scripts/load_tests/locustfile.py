import random
from locust import HttpUser, task, between, events

class OctoBoxLoadTestUser(HttpUser):
    """
    Simulação de Carga (Stress/Spike Test) para os Endpoints Críticos do OctoBOX.
    Execução sugerida: locust -f locustfile.py --host=http://localhost:8000 --users 1000 --spawn-rate 50
    """
    wait_time = between(1, 4)
    auth_token = None

    def on_start(self):
        """
        Setup do User: Autenticação Inicial para pegar o Token de Sessão.
        TESTE: Autenticação / token (latência, throughput, picos de login)
        """
        response = self.client.post("/api/auth/login", json={
            "username": f"manager_{random.randint(1, 100)}@octobox.com",
            "password": "loadtest_password"
        }, name="/api/auth/login")
        
        if response.status_code == 200:
            self.auth_token = response.json().get("token")
            self.client.headers.update({"Authorization": f"Bearer {self.auth_token}"})

    @task(3)
    def test_list_and_filters(self):
        """
        TESTE: Listagens com filtros/pesquisa (queries compostas, paginação)
        Pesos maiores (3) pois é o comportamento base do Manager.
        """
        status = random.choice(["active", "inactive", "frozen", "lead"])
        # Query Composta (Paginador Server-Side Limit/Offset)
        self.client.get(f"/api/students?status={status}&page=1&limit=50", name="/api/students")
        self.client.get("/api/operations?date=today", name="/api/operations")

    @task(1)
    def test_bulk_actions(self):
        """
        TESTE: Bulk actions / batch update (consistência, partial commit)
        Dispara atualizações em lote para testar locking e OCC.
        """
        self.client.post("/api/items/bulk-update", json={
            "item_ids": [random.randint(1, 1000) for _ in range(20)],
            "action": "apply_discount",
            "value": 15.00
        }, name="/api/items/bulk-update")

    @task(1)
    def test_async_import_jobs(self):
        """
        TESTE: Import CSV / jobs (durabilidade, retries) + Status Tracker
        Dispara o Job assíncrono e aguarda a geração.
        """
        # Simulando envio de CSV multipart minimalista
        response = self.client.post("/api/imports", files={
            'file': ('contacts.csv', 'nome,telefone\nTeste,5511999999999', 'text/csv')
        }, name="/api/imports [POST]")
        
        if response.status_code in (200, 202):
            job_id = response.json().get("job_id", 1)
            # Simula a tela batendo no Tracker de Progresso
            self.client.get(f"/api/imports/{job_id}", name="/api/imports/{id} [GET]")

    @task(1)
    def test_async_export_reports(self):
        """
        TESTE: Export/Reports (geração assíncrona, download)
        """
        self.client.get("/api/reports/export?format=csv&module=finance", name="/api/reports/export")

    @task(1)
    def test_webhook_delivery_bursts(self):
        """
        TESTE: Webhook receiver / delivery (validar deduplicação, retries)
        Dispara rajadas para simular provedores (Evolution/Stripe).
        """
        # Disparamos 5 webhooks seguidos com o mesmo ID para forçar a Idempotency Key
        event_id = f"evt_{random.randint(1000, 9999)}"
        for _ in range(3):
            self.client.post("/api/integrations/webhook/receiver", json={
                "event_id": event_id,
                "type": "payment.succeeded",
                "data": {"amount": 100}
            }, name="/api/webhooks/receiver (Duplication Burst)")

    @task(2)
    def test_audit_logs_insertion(self):
        """
        TESTE: Auditoria/logs (inserção e leitura em alta taxa)
        """
        # Inserção
        self.client.post("/api/audit", json={
            "action": "student_viewed",
            "target": random.randint(1, 1000),
            "timestamp": "2026-03-25T12:00:00Z"
        }, name="/api/audit [POST]")
        # Leitura
        self.client.get("/api/audit?limit=100", name="/api/audit [GET]")
