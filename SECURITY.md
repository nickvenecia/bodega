# Security

## Reporting a problem

Please report security problems privately, not in a public issue: on GitHub, open this repository's
**Security** tab and choose **Report a vulnerability**. Say what you found and how to see it happen. You'll get
a reply, and a fix in a release, as soon as possible.

## What Bodega protects, and how

| What | How |
| --- | --- |
| AI keys, the account sign-in | In the system keychain only (`bodega/services/secrets.py`); never in a file or a log |
| Your gear, rentals, renters | Saved only on your computer; atomic writes; unreadable files are set aside, never overwritten |
| What's sent to an AI | Only when you use AI, to the provider you chose: the gear you ask about (up to 600 pieces a question), with each piece's name, company, series, group, quantity, status, price paid and what goes with what; a page's words when it reads a link. Never renters or rentals. Gear lists and pages are marked as data, never instructions |
| What an AI job may cost | Every answer capped at 4,096 tokens; a job asks at most 150 questions, says how many before a big one, and stops after 3 failures in a row; pages from one store a second apart |
| Web pages and links | `bodega/core/web.py`: https only, public internet addresses only (checked on every redirect, and the connection goes to the checked address), size and unpacking caps, a linear HTML parser |
| AI answers | Must fit a strict shape (`bodega/services/ai/tasks.py`): plain text, sane lengths, real numbers, checked links; you review every change; a safety copy is kept first |
| API keys in transit | Sent only to the provider's own address over https (plain http only to this computer), never on a redirect, never through a proxy for a local model |
| Text on screen | Names and AI answers are always shown as plain text, never as formatting |
| Spreadsheets | Only web links are kept; CSV exports can't carry formulas; huge or booby-trapped files are refused |
| Updates | Only from this repository's releases; the SHA-256 must match; a signed Mac app must be replaced by one signed by the same developer |
| The build | GitHub Actions pinned to exact commits; the signing certificate only in the signing step; dependencies pinned, with Dependabot proposing updates |

## Where your data is, and for how long

Everything is in Bodega's data folder on your computer (Settings › Your Data shows it), except the AI keys and the
account sign-in, which are in the system keychain. Nothing is sent anywhere unless the table says so.

| What | Where | Kept |
| --- | --- | --- |
| Gear, kits, rentals, renters, profiles, settings | `gear.json`, `packages.json`, `rentals/`, `clients.json`, `businesses.json`, `settings.json` | Until you delete them (Edit › Undo can bring a deletion back while Bodega is open) |
| Photos and logos | `photos/`, `logos/` | Kept after a piece is deleted (undo and copies may still use them) |
| Safety copies | `backups/`: one a day, and one before each big change (an import, Tidy Up Groups, AI changes, a restore) | The newest 14 daily copies and the newest 20 others; older ones are deleted. A renter you delete stays in the copies made before |
| Files Bodega couldn't read | Beside the original, renamed `<name>.<why>-<time>` | Until you delete them: they may hold your only copy |
| Back Up zips | Wherever you save them | Not encrypted; keep them as you would the data folder |
| Calendar files | `calendar/` | Until you delete them |
| Feedback not sent yet | `feedback/` | Until sending is switched on and it goes out |
| The log | `logs/`: what Bodega did, never names, emails, phone numbers, addresses or file paths | 4 files of 1 MB each; the oldest is overwritten |
| AI keys, the account sign-in | The system keychain | Until you remove them in Settings |

What leaves your computer, and only when you use the feature:

| Where | What it receives |
| --- | --- |
| GitHub (Check for Updates, and once each time Bodega opens unless you turn it off) | Your internet address and Bodega's version |
| A store's or maker's page (Check Price, Update from Links, a photo from a link) | Your internet address and that page's link |
| Google (Import from a Google Sheet) | Your internet address and the sheet's link |
| Your AI provider | What the table above lists, with your internet address |

## What Bodega accepts

- The data folder isn't encrypted: anyone who can sign in to your computer as you can read it. Bodega relies on
  the computer's own sign-in and disk encryption (FileVault, BitLocker), and Back Up zips are the same.
- Safety copies keep a renter you deleted for as long as the copy is kept (see the table above).
- Your AI provider keeps what's sent to it under its own terms.
- A page Bodega reads for a link can see your internet address, as a web browser's visit would.

## If something goes wrong

- **A bad release.** Publish a fixed version with a higher number at once; Bodega offers it as an update. Mark the
  bad Release as a pre-release on GitHub (so update checks skip it) and say what happened in the next release's
  notes. Never delete a tag people may have installed from.
- **A leaked signing certificate or secret.** Revoke it with the issuer (Apple, the Windows certificate authority),
  remove it from GitHub's Secrets, issue a new one, and publish a release signed with the new one. A Mac copy only
  takes an update signed by the same developer, so say in the release notes how to download it by hand.
- **A security report.** Reply within a week, fix it in a release, and credit the reporter if they'd like.
