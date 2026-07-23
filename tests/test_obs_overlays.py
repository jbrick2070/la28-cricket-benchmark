import unittest
import json
try:
    from la28_cricket import obs_overlays
    HAS_OBS = True
except ImportError:
    HAS_OBS = False

class TestOBSOverlays(unittest.TestCase):
    @unittest.skipUnless(HAS_OBS, "obs_overlays module not available yet")
    def test_obs_overlays_import(self):
        self.assertIsNotNone(obs_overlays)
        
    @unittest.skipUnless(HAS_OBS, "obs_overlays module not available yet")
    def test_routes_exist(self):
        # Depending on implementation, we can test flask routes or just that functions exist
        app = getattr(obs_overlays, "app", None)
        if app:
            with app.test_client() as client:
                res_health = client.get("/api/health")
                self.assertEqual(res_health.status_code, 200)
                try:
                    data = res_health.get_json()
                except Exception:
                    data = json.loads(res_health.data.decode("utf-8"))
                self.assertEqual(data.get("status"), "ok")
                
                res_data = client.get("/api/data")
                self.assertEqual(res_data.status_code, 200)
                
                # Test HTML routes if they exist
                for route in ["/", "/scoreboard", "/predictions"]:
                    res = client.get(route)
                    if res.status_code == 200:
                        self.assertIn(b"html", res.data.lower())
                
if __name__ == "__main__":
    unittest.main()
