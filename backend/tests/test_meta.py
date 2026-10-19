from fastapi.testclient import TestClient

from app.main import app
from app.taxonomy import recruiter_domain


def test_meta_lists_taxonomy():
    body = TestClient(app).get("/api/meta").json()
    assert len(body["industries"]) == 13
    assert sum(len(g["role_types"]) for g in body["role_type_groups"]) == 22
    assert body["terms"] == ["Summer 2027", "Fall 2026", "Spring 2027"]


def test_recruiter_domain():
    assert recruiter_domain("embedded_firmware", "space") == "embedded firmware roles at space companies"
    assert recruiter_domain("biology_lab", "biotech_pharma") == "biology lab roles at biotech and pharma companies"
    assert recruiter_domain("software", "other") == "software roles"
