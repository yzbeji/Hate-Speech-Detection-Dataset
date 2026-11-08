from __future__ import annotations

import argparse
import logging
from pathlib import Path

from comment_extractor.exporters import JsonlExporter
from comment_extractor.extractors import extractor_for
from comment_extractor.utils.checkpoint import write_checkpoint
from comment_extractor.utils.retry import run_with_retry


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract Instagram or TikTok post comments into JSONL")
    parser.add_argument("--url", required=True, help="Instagram post/reel URL or TikTok video URL")
    parser.add_argument("--output", help="Output JSONL file path (default: data/raw/<platform>_comments.jsonl)")
    parser.add_argument("--max-comments", type=int, default=2000, help="Maximum comments to collect")
    parser.add_argument(
        "--checkpoint",
        default="data/raw/extract.checkpoint.json",
        help="Checkpoint JSON file",
    )
    parser.add_argument(
        "--profile-dir",
        default=".browser-profile",
        help="Browser profile folder; keeps the login between runs (never commit it)",
    )
    parser.add_argument("--headed", action="store_true", help="Run browser in headed mode")
    parser.add_argument(
        "--manual-wait-seconds",
        type=int,
        default=0,
        help="In headed mode, wait this long for manual captcha/login resolution",
    )
    parser.add_argument("--retries", type=int, default=2, help="Retry attempts on extractor failure")
    parser.add_argument("--base-delay", type=float, default=2.0, help="Base retry delay in seconds")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    args = parser.parse_args()

    try:
        args.extractor_cls = extractor_for(args.url)
    except ValueError as exc:
        parser.error(str(exc))
    return args


def main() -> int:
    args = parse_args()
    logging.basicConfig(level=getattr(logging, args.log_level), format="%(levelname)s: %(message)s")

    source_url = args.url
    output_path = Path(args.output or f"data/raw/{args.extractor_cls.platform}_comments.jsonl")
    checkpoint_path = Path(args.checkpoint)

    extractor = args.extractor_cls(
        profile_dir=args.profile_dir,
        headless=not args.headed,
        manual_wait_seconds=args.manual_wait_seconds,
    )

    def _extract():
        return extractor.extract(source_url=source_url, max_comments=args.max_comments)

    effective_retries = args.retries
    if args.headed and args.manual_wait_seconds > 0:
        # Avoid repeating long manual captcha windows on automatic retries.
        effective_retries = 0

    if effective_retries != args.retries:
        logging.info("Adjusted retries from %s to %s for headed/manual run", args.retries, effective_retries)

    try:
        records = run_with_retry(_extract, retries=effective_retries, base_delay=args.base_delay)
    except BaseException as exc:
        # A headed run is often ended on purpose by closing the browser or pressing Ctrl+C.
        if not args.headed:
            raise
        logging.info("Manual run stopped; treating as normal stop. (%r)", exc)
        records = []

    exporter = JsonlExporter(output_path)
    written = exporter.write(records)

    write_checkpoint(
        checkpoint_path,
        source_url=source_url,
        output_path=str(output_path),
        total_written=len(exporter.seen_comment_ids),
    )

    logging.info("Fetched records: %s", len(records))
    logging.info("Written records: %s", written)
    logging.info("Unique IDs in output: %s", len(exporter.seen_comment_ids))
    logging.info("Dataset path: %s", output_path.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
