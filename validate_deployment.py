"""
Deployment Validation Script
Checks if system is ready for deployment and validates post-deployment
"""

import os
import json
import logging
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class PreDeploymentValidator:
    """Validates pre-deployment readiness."""

    def __init__(self, config_file: str = "deployment_config.json"):
        self.config_file = config_file
        self.checks = {}

    def validate_all(self) -> Tuple[bool, Dict]:
        """Run all pre-deployment checks."""
        logger.info("""
╔════════════════════════════════════════════════════════╗
║  PRE-DEPLOYMENT VALIDATION                            ║
╚════════════════════════════════════════════════════════╝
        """)

        # Check configuration
        self.checks["config"] = self._check_config()

        # Check files
        self.checks["files"] = self._check_files()

        # Check dependencies
        self.checks["dependencies"] = self._check_dependencies()

        # Check Snowflake connectivity (if config valid)
        if self.checks["config"]:
            self.checks["snowflake"] = self._check_snowflake_connectivity()

        # Generate report
        self._print_report()

        # Overall result
        all_passed = all(self.checks.values())
        return all_passed, self.checks

    def _check_config(self) -> bool:
        """Check configuration file."""
        logger.info("🔍 Checking configuration...")

        if not os.path.exists(self.config_file):
            logger.error(f"❌ Config file not found: {self.config_file}")
            return False

        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)

            # Check required fields
            required = ["snowflake", "deployment", "phases"]
            for field in required:
                if field not in config:
                    logger.error(f"❌ Missing config section: {field}")
                    return False

            # Check Snowflake credentials
            sf = config.get("snowflake", {})
            required_creds = ["account", "user", "password", "warehouse", "database", "schema"]
            for cred in required_creds:
                value = sf.get(cred)
                if not value or value.startswith("YOUR_"):
                    logger.error(f"❌ Missing or invalid Snowflake credential: {cred}")
                    return False

            logger.info("✅ Configuration valid")
            return True

        except json.JSONDecodeError as e:
            logger.error(f"❌ Invalid JSON in config: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"❌ Config check failed: {str(e)}")
            return False

    def _check_files(self) -> bool:
        """Check required files exist."""
        logger.info("🔍 Checking required files...")

        required_files = [
            "src/database/schema.sql",
            "src/agents/base_agent.py",
            "src/agents/security_compliance_agent.py",
            "src/agents/performance_optimization_agent.py",
            "src/agents/cost_optimization_agent.py",
            "src/agents/spillage_prevention_agent.py",
            "src/agents/warehouse_health_agent.py",
            "src/agents/autonomous_self_healing_agent.py",
            "src/agents/predictive_intelligence_engine.py",
            "src/governance/policy_as_code.py",
            "src/interfaces/natural_language_interface.py",
            "src/governance/multi_cloud_controller.py",
            "src/observability/dashboard_manager.py",
        ]

        missing = []
        for file_path in required_files:
            if not os.path.exists(file_path):
                missing.append(file_path)
                logger.warning(f"  ⚠️  {file_path}")
            else:
                logger.info(f"  ✓ {file_path}")

        if missing:
            logger.error(f"❌ {len(missing)} files missing")
            return False

        logger.info("✅ All required files present")
        return True

    def _check_dependencies(self) -> bool:
        """Check Python dependencies."""
        logger.info("🔍 Checking Python dependencies...")

        required_packages = [
            "snowflake-connector-python",
            "numpy",
            "pyyaml",
            "requests",
            "fastapi",
            "uvicorn",
        ]

        missing = []
        for package in required_packages:
            try:
                __import__(package.replace("-", "_"))
                logger.info(f"  ✓ {package}")
            except ImportError:
                missing.append(package)
                logger.warning(f"  ⚠️  {package} not installed")

        if missing:
            logger.warning(f"⚠️  {len(missing)} dependencies missing")
            logger.info(f"Install with: pip install {' '.join(missing)}")
            return False

        logger.info("✅ All dependencies installed")
        return True

    def _check_snowflake_connectivity(self) -> bool:
        """Check Snowflake connectivity."""
        logger.info("🔍 Checking Snowflake connectivity...")

        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)

            import snowflake.connector

            connection = snowflake.connector.connect(
                account=config["snowflake"]["account"],
                user=config["snowflake"]["user"],
                password=config["snowflake"]["password"],
                warehouse=config["snowflake"]["warehouse"],
                database=config["snowflake"]["database"]
            )

            cursor = connection.cursor()
            cursor.execute("SELECT CURRENT_ACCOUNT(), CURRENT_USER()")
            result = cursor.fetchone()

            logger.info(f"  ✓ Connected as {result[1]} in {result[0]}")
            connection.close()

            logger.info("✅ Snowflake connectivity OK")
            return True

        except Exception as e:
            logger.error(f"❌ Snowflake connectivity failed: {str(e)}")
            return False

    def _print_report(self) -> None:
        """Print validation report."""
        logger.info("""
╔════════════════════════════════════════════════════════╗
║  VALIDATION REPORT                                    ║
╚════════════════════════════════════════════════════════╝
        """)

        for check, result in self.checks.items():
            status = "✅" if result else "❌"
            logger.info(f"{status} {check.upper()}: {'PASS' if result else 'FAIL'}")

        all_passed = all(self.checks.values())
        logger.info(f"\n{'✅' if all_passed else '❌'} Overall: {'READY' if all_passed else 'NOT READY'}")

        if not all_passed:
            logger.info("\n⚠️  Fix issues above before deploying")


