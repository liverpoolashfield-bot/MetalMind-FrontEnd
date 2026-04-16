# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository

Single-file static landing page for "MetalMind AI" (an AI Hackathon project pitched as an import-optimization product). Everything lives in `index.html` — HTML, CSS (inline `<style>`), and JS (inline `<script>`) are all in one document. No build system, package manager, tests, or dependencies beyond CDN-loaded Google Fonts.

## Running / previewing

Open `index.html` directly in a browser, or serve the directory with any static server (e.g. `python -m http.server`). There is no build, lint, or test step.

## Structure inside the single file

- `:root` CSS custom properties at the top of `<style>` define the full design system — dark background tokens (`--bg-primary/secondary/card`), an off-gold `--accent` (`#c9a84c`) and a `--teal` secondary. Change colors here rather than in individual rules.
- Typography uses `DM Sans` (body), `Playfair Display` (display/logo), and `JetBrains Mono` (mono accents), all via the single Google Fonts `<link>` in `<head>`.
- Sections are delimited by `/* ─── NAME ─── */` comment banners in the CSS (NAV, HERO, etc.) — use these as the map when editing. Matching semantic HTML sections appear in `<body>` in the same order.

When making changes, prefer editing within the existing single file and reusing the CSS variables/section conventions above rather than introducing new files, frameworks, or a build step.
