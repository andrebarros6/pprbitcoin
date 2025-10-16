"""
Test script to validate all API endpoints
Run with the API server running on http://localhost:8000
"""
import requests
import json
from datetime import datetime, timedelta
from typing import Dict, List

BASE_URL = "http://localhost:8000"


class Colors:
    """ANSI color codes"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    END = '\033[0m'
    BOLD = '\033[1m'


def print_header(text: str):
    """Print formatted header"""
    print(f"\n{Colors.CYAN}{Colors.BOLD}{'=' * 70}")
    print(f"  {text}")
    print(f"{'=' * 70}{Colors.END}\n")


def print_test(name: str, passed: bool, details: str = ""):
    """Print test result"""
    status = f"{Colors.GREEN}✓ PASS{Colors.END}" if passed else f"{Colors.RED}✗ FAIL{Colors.END}"
    print(f"{status} | {name}")
    if details:
        print(f"       {Colors.YELLOW}{details}{Colors.END}")


def test_endpoint(method: str, endpoint: str, expected_status: int = 200, params: Dict = None) -> Dict:
    """
    Test an API endpoint

    Args:
        method: HTTP method (GET, POST)
        endpoint: API endpoint path
        expected_status: Expected HTTP status code
        params: Query parameters

    Returns:
        Dict with test results
    """
    url = f"{BASE_URL}{endpoint}"

    try:
        if method == "GET":
            response = requests.get(url, params=params, timeout=10)
        elif method == "POST":
            response = requests.post(url, json=params, timeout=10)
        else:
            return {
                "success": False,
                "error": f"Unsupported method: {method}"
            }

        success = response.status_code == expected_status

        return {
            "success": success,
            "status_code": response.status_code,
            "data": response.json() if response.status_code == 200 else None,
            "response": response
        }

    except requests.exceptions.ConnectionError:
        return {
            "success": False,
            "error": "Connection refused. Is the API server running?"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def run_tests():
    """Run all API tests"""
    results = {
        "passed": 0,
        "failed": 0,
        "tests": []
    }

    print_header("PPR BITCOIN API TESTS")

    # Test 1: Root endpoint
    print_header("1. System Endpoints")

    result = test_endpoint("GET", "/")
    passed = result.get("success", False)
    print_test("GET /", passed, f"Status: {result.get('status_code', 'N/A')}")
    results["passed" if passed else "failed"] += 1

    # Test 2: Health check
    result = test_endpoint("GET", "/health")
    passed = result.get("success", False)
    print_test("GET /health", passed, f"Status: {result.get('status_code', 'N/A')}")
    results["passed" if passed else "failed"] += 1

    # Test 3: Get all PPRs
    print_header("2. PPR Endpoints")

    result = test_endpoint("GET", "/api/v1/pprs")
    passed = result.get("success", False)
    ppr_count = result.get("data", {}).get("total", 0) if passed else 0
    print_test("GET /api/v1/pprs", passed, f"Found {ppr_count} PPRs")
    results["passed" if passed else "failed"] += 1

    # Store first PPR ID for subsequent tests
    first_ppr_id = None
    if passed and ppr_count > 0:
        first_ppr_id = result["data"]["data"][0]["id"]
        print(f"       Using PPR ID: {first_ppr_id}")

    # Test 4: Get specific PPR
    if first_ppr_id:
        result = test_endpoint("GET", f"/api/v1/pprs/{first_ppr_id}")
        passed = result.get("success", False)
        ppr_name = result.get("data", {}).get("nome", "N/A") if passed else "N/A"
        print_test(f"GET /api/v1/pprs/{{id}}", passed, f"PPR: {ppr_name}")
        results["passed" if passed else "failed"] += 1

        # Test 5: Get PPR historical data
        result = test_endpoint("GET", f"/api/v1/pprs/{first_ppr_id}/historical")
        passed = result.get("success", False)
        record_count = len(result.get("data", {}).get("data", [])) if passed else 0
        print_test(f"GET /api/v1/pprs/{{id}}/historical", passed, f"Found {record_count} historical records")
        results["passed" if passed else "failed"] += 1

        # Test 6: Get PPR historical with date filter
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=365)
        result = test_endpoint("GET", f"/api/v1/pprs/{first_ppr_id}/historical", params={
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat()
        })
        passed = result.get("success", False)
        record_count = len(result.get("data", {}).get("data", [])) if passed else 0
        print_test(f"GET /api/v1/pprs/{{id}}/historical?dates", passed,
                   f"Found {record_count} records (last year)")
        results["passed" if passed else "failed"] += 1

    # Test 7: Bitcoin endpoints
    print_header("3. Bitcoin Endpoints")

    result = test_endpoint("GET", "/api/v1/bitcoin/latest")
    passed = result.get("success", False)
    btc_price = result.get("data", {}).get("preco_eur", "N/A") if passed else "N/A"
    btc_date = result.get("data", {}).get("data", "N/A") if passed else "N/A"
    print_test("GET /api/v1/bitcoin/latest", passed, f"Price: {btc_price} EUR (Date: {btc_date})")
    results["passed" if passed else "failed"] += 1

    # Test 8: Bitcoin historical
    result = test_endpoint("GET", "/api/v1/bitcoin/historical")
    passed = result.get("success", False)
    record_count = len(result.get("data", {}).get("data", [])) if passed else 0
    print_test("GET /api/v1/bitcoin/historical", passed, f"Found {record_count} historical records")
    results["passed" if passed else "failed"] += 1

    # Test 9: Bitcoin historical with date filter
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=365)
    result = test_endpoint("GET", "/api/v1/bitcoin/historical", params={
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat()
    })
    passed = result.get("success", False)
    record_count = len(result.get("data", {}).get("data", [])) if passed else 0
    print_test("GET /api/v1/bitcoin/historical?dates", passed,
               f"Found {record_count} records (last year)")
    results["passed" if passed else "failed"] += 1

    # Test 10: Bitcoin historical (last 30 days)
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=30)
    result = test_endpoint("GET", "/api/v1/bitcoin/historical", params={
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat()
    })
    passed = result.get("success", False)
    record_count = len(result.get("data", {}).get("data", [])) if passed else 0
    print_test("GET /api/v1/bitcoin/historical (30 days)", passed,
               f"Found {record_count} records")
    results["passed" if passed else "failed"] += 1

    # Summary
    print_header("TEST SUMMARY")
    total = results["passed"] + results["failed"]
    pass_rate = (results["passed"] / total * 100) if total > 0 else 0

    print(f"Total Tests: {total}")
    print(f"{Colors.GREEN}Passed: {results['passed']}{Colors.END}")
    print(f"{Colors.RED}Failed: {results['failed']}{Colors.END}")
    print(f"Pass Rate: {pass_rate:.1f}%")

    if results["failed"] == 0:
        print(f"\n{Colors.GREEN}{Colors.BOLD}🎉 ALL TESTS PASSED!{Colors.END}")
    else:
        print(f"\n{Colors.YELLOW}⚠️  Some tests failed. Check the output above.{Colors.END}")

    return results


def test_data_integrity():
    """Test data integrity and relationships"""
    print_header("4. Data Integrity Tests")

    # Test PPR-Historical relationship
    result = test_endpoint("GET", "/api/v1/pprs")
    if result.get("success"):
        pprs = result["data"]["data"]

        for ppr in pprs[:3]:  # Test first 3 PPRs
            hist_result = test_endpoint("GET", f"/api/v1/pprs/{ppr['id']}/historical")
            has_data = len(hist_result.get("data", {}).get("data", [])) > 0 if hist_result.get("success") else False

            print_test(
                f"PPR '{ppr['nome']}' has historical data",
                has_data,
                f"Records: {len(hist_result.get('data', {}).get('data', [])) if hist_result.get('success') else 0}"
            )

    # Test Bitcoin data continuity
    result = test_endpoint("GET", "/api/v1/bitcoin/historical", params={
        "start_date": (datetime.now() - timedelta(days=7)).date().isoformat()
    })

    if result.get("success"):
        records = result["data"]["data"]
        has_recent_data = len(records) > 0
        print_test(
            "Bitcoin has recent data (last 7 days)",
            has_recent_data,
            f"Found {len(records)} records"
        )


if __name__ == "__main__":
    print(f"{Colors.BOLD}PPR Bitcoin API Test Suite{Colors.END}")
    print(f"Testing API at: {Colors.CYAN}{BASE_URL}{Colors.END}")
    print(f"Make sure the API server is running (python app.py)")
    print()

    try:
        # Check if server is running
        response = requests.get(BASE_URL, timeout=2)
        print(f"{Colors.GREEN}✓ API server is running{Colors.END}\n")
    except:
        print(f"{Colors.RED}✗ Cannot connect to API server at {BASE_URL}{Colors.END}")
        print(f"{Colors.YELLOW}Please start the server with: python app.py{Colors.END}\n")
        exit(1)

    # Run tests
    results = run_tests()

    # Test data integrity
    test_data_integrity()

    print(f"\n{Colors.CYAN}{'=' * 70}{Colors.END}\n")

    # Exit with appropriate code
    exit(0 if results["failed"] == 0 else 1)