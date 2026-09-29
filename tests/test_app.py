from copy import deepcopy
from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient

import src.app as app_module


INITIAL_ACTIVITIES = deepcopy(app_module.activities)


@pytest.fixture(autouse=True)
def reset_activities(monkeypatch):
    monkeypatch.setattr(app_module, "activities", deepcopy(INITIAL_ACTIVITIES))


@pytest.fixture
def client():
    return TestClient(app_module.app)


def activity_url(activity_name, action):
    return f"/activities/{quote(activity_name, safe='')}/{action}"


def test_root_redirects_to_static_index(client):
    response = client.get("/", follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"] == "/static/index.html"


def test_get_activities_returns_all_activities(client):
    response = client.get("/activities")

    assert response.status_code == 200
    assert response.json() == INITIAL_ACTIVITIES


def test_signup_adds_participant(client):
    activity_name = "Basketball Team"
    email = "new.student@mergington.edu"

    response = client.post(
        activity_url(activity_name, "signup"), params={"email": email}
    )

    assert response.status_code == 200
    assert response.json() == {
        "message": f"Signed up {email} for {activity_name}"
    }
    assert email in app_module.activities[activity_name]["participants"]


def test_signup_rejects_duplicate_participant(client):
    activity_name = "Chess Club"
    email = "michael@mergington.edu"

    response = client.post(
        activity_url(activity_name, "signup"), params={"email": email}
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Student already signed up for this activity"


def test_signup_rejects_unknown_activity(client):
    response = client.post(
        activity_url("Unknown Activity", "signup"),
        params={"email": "student@mergington.edu"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Activity not found"


def test_signup_requires_email(client):
    response = client.post(activity_url("Basketball Team", "signup"))

    assert response.status_code == 422


def test_remove_participant(client):
    activity_name = "Chess Club"
    email = "michael@mergington.edu"

    response = client.delete(
        activity_url(activity_name, "participants"), params={"email": email}
    )

    assert response.status_code == 200
    assert response.json() == {"message": f"Removed {email} from {activity_name}"}
    assert email not in app_module.activities[activity_name]["participants"]


def test_remove_participant_from_unknown_activity(client):
    response = client.delete(
        activity_url("Unknown Activity", "participants"),
        params={"email": "student@mergington.edu"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Activity not found"


def test_remove_unregistered_participant(client):
    response = client.delete(
        activity_url("Basketball Team", "participants"),
        params={"email": "student@mergington.edu"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Student is not signed up for this activity"


def test_remove_clears_duplicate_entries_and_allows_resignup(client):
    activity_name = "Basketball Team"
    email = "student@mergington.edu"
    app_module.activities[activity_name]["participants"] = [email, email]

    delete_response = client.delete(
        activity_url(activity_name, "participants"), params={"email": email}
    )
    signup_response = client.post(
        activity_url(activity_name, "signup"), params={"email": email}
    )

    assert delete_response.status_code == 200
    assert signup_response.status_code == 200
    assert app_module.activities[activity_name]["participants"].count(email) == 1