from .main import main

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        # Manual headed runs may be intentionally interrupted by user/browser close.
        raise SystemExit(0)
