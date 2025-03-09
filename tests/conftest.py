import os
import pytest
import requests

@pytest.fixture(scope="session")
def base_url():
    # Base URL for the airportgap API endpoints.
    return "https://airportgap.com/api"

@pytest.fixture(scope="session")
def credentials():
    # preferably have these in obfuscated environment variables
    # this will do for now.
    email = "jpsmith866@gmail.com"
    password = "password1"
    return {"email": email, "password": password}

@pytest.fixture(scope="session")
def auth_token(base_url, credentials):
    url = f"{base_url}/tokens"
    response = requests.post(url, data=credentials)
    assert response.status_code == 200, f"Token request failed with status {response.status_code}"
    token = response.json().get("token")
    if not token:
        raise ValueError("No token found in the response")
    return token

@pytest.fixture(scope="session")
def auth_headers(auth_token):
    return {
        "Authorization": f"Bearer token={auth_token}",
        "Content-Type": "application/json"
    }

# Clear favourites down to start fresh
@pytest.fixture(autouse=True)
def clear_favorites_before_test(base_url, auth_headers):
    url_clear = f"{base_url}/favorites/clear_all"
    response = requests.delete(url_clear, headers=auth_headers)
    # 204 No Content is expected, but if there are no favorites it might return 404 or 204.
    # with more time it might be an idea to ping the endpoint before the test starts to see if there 
    # are any faves, delete, then check again to assert theyve been cleared.
    assert response.status_code in [204, 404], f"Expected status 204 or 404, got {response.status_code}"
    yield

# Its usually pretty useful to know if an api call took a bit longer than usual
# even if it technically passes the test. Yes, we got the airports, but why did
# it take 5 seconds? The airport API is fairly simple, so a default of 1 second
# should be more than enough
DEFAULT_SLOW_TEST_THRESHOLD = 1.0
# And then store any slow ones for the report
slow_thresholds = {}
def pytest_collection_modifyitems(session, config, items):
    for item in items:
        marker = item.get_closest_marker("slow_threshold")
        threshold = marker.args[0] if marker and marker.args else DEFAULT_SLOW_TEST_THRESHOLD
        slow_thresholds[item.nodeid] = threshold

def pytest_runtest_logreport(report):
    if report.when == "call":
        # Look up the threshold using the test’s nodeid.
        threshold = slow_thresholds.get(report.nodeid, DEFAULT_SLOW_TEST_THRESHOLD)
        if report.duration > threshold:
            report.slow_warning = f"Test took {report.duration:.2f}s (threshold: {threshold:.2f}s)"
        else:
            report.slow_warning = ""


def pytest_html_results_table_header(cells):
    # Add a section to the HTML report for slow warning
    cells.insert(2, "<th>Slow Warning</th>")

def pytest_html_results_table_row(report, cells):
    # Insert the slow warning message
    slow_warning = getattr(report, "slow_warning", "")
    cells.insert(2, f"<td>{slow_warning}</td>")

# load all the test data
def load_json(filename):
    filepath = os.path.join(os.path.dirname(__file__), "test_data", filename)
    with open(filepath, "r") as f:
        import json
        return json.load(f)

@pytest.fixture(scope="session")
def distance_test_data():
    return load_json("airports_distance.json")

@pytest.fixture(scope="session")
def airport_test_data():
    return load_json("airports.json")

@pytest.fixture(scope="session")
def favourite_test_data():
    return load_json("favourites.json")