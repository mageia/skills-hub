#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import parse_qs, urlparse

DEFAULT_WHISPER_MODEL = 'small'
TIMESTAMP_MARKER = '-->'
SUPPORTED_SUBTITLE_EXTENSIONS = ('.srt', '.vtt', '.ttml', '.srv1', '.srv2', '.srv3', '.json3')


@dataclass(frozen=True)
class SubtitleCandidate:
    language: str
    kind: str


@dataclass(frozen=True)
class OutputPaths:
    output_dir: Path
    transcript_txt: Path
    transcript_srt: Path
    metadata_json: Path
    process_log: Path
    audio_source: Path
    normalized_audio: Path


class WorkflowError(RuntimeError):
    pass


class Logger:
    def __init__(self, path: Path):
        self.path = path

    def log(self, message: str) -> None:
        timestamp = datetime.now(UTC).isoformat()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open('a', encoding='utf-8') as handle:
            handle.write(f'[{timestamp}] {message}\n')


def script_dir() -> Path:
    return Path(__file__).resolve().parent


def skill_dir() -> Path:
    return script_dir().parents[0]


def default_output_root() -> Path:
    return skill_dir() / 'outputs'


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('url', help='YouTube video URL')
    parser.add_argument('--output-root', default=str(default_output_root()), help='Output root directory')
    parser.add_argument('--force', action='store_true', help='Overwrite existing output directory')
    return parser.parse_args()


def extract_video_id(url: str) -> str:
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    if host.endswith('youtu.be'):
        video_id = parsed.path.strip('/').split('/')[0]
    elif 'youtube.com' in host:
        if parsed.path == '/watch':
            video_id = parse_qs(parsed.query).get('v', [''])[0]
        else:
            parts = [part for part in parsed.path.split('/') if part]
            video_id = parts[1] if len(parts) >= 2 and parts[0] in {'shorts', 'embed', 'live'} else ''
    else:
        raise ValueError('URL is not a YouTube URL')

    if not video_id:
        raise ValueError('Unable to determine YouTube video id')
    return video_id


def first_available_language(items: dict[str, list[dict[str, Any]]]) -> str | None:
    for language, tracks in items.items():
        if language == 'live_chat':
            continue
        if tracks:
            return language
    return None


def select_subtitle_candidate(info: dict[str, Any]) -> SubtitleCandidate | None:
    manual = first_available_language(info.get('subtitles') or {})
    if manual:
        return SubtitleCandidate(language=manual, kind='manual')
    auto = first_available_language(info.get('automatic_captions') or {})
    if auto:
        return SubtitleCandidate(language=auto, kind='auto')
    return None


def srt_to_text(content: str) -> str:
    lines: list[str] = []
    for block in content.strip().split('\n\n'):
        text_lines = []
        for raw_line in block.splitlines():
            line = raw_line.strip()
            if not line or line.isdigit() or TIMESTAMP_MARKER in line:
                continue
            text_lines.append(line)
        if text_lines:
            lines.append(' '.join(text_lines))
    return '\n'.join(lines)


def prepare_output_dir(output_root: Path, video_id: str, force: bool) -> Path:
    output_root.mkdir(parents=True, exist_ok=True)
    output_dir = output_root / video_id
    if output_dir.exists():
        has_content = any(output_dir.iterdir())
        if has_content and not force:
            raise FileExistsError(f'Output directory already exists: {output_dir}')
        if force:
            shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def build_output_paths(output_dir: Path) -> OutputPaths:
    return OutputPaths(
        output_dir=output_dir,
        transcript_txt=output_dir / 'transcript.txt',
        transcript_srt=output_dir / 'transcript.srt',
        metadata_json=output_dir / 'metadata.json',
        process_log=output_dir / 'process.log',
        audio_source=output_dir / 'source.wav',
        normalized_audio=output_dir / 'normalized.wav',
    )


