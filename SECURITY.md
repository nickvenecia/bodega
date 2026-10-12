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
| What's sent to an AI | Gear names and links only (never renters or rentals), and only when you use AI |
| Web pages and links | `bodega/core/web.py`: https only, public internet addresses only (checked on every redirect, and the connection goes to the checked address), size and unpacking caps, a linear HTML parser |
| AI answers | Must fit a strict shape (`bodega/services/ai/tasks.py`): plain text, sane lengths, real numbers, checked links; you review every change; a copy of your gear is kept first |
| API keys in transit | Sent only to the provider's own address over https (plain http only to this computer), never on a redirect, never through a proxy for a local model |
| Text on screen | Names and AI answers are always shown as plain text, never as formatting |
| Spreadsheets | Only web links are kept; CSV exports can't carry formulas; huge or booby-trapped files are refused |
| Updates | Only from this repository's releases; the SHA-256 must match; a signed Mac app must be replaced by one signed by the same developer |
| The build | GitHub Actions pinned to exact commits; the signing certificate only in the signing step; dependencies pinned, with Dependabot proposing updates |
