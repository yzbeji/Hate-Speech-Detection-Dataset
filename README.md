# Hate Speech Detection Dataset

Comentarii în limba română de pe Instagram, pentru detecția discursului instigator la ură.
Propunerea setului: [docs/data-proposal.md](docs/data-proposal.md).

## Structură

| Cale | Ce conține |
|---|---|
| `data/comments.jsonl` | setul anonimizat, un comentariu pe rând |
| `data/sample/sample.jsonl` | eșantion etichetat |
| `data/raw/` | date brute de la scraper; conțin date personale, **nu se urcă pe GitHub** |
| `src/comment_extractor/` | scraper Instagram și TikTok (Playwright) |
| `scripts/build_dataset.py` | transformă datele brute în setul anonimizat |

## Instalare

```bash
python -m venv .venv
.venv\Scripts\activate          # Linux/macOS: source .venv/bin/activate
pip install -e ".[dev]"
playwright install chromium
```

## 1. Colectare

```bash
comment-extractor --url "https://www.instagram.com/p/<cod>/" --headed --manual-wait-seconds 60
comment-extractor --url "https://www.tiktok.com/@user/video/123" --headed --manual-wait-seconds 20
```

Platforma se alege după link. Rezultatul ajunge în `data/raw/instagram_comments.jsonl`, respectiv
`data/raw/tiktok_comments.jsonl`. Rulările pe mai multe postări se adaugă în același fișier, fără duplicate.

Cu `--headed` browserul e vizibil, ca să puteți face login sau rezolva un captcha în timpul `--manual-wait-seconds`.
Login-ul se păstrează în `.browser-profile/` (ignorat de git), deci e nevoie de el o singură dată.
Fără login, sau fără `--headed`, Instagram arată doar primele ~10–15 comentarii ale unei postări.
Toate opțiunile: `comment-extractor --help`.

## 2. Construirea setului anonimizat

```bash
$env:DATASET_SALT = "<un-secret-al-echipei>"   # cmd: set DATASET_SALT=...  Linux/macOS: export DATASET_SALT=...
python scripts/build_dataset.py
```

Citește toate fișierele `data/raw/*.jsonl` și scrie `data/comments.jsonl`:
- utilizatorul, postarea și id-urile comentariilor devin hash-uri SHA-256 cu sare;
- în text, @mențiunile devin `@USER`, iar linkurile devin `URL`;
- numele afișat al autorului se elimină.

Cu aceeași `DATASET_SALT`, id-urile rămân la fel între rulări. Fără ea, se folosește o sare aleatoare.
Sarea nu se pune în repo.

## Format

```json
{"id": "ig_f86bb5029638", "platform": "instagram", "text": "Yesssss 🔥", "post_hash": "a180d269267a", "author_hash": "6a8df99d36f9", "parent_id": null, "is_reply": false, "created_at": "2026-03-13T18:13:08Z", "like_count": 15, "reply_count": 0, "contains_mention": false, "contains_link": false}
```

## Teste

```bash
pytest
```