def run_command(command: list[str], logger: Logger, *, capture_output: bool = False) -> subprocess.CompletedProcess[str]:
    logger.log(f'Running command: {" ".join(command)}')
    completed = subprocess.run(command, text=True, capture_output=capture_output, check=False)
    if completed.stdout:
        logger.log(completed.stdout.strip())
    if completed.stderr:
        logger.log(completed.stderr.strip())
    if completed.returncode != 0:
        raise WorkflowError(f'Command failed with exit code {completed.returncode}: {" ".join(command)}')
    return completed


def fetch_video_metadata(url: str, logger: Logger) -> dict[str, Any]:
    command = ['yt-dlp', '--dump-single-json', '--skip-download', '--no-warnings', '--no-playlist', url]
    completed = run_command(command, logger, capture_output=True)
    return json.loads(completed.stdout)


def detect_runtime() -> dict[str, Any]:
    check_env_path = script_dir() / 'check_env.py'
    spec = importlib.util.spec_from_file_location('youtube_transcript_local_check_env_runtime', check_env_path)
    if spec is None or spec.loader is None:
        raise WorkflowError(f'Unable to load runtime detector: {check_env_path}')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.detect_runtime()


def find_downloaded_subtitle_file(output_dir: Path, video_id: str) -> Path:
    candidates: list[Path] = []
    for extension in SUPPORTED_SUBTITLE_EXTENSIONS:
        candidates.extend(sorted(output_dir.glob(f'{video_id}*{extension}')))
    if not candidates:
        raise WorkflowError('Subtitle download completed but no subtitle file was found')
    return candidates[0]


def copy_or_convert_subtitle(source: Path, destination: Path, logger: Logger) -> None:
    if source.suffix.lower() == '.srt':
        shutil.copyfile(source, destination)
        return
    command = ['ffmpeg', '-y', '-i', str(source), str(destination)]
    run_command(command, logger)


def download_subtitle_outputs(url: str, candidate: SubtitleCandidate, paths: OutputPaths, logger: Logger) -> None:
    flag = '--write-subs' if candidate.kind == 'manual' else '--write-auto-subs'
    base = paths.output_dir / extract_video_id(url)
    command = [
        'yt-dlp',
        '--skip-download',
        '--no-playlist',
        flag,
        '--sub-langs', candidate.language,
        '--convert-subs', 'srt',
        '-o', str(base),
        url,
    ]
    run_command(command, logger)
    subtitle_file = find_downloaded_subtitle_file(paths.output_dir, extract_video_id(url))
    copy_or_convert_subtitle(subtitle_file, paths.transcript_srt, logger)
    paths.transcript_txt.write_text(srt_to_text(paths.transcript_srt.read_text(encoding='utf-8')), encoding='utf-8')


def download_audio_source(url: str, destination: Path, logger: Logger) -> Path:
    command = [
        'yt-dlp',
        '-x',
        '--audio-format', 'wav',
        '--no-playlist',
        '-o', str(destination),
        url,
    ]
    run_command(command, logger)
    if not destination.exists():
        raise WorkflowError(f'Expected audio file was not created: {destination}')
    return destination


def normalize_audio_for_asr(source: Path, destination: Path, logger: Logger) -> Path:
    command = [
        'ffmpeg',
        '-y',
        '-i', str(source),
        '-ac', '1',
        '-ar', '16000',
        '-c:a', 'pcm_s16le',
        str(destination),
    ]
    run_command(command, logger)
    if not destination.exists():
        raise WorkflowError(f'Expected normalized audio file was not created: {destination}')
    return destination


def format_srt_timestamp(seconds: float) -> str:
    total_millis = int(round(seconds * 1000))
    hours, remainder = divmod(total_millis, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1000)
    return f'{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}'


