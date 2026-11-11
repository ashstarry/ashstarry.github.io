# ashstarry · Windows 95 Desktop

Personal homepage: **https://ashstarry.github.io/**

The homepage is an interactive Windows 95 desktop with shortcuts to:

- **Callay** — https://ashstarry.github.io/callay-site/ (Mac input method website and demo).
- **Wonderline** — https://wonderline.fun/ (voice-driven drawing).
- **Koyoi · 今宵** — https://koyoi.fun/ (interactive miniature town).

The first screen introduces ashstarry and explains each project with a concrete example. Project buttons, desktop shortcuts, or Enter open the real project in an embedded desktop browser window, with maximize/minimize/close controls and an explicit independent-tab fallback. The desktop also includes local NotePad, Paint, Minesweeper, a calendar, wallpaper settings, and a Winamp player for the visitor's own audio.

## Source and rebuilding

The React/Vite source is in `_desktop/`. The generated static files are published from the repository root, alongside the existing Jekyll blog.

```sh
cd _desktop
npm ci --ignore-scripts --no-audit --no-fund
cd ..
node tools/build-desktop.mjs
```

Commit the changed source and generated files together. GitHub Pages continues to publish from `master` at the repository root. Do not add `.nojekyll`: the existing blog still needs Jekyll.

Project destinations are maintained in `_desktop/src/personalProjects.js`; icons and their placement are in `_desktop/src/icon.json`. Full adaptation notes are in `_desktop/ONBOARDING.md`.

## Blog archive and rollback

The previous blog index is available at **https://ashstarry.github.io/blog/**. Existing article URLs, layouts, and assets are retained. Pagination is rooted at `/blog/page:num/`.

The previous homepage baseline is commit `c4047846b33b38a6cfda213f487d9492e5bc0a78`; the backup branch is `backup/home-before-win95-2026-11-10`.

The legacy root service worker is retired without deleting origin-wide caches or browser storage. Desktop data has its own `personal-win95-v1:` storage namespace.

## Credits

Desktop foundation: [Yuteoctober/wins95Portfolio](https://github.com/Yuteoctober/wins95Portfolio), upstream commit `af5c7eccebec51650eca5579e425b2aab47520f4`, MIT License, copyright © 2024 Yute. Its license is retained in `_desktop/LICENSE` and `UPSTREAM-LICENSE.txt`, and the desktop includes a visible credit.

The original blog theme's license remains in the root `LICENSE`. This site is not affiliated with Microsoft. No author-owned chat, email, weather, or AI backend is required by this adaptation.
