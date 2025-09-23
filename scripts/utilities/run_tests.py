#!/usr/bin/env python3
"""
Financial Command Center AI - Test Runner (clean)
- Installs test dependencies
- Runs tests in various modes
- Generates coverage and optional HTML reports
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import webbrowser
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
os.chdir(REPO_ROOT)


class TestRunner:
    def __init__(self) -> None:
        self.project_root = REPO_ROOT
        self.reports_dir = REPO_ROOT / "reports"
        self.coverage_dir = REPO_ROOT / "htmlcov"
        self.reports_dir.mkdir(exist_ok=True)
        self.coverage_dir.mkdir(exist_ok=True)

    def run(self, cmd: list[str], title: str) -> bool:
        print("
" + "=" * 60)
        print(title)
        print("=" * 60)
        print("Command:", " ".join(cmd))
        try:
            result = subprocess.run(cmd)
            ok = result.returncode == 0
            print(f"Result: {'SUCCESS' if ok else 'FAIL'} (exit {result.returncode})")
            return ok
        except Exception as e:
            print("ERROR:", e)
            return False

    def install_test_dependencies(self) -> bool:
        return self.run([sys.executable, "-m", "pip", "install", "-r", "requirements-test.txt"], "Install test dependencies")

    def run_unit(self) -> bool:
        return self.run([sys.executable, "-m", "pytest", "tests/unit", "-v", "--tb=short", "--cov=auth", "--cov-report=term-missing"], "Run unit tests")

    def run_integration(self) -> bool:
        return self.run([sys.executable, "-m", "pytest", "tests/integration", "-v", "--tb=short"], "Run integration tests")

    def run_all(self) -> bool:
        return self.run([
            sys.executable,
            "-m",
            "pytest",
            "tests",
            "-v",
            "--tb=short",
            "--cov=auth",
            "--cov=app",
            "--cov-report=html:htmlcov",
            "--cov-report=term-missing",
            "--cov-report=xml",
            "--html=reports/report.html",
            "--self-contained-html",
        ], "Run all tests with coverage")

    def run_security(self) -> bool:
        return self.run([sys.executable, "-m", "pytest", "-m", "security", "-v", "--tb=short"], "Run security tests")

    def run_api(self) -> bool:
        return self.run([sys.executable, "-m", "pytest", "-m", "api", "-v", "--tb=short"], "Run API tests")

    def run_quick(self) -> bool:
        return self.run([sys.executable, "-m", "pytest", "-m", "not slow", "-v", "--tb=line", "--cov=auth", "--cov-report=term"], "Run quick tests")

    def format_code(self) -> bool:
        return self.run([sys.executable, "-m", "black", "auth/", "app.py", "tests/"], "Run Black formatter")

    def lint_code(self) -> bool:
        ok = True
        ok &= self.run([sys.executable, "-m", "black", "--check", "--diff", "auth/", "app.py", "tests/"], "Check formatting (Black)")
        ok &= self.run([sys.executable, "-m", "isort", "--check-only", "--diff", "auth/", "app.py", "tests/"], "Check imports (isort)")
        ok &= self.run([sys.executable, "-m", "flake8", "auth/", "app.py", "tests/"], "Run flake8")
        return bool(ok)

    def open_reports(self) -> None:
        cov_index = self.coverage_dir / "index.html"
        report = self.reports_dir / "report.html"
        if cov_index.exists():
            webbrowser.open(f"file://{cov_index.resolve()}")
            print("Opened coverage report:", cov_index)
        if report.exists():
            webbrowser.open(f"file://{report.resolve()}")
            print("Opened test report:", report)

    def run_ci(self) -> bool:
        steps: list[tuple[str, callable[[], bool]]] = [
            ("Install dependencies", self.install_test_dependencies),
            ("Format code", self.format_code),
            ("Lint code", self.lint_code),
            ("Run all tests", self.run_all),
        ]
        results: dict[str, bool] = {}
        for name, fn in steps:
            print(f"
--- {name} ---")
            ok = fn()
            results[name] = ok
            if not ok:
                print("CI failed at:", name)
                return False
        print("
CI SUCCESS")
        for name, ok in results.items():
            print(f"  {name}: {'PASS' if ok else 'FAIL'}")
        return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Financial Command Center AI - Test Runner")
    parser.add_argument("--mode", choices=["unit", "integration", "all", "security", "api", "quick", "lint", "format", "ci"], default="quick")
    parser.add_argument("--install", action="store_true", help="Install test dependencies")
    parser.add_argument("--open", action="store_true", help="Open reports after run")
    args = parser.parse_args()

    runner = TestRunner()
    print("Test Runner")
    print("Mode:", args.mode)
    print("Root:", runner.project_root)

    if args.install:
        if not runner.install_test_dependencies():
            sys.exit(1)

    success = True
    if args.mode == "unit":
        success = runner.run_unit()
    elif args.mode == "integration":
        success = runner.run_integration()
    elif args.mode == "all":
        success = runner.run_all()
    elif args.mode == "security":
        success = runner.run_security()
    elif args.mode == "api":
        success = runner.run_api()
    elif args.mode == "quick":
        success = runner.run_quick()
    elif args.mode == "lint":
        success = runner.lint_code()
    elif args.mode == "format":
        success = runner.format_code()
    elif args.mode == "ci":
        success = runner.run_ci()

    if args.open and success:
        runner.open_reports()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
