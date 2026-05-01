import importlib.util
import sys
import unittest
from pathlib import Path
from unittest import mock

SKILL_DIR = Path(__file__).resolve().parents[1]
CHECK_ENV_PATH = SKILL_DIR / 'scripts' / 'check_env.py'


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise FileNotFoundError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class CheckEnvTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_module(CHECK_ENV_PATH, 'youtube_transcript_check_env')

    def test_detect_device_defaults_to_cpu(self):
        with mock.patch.object(self.mod, 'which', return_value=None):
            runtime = self.mod.detect_runtime()
        self.assertEqual(runtime['device'], 'cpu')
        self.assertEqual(runtime['compute_type'], 'int8')

    def test_detect_device_uses_cuda_when_nvidia_smi_exists(self):
        with mock.patch.object(self.mod, 'which', side_effect=lambda name: '/usr/bin/nvidia-smi' if name == 'nvidia-smi' else None):
            runtime = self.mod.detect_runtime()
        self.assertEqual(runtime['device'], 'cuda')
        self.assertEqual(runtime['compute_type'], 'float16')


if __name__ == '__main__':
    unittest.main()
