# Windows 95 personal projects desktop

This is a personalized working copy of [Yuteoctober/wins95Portfolio](https://github.com/Yuteoctober/wins95Portfolio), based on upstream commit `af5c7eccebec51650eca5579e425b2aab47520f4`.

The original Windows 95 visual language and desktop interactions are retained. This adaptation presents the following real projects rather than the original author's résumé and projects:

| Project | Opens |
| --- | --- |
| Callay | <https://ashstarry.github.io/callay-site/> — the Mac input method's website and demo, not the native application itself |
| Wonderline | <https://wonderline.fun/> — the drawing application |
| Koyoi · 今宵 | <https://koyoi.fun/> — the interactive miniature town |

The first visit opens **ashstarry’s personal homepage**, with an introduction and three illustrated project summaries explaining what each project does. Project buttons, desktop shortcuts, Enter, Start and Run open the real site inside a desktop browser window. Each window supports minimize, maximize, close, refresh, and an explicit independent-tab fallback. Only opened projects are loaded; closing a browser window unmounts its iframe. Callay is clearly identified as a native Mac input method whose website/demo is embedded. The blog currently contains no articles. The inherited template archive is unpublished, and the former Blog Archive shortcut is removed (including from saved desktop layouts).

## Run and build

```sh
npm ci --ignore-scripts --no-audit --no-fund
npm run dev
npm run build
npm run preview
```

The project is React 18 and Vite 5, using its checked-in `package-lock.json`. The production build is `dist/`. Vite uses `base: './'`, so the output can be served at a domain root or a directory such as `/windows95/`.

The dependency install scripts were inspected and the first build was verified locally. No GitHub push, upstream deployment, or external chat message is part of these commands. This working copy does not need application API keys.

## What is kept

- Windows, dragging, resizing, minimize/maximize, taskbar, Start menu, Run, and shutdown/restart/guest-login screens.
- Desktop icons, dragging files into folders, right-click menus, recycling/restoring shortcuts, and a virtual My Computer hierarchy.
- Calendar, Minesweeper, wallpaper and title-bar colours, icon sizes, Clippy, Task Manager, local app launcher, Tile Screen, and the simulated app Store.
- Winamp/Webamp, with an **empty initial playlist**. Visitors can supply their own local audio; no default music track is distributed or played.
- A local **NotePad** using the original document-window shell. Its contents are saved only in the visitor's browser.
- A local **Paint** canvas with colour, brush width, clear/undo-clear and PNG export. It replaces the upstream external JSPaint iframe.

The virtual Store's install/uninstall operations organize desktop icons; they do not install software on the visitor's computer. The optional guest-login screen is playful UI, not authentication.

## External services deliberately not inherited

The original site connected to the author's own services. This adaptation does not mount or connect its MSN/live-chat/AI assistant, email sending, news/weather/geolocation, Bitcoin feed, original résumé, old portfolio projects, remote wallpaper rotation, or analytics. Their disabled legacy app names route to the About window rather than opening someone else's service.

The original backend credentials and remote endpoints are not required for this site. Implementing a real public guestbook or live chat later would require a separate backend and moderation/storage choices.

Browser storage is prefixed with `personal-win95-v1:`. Reset affects this desktop's saved preferences and virtual files only; the original whole-origin `localStorage.clear()` upgrade behaviour was removed, so sibling sites or previews are not erased.

## Personalization entry points

- `src/personalProjects.js`: verified names, descriptions, and destination URLs; shared navigation for project links.
- `src/icon.json`: placement of project files, desktop `.url` shortcuts, and the local apps available in the virtual Store.
- `src/components/function/AppFunctions.js`: icon asset mapping. `.url` filenames resolve to the same icon as the corresponding project.
- `src/components/PortfolioFolder.jsx` and `src/css/PortfolioFolder.css`: first-visit personal homepage and project descriptions.
- `src/components/PersonalBrowser.jsx` and `src/css/PersonalBrowser.css`: embedded project browser windows and taskbar entries.
- `src/components/MyBioFolder.jsx`: neutral About text, project summary, and upstream credits. Add a real biography or contact details here only when supplied.
- `src/components/ResumeFile.jsx`: now the local NotePad implementation; the legacy source filename is preserved to reduce changes to window state management.
- `src/components/LocalPaint.jsx`: the browser-local Paint tool.
- `src/portfolioStorage.js`: safe, namespaced browser storage.
- `src/personal.css`: small integration/accessibility and narrow-screen adjustments on top of the original UI.

For another project, add its URL to `personalProjects.js`, add a Project entry and optional unique `.url` desktop entry in `icon.json`, and map its icon. Do not reuse identical `name` values for two files: the original drag-and-drop code uses names as file identities.

## Asset simplification

Original résumé material, old project photos, the bundled pop song and unused spinning-cat video were removed from the customized source. Several very large decorative assets were replaced with lightweight **Silver Waves** and **Scanlines** SVG alternatives. The Tile Screen no longer cycles the original author's personal photos. This retains the wallpaper/Tile features while reducing unrelated source assets from approximately 174 MB to 49 MB before final packaging.

## Credits and licensing

Upstream: **Yute / wins95Portfolio**, copyright © 2024 Yute, [MIT License](LICENSE). Its copyright and permission notice remain intact, and the built site includes `UPSTREAM-LICENSE.txt` from `public/`. The About → Credits panel links to the original repository; the homepage itself leads with the portfolio owner and their work.

The upstream README records Windows 95 icons and library credits. The visual identity and third-party assets retain their respective upstream provenance; this site is not affiliated with Microsoft. Webamp retains its own bundled license notices.

## Verification notes

- `npm ci --ignore-scripts --no-audit --no-fund` succeeded with the upstream lockfile.
- The first adapted `npm run build` passed. It reports the upstream Webamp `eval` notice and a large-JavaScript-chunk warning; the latter is a performance consideration rather than a build failure.
- Final source packaging and browser checks are performed by the owning task after asset cleanup. No full dependency migration or exhaustive test suite was undertaken as part of this onboarding.
