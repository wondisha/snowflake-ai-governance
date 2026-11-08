#!/usr/bin/env python3
"""
Setup Verification Script
Checks all prerequisites before deployment
"""

import os
import sys
import json
import platform
import subprocess
from pathlib import Path

class SetupVerifier:
    def __init__(self):
        self.checks = {}
        self.project_root = Path("/c/LabFiles/Snowflake-AI-Toolkit")
        self.issues = []
        self.warnings = []

    def run_all_checks(self):
        """Run all verification checks"""
        print("""
╔════════════════════════════════════════════════════════╗
║        SETUP VERIFICATION CHECKLIST                   ║
║    Checking prerequisites for deployment              ║
╚════════════════════════════════════════════════════════╝
        """)

        # Check environment
        self._check_operating_system()
        self._check_python_version()
        self._check_project_directory()
        self._check_deployment_files()
        self._check_python_dependencies()
        self._check_snowflake_credentials()
        self._check_snowflake_connectivity()

        # Print results
        self._print_results()

        return len(self.issues) == 0

    def _check_operating_system(self):
        """Check operating system"""
        print("🔍 Checking Operating System...")
        os_name = platform.system()
        self.checks["OS"] = True

        if os_name in ["Windows", "Darwin", "Linux"]:
            print(f"   ✅ {os_name}")
        else:
            print(f"   ⚠️  Unusual OS: {os_name}")
            self.warnings.append(f"Unusual OS: {os_name}")

    def _check_python_version(self):
        """Check Python version"""
        print("🔍 Checking Python Version...")

        version = sys.version_info
        version_str = f"{version.major}.{version.minor}.{version.micro}"

        if version.major >= 3 and version.minor >= 8:
            print(f"   ✅ Python {version_str}")
            self.checks["Python"] = True
        else:
            print(f"   ❌ Python {version_str} (need 3.8+)")
            self.checks["Python"] = False
            self.issues.append(f"Python 3.8+ required (found {version_str})")

    def _check_project_directory(self):
        """Check project directory"""
        print("🔍 Checking Project Directory...")

        if self.project_root.exists():
            print(f"   ✅ Found: {self.project_root}")
            self.checks["Project Dir"] = True
        else:
            print(f"   ❌ Not found: {self.project_root}")
            self.checks["Project Dir"] = False
            self.issues.append(f"Project directory not found: {self.project_root}")

    def _check_deployment_files(self):
        """Check required deployment files"""
        print("🔍 Checking Deployment Files...")

        required_files = [
            "deploy.py",
            "validate_deployment.py",
            "deployment_config.json",
            "src/database/schema.sql",
            "PHASE_5_README.md",
            "PHASE_5_SUMMARY.md",
        ]

        all_exist = True
        for file_name in required_files:
            file_path = self.project_root / file_name
            if file_path.exists():
                print(f"   ✅ {file_name}")
            else:
                print(f"   ❌ {file_name}")
                all_exist = False
                self.issues.append(f"Missing file: {file_name}")

        self.checks["Files"] = all_exist

    def _check_python_dependencies(self):
        """Check Python dependencies"""
        print("🔍 Checking Python Dependencies...")

        required_packages = [
            ("snowflake.connector", "snowflake-connector-python"),
            ("numpy", "numpy"),
            ("yaml", "pyyaml"),
            ("requests", "requests"),
        ]

        all_installed = True
        for import_name, package_name in required_packages:
            try:
                __import__(import_name)
                print(f"   ✅ {package_name}")
            except ImportError:
                print(f"   ❌ {package_name}")
                all_installed = False
                self.issues.append(f"Missing dependency: {package_name}")

        self.checks["Dependencies"] = all_installed

    def _check_snowflake_credentials(self):
        """Check Snowflake credentials configuration"""
        print("🔍 Checking Snowflake Configuration...")

        config_file = self.project_root / "deployment_config.json"

        if not config_file.exists():
            print("   ⚠️  deployment_config.json not found")
            self.checks["Config"] = False
            self.warnings.append("deployment_config.json not found (will be created)")
            return

        try:
            with open(config_file, 'r') as f:
                config = json.load(f)

            sf = config.get("snowflake", {})
            required_creds = ["account", "user", "password", "warehouse", "database"]

            missing_or_default = []
            for cred in required_creds:
                value = sf.get(cred, "")
                if not value or value.startswith("YOUR_"):
                    missing_or_default.append(cred)

            if missing_or_default:
                print(f"   ⚠️  Credentials not configured: {', '.join(missing_or_default)}")
                self.checks["Config"] = False
                self.warnings.append(f"Credentials need to be configured: {', '.join(missing_or_default)}")
            else:
                print("   ✅ Credentials configured")
                self.checks["Config"] = True

        except Exception as e:
            print(f"   ❌ Error reading config: {str(e)}")
            self.checks["Config"] = False
            self.issues.append(f"Error reading config: {str(e)}")

    def _check_snowflake_connectivity(self):
        """Check Snowflake connectivity"""
        print("🔍 Checking Snowflake Connectivity...")

        config_file = self.project_root / "deployment_config.json"

        if not config_file.exists():
            print("   ⏭️  Skipped (config not found yet)")
            self.checks["Connectivity"] = None
            return

        try:
            with open(config_file, 'r') as f:
                config = json.load(f)

            sf = config.get("snowflake", {})

            # Check if credentials are configured
            if sf.get("account", "").startswith("YOUR_"):
                print("   ⏭️  Skipped (credentials not configured)")
                self.checks["Connectivity"] = None
                return

            # Try to connect
            import snowflake.connector

            connection = snowflake.connector.connect(
                account=sf.get("account"),
                user=sf.get("user"),
                password=sf.get("password"),
                warehouse=sf.get("warehouse")
            )

            cursor = connection.cursor()
            cursor.execute("SELECT CURRENT_ACCOUNT(), CURRENT_USER(), CURRENT_WAREHOUSE()")
            result = cursor.fetchone()

            print(f"   ✅ Connected to {result[0]} as {result[1]}")
            print(f"      Warehouse: {result[2]}")

            connection.close()
            self.checks["Connectivity"] = True

        except Exception as e:
            error_msg = str(e)
            if "incorrect username or password" in error_msg.lower():
                print("   ❌ Authentication failed (wrong credentials)")
                self.issues.append("Snowflake credentials incorrect")
            elif "warehouse" in error_msg.lower():
                print(f"   ❌ Warehouse issue: {error_msg}")
                self.issues.append(f"Warehouse error: {error_msg}")
            else:
                print(f"   ❌ Connection failed: {error_msg}")
                self.issues.append(f"Snowflake connection failed: {error_msg}")

            self.checks["Connectivity"] = False

    def _print_results(self):
        """Print verification results"""
        print("\n")
        print("""╔════════════════════════════════════════════════════════╗
║           VERIFICATION RESULTS                         ║
╚════════════════════════════════════════════════════════╝
        """)

        for check_name, result in self.checks.items():
            if result is True:
                status = "✅ PASS"
            elif result is False:
                status = "❌ FAIL"
            else:
                status = "⏭️  SKIP"

            print(f"{status}  {check_name}")

        print("\n")

        if self.issues:
            print("🔴 ISSUES TO FIX:")
            for i, issue in enumerate(self.issues, 1):
                print(f"   {i}. {issue}")
            print()

        if self.warnings:
            print("⚠️  WARNINGS (can proceed, but fix these):")
            for i, warning in enumerate(self.warnings, 1):
                print(f"   {i}. {warning}")
            print()

        if not self.issues:
            print("✅ SETUP VERIFICATION PASSED!")
            print("\nYou're ready to deploy. Run:")
            print("   python validate_deployment.py deployment_config.json")
            print("   python deploy.py deployment_config.json")
        else:
            print("❌ SETUP VERIFICATION FAILED!")
            print("\nFix the issues above before deploying.")

    def get_recommendations(self):
        """Get recommendations based on verification"""
        print("\n")
        print("""╔════════════════════════════════════════════════════════╗
║              RECOMMENDED NEXT STEPS                    ║
╚════════════════════════════════════════════════════════╝
        """)

        if self.checks.get("Config") is False or self.checks.get("Config") is None:
            print("\n1️⃣  CONFIGURE CREDENTIALS")
            print("""
   Edit deployment_config.json:

   • account: Your Snowflake account ID
     Find in URL: https://xy12345.us-west-2.snowflakecomputing.com
     Use: xy12345.us-west-2

   • user: Your Snowflake username

   • password: Your Snowflake password

   • warehouse: Your compute warehouse name
     Or create one in Snowflake:
     CREATE WAREHOUSE GOVERNANCE_WH WAREHOUSE_SIZE = 'MEDIUM';

   • database: Database for governance
     Or create one in Snowflake:
     CREATE DATABASE GOVERNANCE;

   Then save the file.
            """)

        if self.checks.get("Dependencies") is False:
            print("\n2️⃣  INSTALL DEPENDENCIES")
            print("""
   Run this command:

   pip install snowflake-connector-python numpy pyyaml requests
            """)

        if self.checks.get("Connectivity") is False:
            print("\n3️⃣  FIX SNOWFLAKE CONNECTIVITY")
            print("""
   • Verify credentials in deployment_config.json
   • Check warehouse exists and is accessible
   • Ensure network allows Snowflake connection
   • Try logging in via Snowflake web UI to verify credentials
            """)

        if not self.issues:
            print("\n✅ ALL CHECKS PASSED!")
            print("""
   Your setup is ready for deployment.

   Next step: Run deployment validation

   python validate_deployment.py deployment_config.json
            """)


def main():
    """Main verification entry point"""
    verifier = SetupVerifier()

    success = verifier.run_all_checks()
    verifier.get_recommendations()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
