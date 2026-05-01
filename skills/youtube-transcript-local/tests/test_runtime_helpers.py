import importlib.util
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SKILL_DIR = Path(__file__).resolve().parents[1]
RUN_PATH = SKILL_DIR / 'scripts' / 'run_youtube_transcript.py'


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise FileNotFoundError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class RuntimeHelperTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_module(RUN_PATH, 'youtube_transcript_run_mod')

    def test_extract_video_id_from_watch_url(self):
        self.assertEqual(self.mod.extract_video_id('https://www.youtube.com/watch?v=abc123XYZ89'), 'abc123XYZ89')

    def test_extract_video_id_from_short_url(self):
        self.assertEqual(self.mod.extract_video_id('https://youtu.be/abc123XYZ89'), 'abc123XYZ89')

    def test_extract_video_id_rejects_non_youtube(self):
        with self.assertRaises(ValueError):
            self.mod.extract_video_id('https://example.com/watch?v=abc123XYZ89')

    def test_select_subtitle_candidate_prefers_manual_when_present(self):
        info = {'subtitles': {'en': [{'ext': 'vtt'}]}, 'automatic_captions': {}}
        candidate = self.mod.select_subtitle_candidate(info)
        self.assertEqual(candidate.language, 'en')
        self.assertEqual(candidate.kind, 'manual')

    def test_select_subtitle_candidate_falls_back_to_auto(self):
        info = {'subtitles': {}, 'automatic_captions': {'de': [{'ext': 'vtt'}]}}
        candidate = self.mod.select_subtitle_candidate(info)
        self.assertEqual(candidate.language, 'de')
        self.assertEqual(candidate.kind, 'auto')

    def test_srt_to_text_strips_indices_and_timestamps(self):
        text = self.mod.srt_to_text('1\n00:00:00,000 --> 00:00:01,000\nHello world\n\n2\n00:00:01,000 --> 00:00:02,000\nSecond line\n')
        self.assertEqual(text, 'Hello world\nSecond line')

    def test_prepare_output_dir_requires_force_to_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_root = Path(tmp)
            video_dir = output_root / 'abc123XYZ89'
            video_dir.mkdir()
            (video_dir / 'transcript.txt').write_text('exists', encoding='utf-8')
            with self.assertRaises(FileExistsError):
                self.mod.prepare_output_dir(output_root, 'abc123XYZ89', force=False)

    def test_run_workflow_uses_subtitle_branch_when_available(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_root = Path(tmp)

            def fake_download_subtitles(url, candidate, paths, logger):
                paths.transcript_srt.write_text('1\n00:00:00,000 --> 00:00:01,000\nHello\n', encoding='utf-8')
                paths.transcript_txt.write_text('Hello', encoding='utf-8')

            with mock.patch.object(self.mod, 'fetch_video_metadata', return_value={'subtitles': {'en': [{'ext': 'vtt'}]}, 'automatic_captions': {}, 'title': 'Demo'}), \
                 mock.patch.object(self.mod, 'download_subtitle_outputs', side_effect=fake_download_subtitles), \
                 mock.patch.object(self.mod, 'download_audio_source') as audio_mock, \
                 mock.patch.object(self.mod, 'normalize_audio_for_asr') as normalize_mock, \
                 mock.patch.object(self.mod, 'transcribe_audio') as asr_mock:
                result = self.mod.run_workflow('https://www.youtube.com/watch?v=abc123XYZ89', output_root, force=False)

            metadata = json.loads((output_root / 'abc123XYZ89' / 'metadata.json').read_text(encoding='utf-8'))
            self.assertEqual(result['source_method'], 'subtitle')
            self.assertEqual(metadata['source_method'], 'subtitle')
            audio_mock.assert_not_called()
            normalize_mock.assert_not_called()
            asr_mock.assert_not_called()

    def test_run_workflow_falls_back_to_asr_when_subtitle_download_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_root = Path(tmp)

            def fake_download_audio(url, destination, logger):
                destination.write_text('audio', encoding='utf-8')
                return destination

            def fake_normalize_audio(source, destination, logger):
                destination.write_text('normalized', encoding='utf-8')
                return destination

            def fake_transcribe(audio_path, paths, runtime, logger):
                paths.transcript_srt.write_text('1\n00:00:00,000 --> 00:00:01,000\nRecovered\n', encoding='utf-8')
                paths.transcript_txt.write_text('Recovered', encoding='utf-8')
                return {'language': 'en', 'model': 'small'}

            with mock.patch.object(self.mod, 'fetch_video_metadata', return_value={'subtitles': {'en': [{'ext': 'vtt'}]}, 'automatic_captions': {}, 'title': 'Demo'}), \
                 mock.patch.object(self.mod, 'download_subtitle_outputs', side_effect=self.mod.WorkflowError('subtitle failed')), \
                 mock.patch.object(self.mod, 'detect_runtime', return_value={'device': 'cpu', 'compute_type': 'int8', 'gpu_detected': False}), \
                 mock.patch.object(self.mod, 'download_audio_source', side_effect=fake_download_audio), \
                 mock.patch.object(self.mod, 'normalize_audio_for_asr', side_effect=fake_normalize_audio), \
                 mock.patch.object(self.mod, 'transcribe_audio', side_effect=fake_transcribe):
                result = self.mod.run_workflow('https://www.youtube.com/watch?v=abc123XYZ89', output_root, force=False)

            metadata = json.loads((output_root / 'abc123XYZ89' / 'metadata.json').read_text(encoding='utf-8'))
            self.assertEqual(result['source_method'], 'asr')
            self.assertEqual(metadata['source_method'], 'asr')

    def test_run_workflow_falls_back_to_asr_when_subtitles_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_root = Path(tmp)

            def fake_download_audio(url, destination, logger):
                destination.write_text('audio', encoding='utf-8')
                return destination

            def fake_normalize_audio(source, destination, logger):
                destination.write_text('normalized', encoding='utf-8')
                return destination

            def fake_transcribe(audio_path, paths, runtime, logger):
                paths.transcript_srt.write_text('1\n00:00:00,000 --> 00:00:01,000\nHi\n', encoding='utf-8')
                paths.transcript_txt.write_text('Hi', encoding='utf-8')
                return {'language': 'en', 'model': 'small'}

            with mock.patch.object(self.mod, 'fetch_video_metadata', return_value={'subtitles': {}, 'automatic_captions': {}, 'title': 'Demo'}), \
                 mock.patch.object(self.mod, 'detect_runtime', return_value={'device': 'cpu', 'compute_type': 'int8', 'gpu_detected': False}), \
                 mock.patch.object(self.mod, 'download_audio_source', side_effect=fake_download_audio), \
                 mock.patch.object(self.mod, 'normalize_audio_for_asr', side_effect=fake_normalize_audio), \
                 mock.patch.object(self.mod, 'transcribe_audio', side_effect=fake_transcribe):
                result = self.mod.run_workflow('https://www.youtube.com/watch?v=abc123XYZ89', output_root, force=False)

            metadata = json.loads((output_root / 'abc123XYZ89' / 'metadata.json').read_text(encoding='utf-8'))
            self.assertEqual(result['source_method'], 'asr')
            self.assertEqual(metadata['source_method'], 'asr')
            self.assertEqual(metadata['device'], 'cpu')


if __name__ == '__main__':
    unittest.main()
