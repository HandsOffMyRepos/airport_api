import requests
import pytest
from haversine import haversine, Unit

# We need favourites to query given the need to clear them down too, this will create for us.
def create_favourite(base_url, auth_headers, airport_id, note="Test favorite"):
    url = f"{base_url}/favorites"
    unique_note = f"{note}"
    payload = {"airport_id": airport_id, "note": unique_note}
    headers = auth_headers.copy()
    headers["Content-Type"] = "application/x-www-form-urlencoded"
    response = requests.post(url, data=payload, headers=headers)
    if response.status_code != 201:
        print("Create favorite failed. Status code:", response.status_code)
        print("Response text:", response.text)
    assert response.status_code == 201, f"Expected status 201, got {response.status_code}"
    json_data = response.json()
    favorite_id = json_data.get("data", {}).get("id")
    assert favorite_id is not None, "Favorite ID should not be None"
    return favorite_id

def test_get_airports(base_url, auth_headers):
    url = f"{base_url}/airports"
    response = requests.get(url, headers=auth_headers)
    assert response.status_code == 200, f"Expected status 200, got {response.status_code}"
    json_data = response.json()
    assert "data" in json_data, "Expected key 'data' in response"
    # Check the pagination links
    if json_data["data"]:
        assert "links" in json_data, "Expected key 'links' for pagination in response"

def test_get_airport_by_id(base_url, auth_headers, airport_test_data):
    for entry in airport_test_data:
        airport_id = entry["id"]
        url = f"{base_url}/airports/{airport_id}"
        response = requests.get(url, headers=auth_headers)
        assert response.status_code == 200, f"GET airport {airport_id} returned {response.status_code}"
        json_data = response.json()
        assert json_data["data"].get("id") == airport_id, f"Expected airport id '{airport_id}'"

def test_post_airports_distance(base_url, auth_headers, distance_test_data):
    for test_case in distance_test_data:
        from_airport = test_case["from"]
        to_airport = test_case["to"]
        url = f"{base_url}/airports/distance"
        payload = {"from": from_airport, "to": to_airport}
        headers = auth_headers.copy()
        headers["Content-Type"] = "application/x-www-form-urlencoded"
        response = requests.post(url, data=payload, headers=headers)
        assert response.status_code == 200, f"Distance request from {from_airport} to {to_airport} returned {response.status_code}"
        json_data = response.json()
        attributes = json_data.get("data", {}).get("attributes", {})
        for key in ["from_airport", "to_airport", "miles", "kilometers", "nautical_miles"]:
            assert key in attributes, f"Expected key '{key}' in response attributes"

        # Validate distance calculations using haversine. Not done this before, interesting exercise.
        # thought this would be way more complex until i saw you get the lat and long from the endpoint.
        # would be REALLY interesting to try do this without that.
        f_airport = attributes["from_airport"]
        t_airport = attributes["to_airport"]
        from_coords = (float(f_airport["latitude"]), float(f_airport["longitude"]))
        to_coords = (float(t_airport["latitude"]), float(t_airport["longitude"]))
        expected_miles = haversine(from_coords, to_coords, unit=Unit.MILES)
        expected_kilometers = haversine(from_coords, to_coords, unit=Unit.KILOMETERS)
        expected_nautical = expected_miles * 0.868976

        actual_miles = float(attributes["miles"])
        actual_kilometers = float(attributes["kilometers"])
        actual_nautical = float(attributes["nautical_miles"])
        tolerance = 0.01
        assert abs(actual_miles - expected_miles) / expected_miles < tolerance, \
            f"Miles value mismatch: expected ~{expected_miles}, got {actual_miles}"
        assert abs(actual_kilometers - expected_kilometers) / expected_kilometers < tolerance, \
            f"Kilometers value mismatch: expected ~{expected_kilometers}, got {actual_kilometers}"
        assert abs(actual_nautical - expected_nautical) / expected_nautical < tolerance, \
            f"Nautical miles value mismatch: expected ~{expected_nautical}, got {actual_nautical}"

# This test is a bit more complex, so ill set the threshold for slow running to be
# 2.5sec instead of 1
@pytest.mark.slow_threshold(2.5)
def test_create_get_update_delete_favorite(base_url, auth_headers, favourite_test_data):
    for fav_data in favourite_test_data:
        airport_id = fav_data["airport_id"]
        original_note = fav_data["note"]
        updated_note = fav_data["updated_note"]

    # Create favorite
    favorite_id = create_favourite(base_url, auth_headers, airport_id, note=original_note)

    # Get favorite
    url = f"{base_url}/favorites/{favorite_id}"
    response = requests.get(url, headers=auth_headers)
    assert response.status_code == 200, f"GET favorite returned {response.status_code}"
    json_data = response.json()
    assert json_data.get("data", {}).get("attributes", {}).get("note") == original_note, "Favorite note mismatch"

    # Patch fave
    url_patch = f"{base_url}/favorites/{favorite_id}"
    patch_headers = auth_headers.copy()
    patch_headers["Content-Type"] = "application/x-www-form-urlencoded"
    patch_response = requests.patch(url_patch, data={"note": updated_note}, headers=patch_headers)
    assert patch_response.status_code == 200, f"PATCH returned {patch_response.status_code}"
    patch_json = patch_response.json()
    assert patch_json.get("data", {}).get("attributes", {}).get("note") == updated_note, "Updated note mismatch"

    # Delete favorite
    url_delete = f"{base_url}/favorites/{favorite_id}"
    delete_response = requests.delete(url_delete, headers=auth_headers)
    assert delete_response.status_code == 204, f"DELETE returned {delete_response.status_code}"

    # Confirm deletion
    get_deleted = requests.get(url, headers=auth_headers)
    assert get_deleted.status_code == 404, f"Expected 404 after deletion, got {get_deleted.status_code}"

def test_delete_clear_all_favorites(base_url, auth_headers, favourite_test_data):
    # Create two favorites
    if len(favourite_test_data) >= 2:
        fav1 = create_favourite(base_url, auth_headers, favourite_test_data[0]["airport_id"], note=favourite_test_data[0]["note"])
        fav2 = create_favourite(base_url, auth_headers, favourite_test_data[1]["airport_id"], note=favourite_test_data[1]["note"])
    url_clear = f"{base_url}/favorites/clear_all"
    clear_response = requests.delete(url_clear, headers=auth_headers)
    assert clear_response.status_code == 204, f"Clear all returned {clear_response.status_code}"
    get_response = requests.get(f"{base_url}/favorites", headers=auth_headers)
    assert get_response.status_code == 200, f"GET favorites returned {get_response.status_code}"
    json_data = get_response.json()
    assert "data" in json_data, "Expected key 'data' in response"
    assert len(json_data["data"]) == 0, "Expected no favorites after clearing"
