# AiSensy session refresh (macOS)

Run this whenever the broadcast sync fails with "AISENSY_LOGIN_EXPIRED" or a
redirect to login — for example after someone logs the automation out of AiSensy.

## Setup (once)
1. Clone this repo, or download it as a ZIP from GitHub (Code → Download ZIP) and unzip it.
2. Python 3.10+ is required. The first run creates a local `.venv` and downloads
   Playwright Chromium; later runs reuse them.

## Every time the session expires
```bash
bash session-refresh/refresh.command
```
1. Sign in to AiSensy in the browser that opens and complete the OTP yourself.
2. Open Campaigns and confirm in Terminal that campaign rows are visible.
3. A second window verifies the saved login. **Do not sign in there.** Confirm
   only if rows load without logging in.
4. The helper copies the compressed session and opens this repo's
   `AISENSY_SESSION` secret page. Paste, click **Update secret**, then press
   Enter in Terminal.
5. Rerun the workflow from the Actions tab.

### Optional direct upload
With GitHub CLI installed and `gh auth login` done once:
```bash
bash session-refresh/refresh.command --upload
```
This replaces `AISENSY_SESSION` after verification. Your GitHub account needs
permission to manage this repo's Actions secrets.

## Device name in AiSensy
Logins made by this helper, and the workflows that reuse them, identify
themselves as **"Broadcast Automation - DO NOT LOG OUT"**. Leave that entry
alone in AiSensy's logged-in devices list — logging it out stops the sync until
this helper is run again.

## Safety
Session data stays in memory, is never printed or written to a file, and is
compressed before clipboard/upload. Clipboard mode clears it on finish if
unchanged. Never commit session data or paste it into chat.
