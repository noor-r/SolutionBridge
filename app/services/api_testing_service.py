"""Automated API Testing and HTML/JSON Report Generation Service."""

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import httpx
from sqlalchemy.orm import Session
from app.db.models import ApiEndpoint, ApiTestRun, Customer
from app.utils.request_id import generate_request_id
from app.core.config import settings
from app.core.logging import logger

REPORTS_DIR = Path(__file__).resolve().parent.parent.parent / "reports"
REPORTS_DIR.mkdir(exist_ok=True)


class ApiTestingService:
    """Executes automated integration test suites and generates audit reports."""

    def __init__(self, db: Session):
        self.db = db
        self.base_url = settings.BACKEND_API_URL

    def run_all_tests(self, customer_id: int = 1) -> Dict[str, Any]:
        """Execute active registered endpoint integration tests."""
        endpoints = self.db.query(ApiEndpoint).filter(ApiEndpoint.active == True).all()
        customer = self.db.query(Customer).filter(Customer.id == customer_id).first()

        results: List[Dict[str, Any]] = []
        total_latency = 0.0
        passed_count = 0
        failed_count = 0
        error_count = 0

        # Sample headers
        headers = {
            "X-Customer-ID": str(customer_id),
            "Content-Type": "application/json",
        }

        with httpx.Client(base_url=self.base_url, timeout=5.0) as client:
            for ep in endpoints:
                req_id = generate_request_id()
                headers["X-Request-ID"] = req_id

                # Format endpoint if parameterized
                target_path = ep.endpoint.replace("{customer_id}", str(customer_id)).replace("{order_id}", "1").replace("{product_id}", "1")

                start_t = time.perf_counter()
                status_code = 500
                resp_body = ""
                error_msg = None
                test_status = "ERROR"

                try:
                    if ep.method.upper() == "GET":
                        resp = client.get(target_path, headers=headers)
                    elif ep.method.upper() == "POST":
                        payload = {"customer_id": customer_id, "external_order_id": f"TEST-{req_id}", "amount": 99.50}
                        resp = client.post(target_path, json=payload, headers=headers)
                    else:
                        resp = client.get(target_path, headers=headers)

                    latency_ms = round((time.perf_counter() - start_t) * 1000, 2)
                    status_code = resp.status_code
                    resp_body = resp.text[:500]

                    if status_code == ep.expected_status:
                        if latency_ms <= ep.max_response_time_ms:
                            test_status = "PASSED"
                            passed_count += 1
                        else:
                            test_status = "FAILED"
                            error_msg = f"Latency SLA breach: {latency_ms}ms > threshold {ep.max_response_time_ms}ms"
                            failed_count += 1
                    else:
                        test_status = "FAILED"
                        error_msg = f"Status code mismatch: expected {ep.expected_status}, received {status_code}"
                        failed_count += 1

                except Exception as exc:
                    latency_ms = round((time.perf_counter() - start_t) * 1000, 2)
                    test_status = "ERROR"
                    error_msg = str(exc)
                    error_count += 1

                total_latency += latency_ms

                # Record in MySQL
                run_record = ApiTestRun(
                    customer_id=customer_id,
                    endpoint_id=ep.id,
                    request_id=req_id,
                    status_code=status_code,
                    response_time_ms=latency_ms,
                    test_status=test_status,
                    response_body=resp_body,
                    error_message=error_msg,
                    created_at=datetime.now(timezone.utc),
                )
                self.db.add(run_record)

                results.append({
                    "endpoint_id": ep.id,
                    "name": ep.name,
                    "method": ep.method,
                    "endpoint": target_path,
                    "request_id": req_id,
                    "status_code": status_code,
                    "response_time_ms": latency_ms,
                    "test_status": test_status,
                    "error_message": error_msg,
                })

        self.db.commit()

        total_tests = len(results)
        avg_latency = round(total_latency / total_tests, 2) if total_tests > 0 else 0.0
        pass_rate = round(100.0 * passed_count / total_tests, 2) if total_tests > 0 else 0.0

        summary = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "customer_id": customer_id,
            "total_tests": total_tests,
            "passed": passed_count,
            "failed": failed_count,
            "errors": error_count,
            "pass_rate_percent": pass_rate,
            "avg_response_time_ms": avg_latency,
            "test_results": results,
        }

        # Generate reports/api_test_report.json and .html
        self._write_reports(summary)
        return summary

    def _write_reports(self, summary: Dict[str, Any]):
        """Write JSON and HTML test reports."""
        json_file = REPORTS_DIR / "api_test_report.json"
        html_file = REPORTS_DIR / "api_test_report.html"

        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)

        # Generate responsive enterprise HTML report
        rows_html = ""
        for r in summary.get("test_results", []):
            status_badge = (
                '<span style="background-color: #22c55e; color: white; padding: 4px 8px; border-radius: 4px; font-weight: bold;">PASSED</span>'
                if r["test_status"] == "PASSED"
                else '<span style="background-color: #ef4444; color: white; padding: 4px 8px; border-radius: 4px; font-weight: bold;">FAILED</span>'
            )
            rows_html += f"""
            <tr>
                <td>{r['name']}</td>
                <td><code>{r['method']} {r['endpoint']}</code></td>
                <td><code>{r['request_id']}</code></td>
                <td>{r['status_code']}</td>
                <td>{r['response_time_ms']} ms</td>
                <td>{status_badge}</td>
                <td style="color: #ef4444;">{r['error_message'] or '-'}</td>
            </tr>
            """

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>SolutionBridge — API Integration Test Report</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; margin: 40px; background: #0f172a; color: #f8fafc; }}
        .card {{ background: #1e293b; border-radius: 8px; padding: 24px; margin-bottom: 24px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.3); }}
        .header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #334155; padding-bottom: 16px; }}
        .kpi-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin: 24px 0; }}
        .kpi {{ background: #0f172a; padding: 16px; border-radius: 6px; border-left: 4px solid #3b82f6; }}
        .kpi h3 {{ margin: 0; font-size: 13px; color: #94a3b8; text-transform: uppercase; }}
        .kpi p {{ margin: 8px 0 0 0; font-size: 28px; font-weight: bold; color: #f8fafc; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 16px; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #334155; }}
        th {{ background: #0f172a; color: #94a3b8; font-size: 12px; text-transform: uppercase; }}
        code {{ background: #334155; padding: 2px 6px; border-radius: 4px; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="card">
        <div class="header">
            <div>
                <h1 style="margin:0; font-size: 24px;">SolutionBridge API Integration Report</h1>
                <p style="margin:4px 0 0 0; color: #94a3b8;">Automated Product Solutions Engineering Test Run</p>
            </div>
            <div>
                <span style="color: #94a3b8; font-size: 13px;">Generated at: {summary['timestamp']}</span>
            </div>
        </div>

        <div class="kpi-grid">
            <div class="kpi" style="border-left-color: #3b82f6;">
                <h3>Total Endpoints Tested</h3>
                <p>{summary['total_tests']}</p>
            </div>
            <div class="kpi" style="border-left-color: #22c55e;">
                <h3>Pass Rate</h3>
                <p>{summary['pass_rate_percent']}%</p>
            </div>
            <div class="kpi" style="border-left-color: #ef4444;">
                <h3>Failed Endpoints</h3>
                <p>{summary['failed'] + summary['errors']}</p>
            </div>
            <div class="kpi" style="border-left-color: #eab308;">
                <h3>Average Response Time</h3>
                <p>{summary['avg_response_time_ms']} ms</p>
            </div>
        </div>

        <table>
            <thead>
                <tr>
                    <th>Test Name</th>
                    <th>Endpoint</th>
                    <th>Request ID</th>
                    <th>Status</th>
                    <th>Latency</th>
                    <th>Result</th>
                    <th>Diagnostics / Error</th>
                </tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
        </table>
    </div>
</body>
</html>
"""
        with open(html_file, "w", encoding="utf-8") as f:
            f.write(html_content)

        logger.info(f"Test reports written to {json_file} and {html_file}")
