"""Role abstraction on the real FastAPI app (planning store + event log redirected to a temp dir)."""
import pytest
from fastapi.testclient import TestClient

M = {"X-Demo-Role": "manager", "X-Demo-User": "MGR-01"}
O = {"X-Demo-Role": "operator", "X-Demo-User": "OP-104"}


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    import main
    from planning_store import PlanningStore
    tmp = tmp_path_factory.mktemp("api")
    main.EVENTS_PATH = tmp / "events.json"
    main.engine.planning.store = PlanningStore(tmp / "planning.json")
    return TestClient(main.app)


def test_operator_cannot_use_manager_apis(client):
    assert client.get("/api/planner").status_code == 401
    for method, path in [("get", "/api/planner"), ("post", "/api/planner/recommend"), ("post", "/api/planner/publish"),
                         ("delete", "/api/planner/tasks/T1"), ("post", "/api/weather/scenario")]:
        r = getattr(client, method)(path, headers=O, **({"json": {"scenario": "clear"}} if "scenario" in path else {}))
        assert r.status_code == 403, path


def test_operator_reads_only_own_schedule(client):
    assert client.get("/api/operator/schedule", headers=O).status_code == 200
    assert client.get("/api/operator/schedule?operator_id=OP-101", headers=O).status_code == 403
    assert client.get("/api/weather/forecast", headers=O).json()["synthetic"] is True


def test_manager_flow_and_existing_endpoints(client):
    assert client.post("/api/planner/recommend", headers=M).status_code == 200
    r = client.post("/api/planner/publish", headers=M)
    assert r.status_code == 200 and r.json()["plan_status"] == "published"
    s = client.get("/api/operator/schedule", headers=O).json()
    assert s["published"] and s["tasks"][0]["task_id"] == "T4"
    # existing, unauthenticated endpoints keep working and state carries forecast context
    st = client.get("/api/state").json()
    assert "weather" not in st or st["weather"] in ("clear", "rain", "heat")
    assert st["planning"]["forecast"]["synthetic"] is True
    assert client.get("/api/meta").status_code == 200


def test_operator_planner_endpoint_is_read_only(client):
    import copy

    import main
    client.post("/api/planner/recommend", headers=M)
    client.post("/api/planner/publish", headers=M)
    before = copy.deepcopy(main.engine.planning.store.published)
    r = client.get("/api/operator/planner", headers=O)
    assert r.status_code == 200 and r.json()["available"]
    assert r.json()["published_order"][0] == "T4"
    assert client.get("/api/operator/planner?operator_id=OP-101", headers=O).status_code == 403
    assert client.get("/api/operator/planner", headers=M).status_code == 400
    assert client.get("/api/operator/planner?operator_id=OP-104", headers=M).status_code == 200
    assert main.engine.planning.store.published == before
