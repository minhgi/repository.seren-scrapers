# repository.seren-scrapers
Seren scrapers - a4kscrapers_easynews_orion

## Install

These are Seren *provider packages* (Orion, EasyNews/`a4kNewsgroups`, `a4kScrapers`) — not Kodi add-ons. They never appear in Kodi's Add-ons browser. Seren installs and updates them entirely on its own, through its own provider-manager screen. Seren itself must already be installed first.

1. In Seren: **Tools → Provider Tools → Manage Provider Packages → Install Package**.
2. Choose **Web Location...** — this opens Seren's "Enter Zip URL" prompt.
3. Paste one of the URLs below, confirm, then repeat steps 1-3 for each remaining package.

| Package | URL |
|---|---|
| Orion | `https://raw.githubusercontent.com/minhgi/repository.seren-scrapers/main/repo/zips/Orion/Orion-5.0.1.zip` |
| EasyNews (a4kNewsgroups) | `https://raw.githubusercontent.com/minhgi/repository.seren-scrapers/main/repo/zips/a4kNewsgroups/a4kNewsgroups-1.4.9.zip` |
| a4kScrapers | `https://raw.githubusercontent.com/minhgi/repository.seren-scrapers/main/repo/zips/a4kScrapers/a4kScrapers-2.99.127.zip` |

4. **EasyNews needs credentials before it'll return anything.** Back in Manage Provider Packages, select `a4kNewsgroups` → **Configure Package** → enter your EasyNews username/password. Orion and a4kScrapers don't need this step.

Once installed, Seren checks each package's `remote_meta` on its own maintenance cycle and re-downloads automatically when a version goes up — no need to repeat these steps for future updates.