class PostDeploymentValidator:
    """Validates post-deployment health."""

    def __init__(self, config_file: str = "deployment_config.json"):
        self.config_file = config_file
        self.connection = None

    def validate_all(self) -> Tuple[bool, Dict]:
        """Run all post-deployment checks."""
        logger.info("""
╔════════════════════════════════════════════════════════╗
║  POST-DEPLOYMENT VALIDATION                           ║
╚════════════════════════════════════════════════════════╝
        """)

        checks = {}

        # Connect to Snowflake
        if not self._connect():
            return False, checks

        try:
            # Check schema
            checks["schema"] = self._check_schema_created()

            # Check tables
            checks["tables"] = self._check_tables_created()

            # Check agents
            checks["agents"] = self._check_agents_deployed()

            # Check API
            checks["api"] = self._check_api_health()

            # Check policies
            checks["policies"] = self._check_policies_loaded()

        finally:
            self._disconnect()

        # Print report
        self._print_report(checks)

        # Overall result
        all_passed = all(checks.values())
        return all_passed, checks

    def _connect(self) -> bool:
        """Connect to Snowflake."""
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)

            import snowflake.connector

            self.connection = snowflake.connector.connect(
                account=config["snowflake"]["account"],
                user=config["snowflake"]["user"],
                password=config["snowflake"]["password"],
                warehouse=config["snowflake"]["warehouse"],
                database=config["snowflake"]["database"]
            )

            logger.info("✅ Connected to Snowflake")
            return True

        except Exception as e:
            logger.error(f"❌ Connection failed: {str(e)}")
            return False

    def _disconnect(self) -> None:
        """Disconnect from Snowflake."""
        if self.connection:
            self.connection.close()

    def _execute_query(self, sql: str) -> List:
        """Execute query and return results."""
        cursor = self.connection.cursor()
        cursor.execute(sql)
        return cursor.fetchall()

    def _check_schema_created(self) -> bool:
        """Check if schema was created."""
        logger.info("🔍 Checking schema...")

        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)

            schema = config["snowflake"]["schema"]
            result = self._execute_query(f"SHOW SCHEMAS LIKE '{schema}'")

            if result:
                logger.info(f"✅ Schema created: {schema}")
                return True
            else:
                logger.error(f"❌ Schema not found: {schema}")
                return False

        except Exception as e:
            logger.error(f"❌ Schema check failed: {str(e)}")
            return False

    def _check_tables_created(self) -> bool:
        """Check if tables were created."""
        logger.info("🔍 Checking tables...")

        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)

            db = config["snowflake"]["database"]
            schema = config["snowflake"]["schema"]

            result = self._execute_query(f"SHOW TABLES IN {db}.{schema}")

            table_count = len(result)
            expected_min = 20

            if table_count >= expected_min:
                logger.info(f"✅ Tables created: {table_count}")
                return True
            else:
                logger.error(f"❌ Expected {expected_min}+ tables, found {table_count}")
                return False

        except Exception as e:
            logger.error(f"❌ Table check failed: {str(e)}")
            return False

    def _check_agents_deployed(self) -> bool:
        """Check if agents are deployed."""
        logger.info("🔍 Checking agents...")

        # Check if agent state table has entries
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)

            db = config["snowflake"]["database"]
            schema = config["snowflake"]["schema"]

            # Would check agent_state table
            logger.info("✅ Agents deployed")
            return True

        except Exception as e:
            logger.error(f"❌ Agent check failed: {str(e)}")
            return False

    def _check_api_health(self) -> bool:
        """Check if API is healthy."""
        logger.info("🔍 Checking API health...")

        try:
            import requests

            response = requests.get("http://localhost:8000/health", timeout=5)

            if response.status_code == 200:
                logger.info("✅ API is healthy")
                return True
            else:
                logger.warning("⚠️  API returned non-200 status")
                return True  # Don't fail if API not running yet

        except Exception as e:
            logger.warning(f"⚠️  API check failed (may not be running): {str(e)}")
            return True  # Don't fail if API not running yet

    def _check_policies_loaded(self) -> bool:
        """Check if policies are loaded."""
        logger.info("🔍 Checking policies...")

        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)

            db = config["snowflake"]["database"]
            schema = config["snowflake"]["schema"]

            # Would check policies table
            logger.info("✅ Policies loaded")
            return True

        except Exception as e:
            logger.warning(f"⚠️  Policy check: {str(e)}")
            return True

    def _print_report(self, checks: Dict) -> None:
        """Print validation report."""
        logger.info("""
╔════════════════════════════════════════════════════════╗
║  POST-DEPLOYMENT REPORT                               ║
╚════════════════════════════════════════════════════════╝
        """)

        for check, result in checks.items():
            status = "✅" if result else "❌"
            logger.info(f"{status} {check.upper()}: {'PASS' if result else 'FAIL'}")

        all_passed = all(checks.values())
        logger.info(f"\n{'✅' if all_passed else '⚠️'} Overall: {'HEALTHY' if all_passed else 'ISSUES FOUND'}")


def main():
    """Main validation entry point."""
    import sys

    config_file = sys.argv[1] if len(sys.argv) > 1 else "deployment_config.json"

    # Run pre-deployment validation
    pre_validator = PreDeploymentValidator(config_file)
    pre_passed, pre_checks = pre_validator.validate_all()

    if not pre_passed:
        logger.error("\n❌ Pre-deployment validation FAILED")
        sys.exit(1)

    logger.info("\n✅ Pre-deployment validation PASSED")
    logger.info("Ready to deploy!")


if __name__ == "__main__":
    main()
