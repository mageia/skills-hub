import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[1]


class SkillStructureTests(unittest.TestCase):
    def test_required_files_exist(self):
        for rel in [
            'SKILL.md',
            'agents/openai.yaml',
            'references/workflow.md',
            'references/dependencies.md',
            'references/output-format.md',
            'scripts/validate_skill.py',
            'scripts/bootstrap.sh',
            'scripts/check_env.py',
            'scripts/run_youtube_transcript.py',
        ]:
            self.assertTrue((SKILL_DIR / rel).exists(), rel)


if __name__ == '__main__':
    unittest.main()
