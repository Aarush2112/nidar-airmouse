import importlib.util
import math
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]

def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "script" / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

class MissionTests(unittest.TestCase):
    def test_routes(self):
        for name, count in [("nidar_square_mission", 5), ("nidar_lawnmower_mission", 12)]:
            with self.subTest(name=name):
                points = load(name).waypoints(0.5)
                self.assertEqual(len(points), count)
                self.assertEqual(points[0][1:], (0.0, 0.0, 0.5))
                self.assertEqual(points[-1][1:], points[0][1:])
                self.assertTrue(all(0 <= x <= 1 and 0 <= y <= 1 and z == 0.5 for _, x, y, z in points))
        points = load("nidar_lawnmower_mission").waypoints(0.5)
        self.assertEqual(sorted({p[2] for p in points}), [0, 0.25, 0.5, 0.75, 1])

    def test_cli(self):
        for name in ["nidar_square_mission", "nidar_lawnmower_mission"]:
            for value in ["0.5", "0", "-1", "nan", "inf"]:
                with self.subTest(name=name, value=value):
                    result = subprocess.run([sys.executable, str(ROOT / "script" / (name + ".py")), value], capture_output=True, text=True)
                    self.assertEqual(result.returncode, 0 if value == "0.5" else 2)

if __name__ == "__main__":
    unittest.main()
