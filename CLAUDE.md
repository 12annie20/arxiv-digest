# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project info

- **Repo**: https://github.com/12annie20/arxiv-digest
- **GitHub Pages**: https://12annie20.github.io/arxiv-digest/
- **Local output**: `C:\Users\anlic\ArxivDigest`
- **API keys**: `GEMINI_API_KEY` (primary), `GEMINI_API_KEY_2` (fallback)
- **Core files**: `daily_digest_gemini.py`, `digest_template.html`

## Working principles

- Execute directly without asking for confirmation
- Fix errors autonomously without explaining each step
- Report only the result when done, not the process
- Use the fewest steps possible
- After any code change, `git push`

## What this project does

Daily arXiv digest focused on **AI × Psychology** cross-disciplinary research. The script fetches papers from arXiv RSS feeds, sends them to Gemini for analysis, and renders a styled HTML report that is published to GitHub Pages at `https://12annie20.github.io/arxiv-digest/`.

## Running the digest

```bash
python daily_digest_gemini.py
```

Requires env vars `GEMINI_API_KEY` (and optionally `GEMINI_API_KEY_2` as fallback). On Windows, the script sets UTF-8 stdout/stderr at startup to avoid cp950 encoding errors.

The script auto-opens the browser and attempts `git add / commit / push` at the end. On GitHub Actions the push is handled by the workflow instead.

## Architecture

Everything lives in two files:

**`daily_digest_gemini.py`** — single-file pipeline with these stages:
1. `gather_papers()` — fetches `cs.AI`, `cs.HC`, `cs.CL`, `cs.CY` RSS feeds, deduplicates by `arxiv_id`, returns up to 40 papers
2. `main()` dedup filter — loads `shown_papers.json`, removes already-shown arxiv_ids; falls back to including old papers if fewer than 10 fresh ones remain; caps at 30 papers sent to Gemini
3. `call_gemini()` — sends papers in one prompt to `gemini-2.5-flash`; parses JSON response; retries on 503 (up to 5×, with backoff); raises `QuotaExceededError` on 429 so `main()` can switch keys
4. Render functions (`render_therm`, `render_picks`, `render_papers`, `render_llm`, `render_prompt`) — each takes the relevant slice of the parsed JSON and returns an HTML string
5. `build_html()` — reads `digest_template.html` and replaces `{{PLACEHOLDER}}` tokens with rendered HTML
6. `save_html()` — writes both `digest_YYYY-MM-DD.html` and `index.html` (GitHub Pages entry point)
7. `save_shown()` — appends used arxiv_ids (from picks + papers + llm_papers + prompt_papers) to `shown_papers.json`, capped at 500 entries

**`digest_template.html`** — static HTML/CSS shell with `{{DATE}}`, `{{DATETIME}}`, `{{THERMOMETER}}`, `{{PICKS}}`, `{{PAPERS}}`, `{{LLM_PAPERS}}`, `{{PROMPT_PAPERS}}`, `{{SUMMARY}}`, `{{TOMORROW}}` placeholders. Contains all CSS (Cormorant Garamond + DM Mono fonts, Mocha-palette color tokens in `:root`).

### Tab structure

| Tab ID | Nav label | Placeholder | Content |
|---|---|---|---|
| `tab-home` | ☀ 今日推薦 | `{{THERMOMETER}}` `{{PICKS}}` `{{SUMMARY}}` `{{TOMORROW}}` | Field thermometer + 3 picks + insight |
| `tab-papers` | 📚 TOP 5 深度解析 | `{{PAPERS}}` | 5 deep-review cards |
| `tab-llm` | 🤖 LLM × 心理學 | `{{LLM_PAPERS}}` | 3 LLM × psychology cards |
| `tab-prompt` | 🔬 Prompt × 心理學 | `{{PROMPT_PAPERS}}` | 3 prompt engineering × psychology cards |
| `tab-favs` | ★ 收藏夾 | — | Client-side localStorage favourites |

### Gemini JSON schema

The prompt requests a single JSON object with keys: `thermometer`, `picks` (3), `papers` (5), `llm_papers` (3), `prompt_papers` (3), `summary`, `tomorrow`. All `arxiv_id` values must come from the fetched paper list — Gemini must not invent IDs.

Abstract depth requirements (set in the prompt):
- `papers[].abstract`: 6–8 sentences covering motivation, problem, method, experiment, findings, implications
- `papers[].contributions`: 3 items (previously 2)
- `llm_papers[].implication`: 4–5 sentences including ethics/social implications
- `prompt_papers[].application`: 4–5 sentences covering current use, future potential, and psychology practice relevance

Selection criteria (`選文標準` block in `call_gemini()`): prioritises AI × psychology cross-disciplinary work across HCI, affective computing, cognitive science, social/educational/clinical psychology, neuroscience, behavioural science. Does **not** filter by submission date.

### Color tokens (CSS `:root`)

`--m-sage` (cs.AI green), `--m-clay` (cs.CL/accent orange), `--m-slate` (cs.HC blue-grey), `--m-mauve` (cs.CY purple, LLM cards), `--m-teal` (Prompt cards). Each has `-light` and `-pale` variants.

## GitHub Actions

`.github/workflows/daily.yml` runs at **23:00 UTC** (07:00 CST) daily, retries the script up to 5 times on failure, then commits and pushes all changed files. Secrets required: `GEMINI_API_KEY`, `GEMINI_API_KEY_2`.

## Local vs CI behaviour

`IS_GITHUB = os.environ.get("GITHUB_ACTIONS") == "true"` controls:
- `OUTPUT_FOLDER`: `"."` on CI, `C:\Users\anlic\ArxivDigest` locally
- Notifications (Windows balloon tip): local only
- Browser auto-open + git push: local only

## Common edits

- **Add/change RSS feeds**: edit the `feeds` list in `gather_papers()`
- **Change paper counts**: edit the `規則` section of the prompt and the corresponding render functions
- **Add a new tab**: (1) add CSS color token + card styles to template, (2) add nav button + tab panel with `{{NEW_PLACEHOLDER}}` to template, (3) add section to Gemini JSON schema in prompt, (4) add render function, (5) update `build_html()` and `build_error_html()` to replace the new placeholder
- **Selection criteria for picks/papers**: edit the `選文標準` block near the bottom of the prompt in `call_gemini()`
- **Reset dedup history**: delete `shown_papers.json` to start fresh
- **Dedup cap**: `save_shown()` keeps only the last 500 paper IDs; adjust in that function if needed
