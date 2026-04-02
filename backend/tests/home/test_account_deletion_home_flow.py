import pytest


def test_delete_account_without_home_has_no_home_side_effects(client, registered_user):
    delete_response = client.delete("/auth/delete", headers=registered_user["headers"])

    assert delete_response.status_code == 200, delete_response.text
    body = delete_response.json()
    assert body["code"] == "ACCOUNT_DELETED_NO_HOME"



def test_delete_account_of_private_home_owner_dissolves_home(client, private_home_setup):
    delete_response = client.delete("/auth/delete", headers=private_home_setup["headers"])
    owner_home_response = client.get("/home/", headers=private_home_setup["headers"])

    assert delete_response.status_code == 200, delete_response.text
    body = delete_response.json()
    assert body["code"] == "ACCOUNT_DELETED_AND_HOME_DISSOLVED"
    assert owner_home_response.status_code in (401, 403, 404), owner_home_response.text



def test_delete_account_of_shared_home_member_removes_home_access(client, shared_home_setup):
    delete_response = client.delete("/auth/delete", headers=shared_home_setup["member1_headers"])
    owner_view = client.get("/home/", headers=shared_home_setup["owner_headers"])

    assert delete_response.status_code == 200, delete_response.text
    body = delete_response.json()
    assert body["code"] == "ACCOUNT_DELETED_AND_REMOVED_FROM_HOME"

    assert owner_view.status_code == 200, owner_view.text
    owner_body = owner_view.json()
    usernames = {member["username"] for member in owner_body["members"]}
    assert shared_home_setup["member1"]["user"]["username"] not in usernames



def test_delete_account_of_shared_home_owner_transfers_ownership_to_oldest_member(client, shared_home_owner_setup):
    delete_response = client.delete("/auth/delete", headers=shared_home_owner_setup["headers"])
    old_owner_view = client.get("/home/", headers=shared_home_owner_setup["headers"])
    oldest_view = client.get("/home/", headers=shared_home_owner_setup["oldest_member_ctx"]["headers"])

    assert delete_response.status_code == 200, delete_response.text
    body = delete_response.json()
    assert body["code"] == "ACCOUNT_DELETED_AND_OWNER_TRANSFERRED"
    assert old_owner_view.status_code in (401, 403, 404), old_owner_view.text
    assert oldest_view.status_code == 200, oldest_view.text

    oldest_body = oldest_view.json()
    roles = {member["username"]: member["role"] for member in oldest_body["members"]}
    assert roles[shared_home_owner_setup["oldest_member"]["username"]] == "owner"