def write_srt_from_segments(segments: Iterable[Any], destination: Path) -> str:
    text_lines: list[str] = []
    blocks: list[str] = []
    for index, segment in enumerate(segments, start=1):
        text = str(segment.text).strip()
        if not text:
            continue
        text_lines.append(text)
        blocks.append(
            '\n'.join([
                str(index),
                f'{format_srt_timestamp(float(segment.start))} --> {format_srt_timestamp(float(segment.end))}',
                text,
            ])
        )
    destination.write_text('\n\n'.join(blocks) + ('\n' if blocks else ''), encoding='utf-8')
    return '\n'.join(text_lines)


def transcribe_audio(audio_path: Path, paths: OutputPaths, runtime: dict[str, Any], logger: Logger) -> dict[str, Any]:
    logger.log(f'Transcribing audio with device={runtime["device"]} compute_type={runtime["compute_type"]}')
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise WorkflowError('faster-whisper is required for local ASR') from exc

    model = WhisperModel(DEFAULT_WHISPER_MODEL, device=str(runtime['device']), compute_type=str(runtime['compute_type']))
    segments_iter, info = model.transcribe(str(audio_path), vad_filter=True)
    segments = list(segments_iter)
    transcript_text = write_srt_from_segments(segments, paths.transcript_srt)
    paths.transcript_txt.write_text(transcript_text, encoding='utf-8')
    return {
        'language': getattr(info, 'language', None),
        'model': DEFAULT_WHISPER_MODEL,
    }




def run_asr_flow(url: str, paths: OutputPaths, logger: Logger) -> tuple[dict[str, Any], dict[str, Any]]:
    runtime = detect_runtime()
    audio_source = download_audio_source(url, paths.audio_source, logger)
    normalized_audio = normalize_audio_for_asr(audio_source, paths.normalized_audio, logger)
    transcription = transcribe_audio(normalized_audio, paths, runtime, logger)
    metadata_patch = {
        'source_method': 'asr',
        'subtitle_type': None,
        'language': transcription.get('language'),
        'model': transcription.get('model'),
        'device': runtime.get('device'),
    }
    return runtime, metadata_patch

def write_metadata(destination: Path, metadata: dict[str, Any]) -> None:
    destination.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def run_workflow(url: str, output_root: Path, force: bool = False) -> dict[str, Any]:
    video_id = extract_video_id(url)
    output_dir = prepare_output_dir(output_root, video_id, force=force)
    paths = build_output_paths(output_dir)
    logger = Logger(paths.process_log)
    logger.log(f'Starting workflow for {url}')
    info = fetch_video_metadata(url, logger)
    candidate = select_subtitle_candidate(info)

    metadata: dict[str, Any] = {
        'video_url': url,
        'video_id': video_id,
        'source_method': None,
        'subtitle_type': None,
        'language': None,
        'model': None,
        'device': None,
        'status': 'success',
        'title': info.get('title'),
    }

    if candidate is not None:
        logger.log(f'Using existing subtitle candidate language={candidate.language} kind={candidate.kind}')
        try:
            download_subtitle_outputs(url, candidate, paths, logger)
            metadata.update({
                'source_method': 'subtitle',
                'subtitle_type': candidate.kind,
                'language': candidate.language,
            })
        except WorkflowError as exc:
            logger.log(f'Subtitle extraction failed: {exc}; falling back to local ASR')
            _runtime, asr_metadata = run_asr_flow(url, paths, logger)
            metadata.update(asr_metadata)
    else:
        logger.log('No existing subtitles found; falling back to local ASR')
        _runtime, asr_metadata = run_asr_flow(url, paths, logger)
        metadata.update(asr_metadata)

    write_metadata(paths.metadata_json, metadata)
    logger.log(f'Completed workflow with source_method={metadata["source_method"]}')
    return metadata


def main() -> None:
    args = parse_args()
    output_root = Path(args.output_root).expanduser().resolve()
    try:
        metadata = run_workflow(args.url, output_root, force=args.force)
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc
    print(json.dumps(metadata, ensure_ascii=False))


if __name__ == '__main__':
    main()
