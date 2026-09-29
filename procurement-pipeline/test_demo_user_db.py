import importlib.util
import json
import sqlite3
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "procurement-pipeline" / "build_demo_user_db.py"
OUTPUT = ROOT / "demo-ui" / "auth-demo"


class DemoUserDbTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run([sys.executable, str(SCRIPT)], check=True, cwd=ROOT)
        spec = importlib.util.spec_from_file_location("demo_user_db", SCRIPT)
        cls.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.module)
        cls.payload = json.loads((OUTPUT / "users.demo.json").read_text(encoding="utf-8"))

    def test_exact_account_distribution(self):
        users = self.payload["users"]
        self.assertEqual(len(users), 25)
        for company_id in ["C01", "C02", "C03", "C04", "C05"]:
            company_users = [u for u in users if u["company_id"] == company_id]
            self.assertEqual(len(company_users), 5)
            self.assertEqual(sum(u["account_status"] == "inactive" for u in company_users), 1)

    def test_password_is_hashed_and_verifiable(self):
        serialized = (OUTPUT / "users.demo.json").read_text(encoding="utf-8")
        self.assertNotIn(self.module.DEMO_PASSWORD, serialized)
        for user in self.payload["users"]:
            self.assertTrue(
                self.module.verify_password(
                    self.module.DEMO_PASSWORD, user["password_salt"], user["password_hash"]
                )
            )
            self.assertFalse(
                self.module.verify_password("wrong-password", user["password_salt"], user["password_hash"])
            )

    def test_role_and_tenant_boundaries(self):
        roles = {item["role"]: item for item in self.payload["roles"]}
        self.assertEqual(roles["viewer"]["allowed_security_levels"], ["L1"])
        self.assertEqual(roles["bid_analyst"]["allowed_security_levels"], ["L1", "L2"])
        self.assertEqual(roles["cost_analyst"]["allowed_security_levels"], ["L1", "L2", "L3"])
        self.assertTrue(all(item["own_tenant_only"] for item in roles.values()))
        company_tenants = {c["company_id"]: c["tenant_id"] for c in self.payload["companies"]}
        for user in self.payload["users"]:
            self.assertEqual(user["tenant_id"], company_tenants[user["company_id"]])

    def test_sqlite_integrity(self):
        connection = sqlite3.connect(OUTPUT / "users.demo.sqlite3")
        self.assertEqual(connection.execute("PRAGMA integrity_check").fetchone()[0], "ok")
        self.assertEqual(connection.execute("SELECT COUNT(*) FROM users").fetchone()[0], 25)
        self.assertEqual(connection.execute("SELECT COUNT(*) FROM users WHERE account_status='inactive'").fetchone()[0], 5)
        self.assertEqual(connection.execute("SELECT COUNT(*) FROM roles").fetchone()[0], 4)
        connection.close()


if __name__ == "__main__":
    unittest.main()
