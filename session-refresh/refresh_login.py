import argparse
import base64
import json
import shutil
import subprocess
import sys
import webbrowser
import zlib
from urllib.parse import urlsplit

PROJECT = '6589906ef69fc70b424e0e43'
URL = f'https://app.aisensy.com/projects/{PROJECT}/campaigns/all'
REPO = 'Sarthak-B/aisensy-broadcast-tracker'
SECRET = 'AISENSY_SESSION'
HOSTS = {'app.aisensy.com', 'www.app.aisensy.com'}
# Name shown for this login in AiSensy's logged-in devices list.
SESSION_LABEL = 'Broadcast Automation - DO NOT LOG OUT'

def automation_user_agent(browser):
    # Real Chrome version keeps AiSensy treating this as normal Chrome;
    # the label replaces the OS part so the devices list shows it.
    return (f'Mozilla/5.0 ({SESSION_LABEL}) AppleWebKit/537.36 (KHTML, like Gecko) '
            f'Chrome/{browser.version} Safari/537.36 BroadcastAutomation/1.0')

def encode_state(state):
    raw = json.dumps(state, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
    value = 'zlib:' + base64.b64encode(zlib.compress(raw, 9)).decode('ascii')
    if len(value.encode()) >= 48 * 1024:
        raise RuntimeError('Compressed session still exceeds the secret limit. Nothing was uploaded or copied.')
    return value

def campaign_page(context):
    for page in reversed(context.pages):
        try:
            url = urlsplit(page.evaluate('location.href'))
            if url.hostname in HOSTS and f'/projects/{PROJECT}/campaigns' in url.path:
                return page
        except Exception:
            continue
    return None

def confirm(context, prompt):
    while True:
        answer = input(prompt + ' [yes / retry / quit]: ').strip().lower()
        if answer in ('quit', 'q', 'no', 'n'):
            raise RuntimeError('Cancelled. GitHub secret was not changed.')
        # Pump browser events after terminal input; page.url alone can be stale.
        for page in context.pages:
            if not page.is_closed():
                page.wait_for_timeout(300)
                break
        if answer in ('yes', 'y'):
            page = campaign_page(context)
            if page is not None:
                return page
            print('The helper cannot see this project’s Campaigns page yet. Use the browser it opened, then retry.')

def main():
    parser = argparse.ArgumentParser(description='Refresh and verify AiSensy session without saving credentials to disk.')
    parser.add_argument('--upload', action='store_true', help='Upload verified session using an already authenticated GitHub CLI.')
    args = parser.parse_args()
    if args.upload:
        if not shutil.which('gh'):
            raise RuntimeError('Install GitHub CLI first, or run without --upload to copy the secret.')
        if subprocess.run(['gh', 'auth', 'status', '--hostname', 'github.com'], capture_output=True).returncode:
            raise RuntimeError('Run gh auth login first, then rerun with --upload.')
    from playwright.sync_api import sync_playwright, TimeoutError as BrowserTimeout
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        try:
            user_agent = automation_user_agent(browser)
            login = browser.new_context(timezone_id='Asia/Kolkata', user_agent=user_agent)
            print(f'This login will be labelled in AiSensy as: {SESSION_LABEL}')
            page = login.new_page()
            try:
                page.goto(URL, wait_until='domcontentloaded', timeout=60000)
            except BrowserTimeout:
                pass
            print('\nSign in to AiSensy in the opened browser. Complete OTP yourself and open Campaigns.')
            confirm(login, 'Can you see your campaign names and metrics?')
            state = login.storage_state(indexed_db=True)
            # Test the exact encoded/decoded state used by GitHub Actions.
            value = encode_state(state)
            restored = json.loads(zlib.decompress(base64.b64decode(value[5:])))
            check = browser.new_context(storage_state=restored, timezone_id='Asia/Kolkata', user_agent=user_agent)
            verified = check.new_page()
            try:
                verified.goto(URL, wait_until='domcontentloaded', timeout=60000)
            except BrowserTimeout:
                pass
            print('\nA separate verification window is open. DO NOT sign in there.')
            confirm(check, 'Do campaign rows load in that verification window WITHOUT signing in again?')
            print(f'Verified by you. Compressed session size: {len(value.encode())} bytes.')
            if args.upload:
                result = subprocess.run(['gh', 'secret', 'set', SECRET, '--repo', REPO], input=value, text=True, capture_output=True)
                if result.returncode:
                    raise RuntimeError('GitHub rejected the secret update. Check repository access and Secrets write permission. Nothing was copied.')
                print(f'Updated {SECRET} in {REPO}. You can rerun your workflow now.')
            else:
                if not shutil.which('pbcopy'):
                    raise RuntimeError('Clipboard mode requires macOS. Use --upload with GitHub CLI instead.')
                subprocess.run(['pbcopy'], input=value, text=True, check=True)
                webbrowser.open(f'https://github.com/{REPO}/settings/secrets/actions/{SECRET}')
                print('\nSession copied. Paste into AISENSY_SESSION and click Update secret.')
                print('Do not paste the session into chat. Nothing was written to a session file.')
                input('After updating the secret, press Enter to finish: ')
                # Clear only if clipboard still contains this session.
                if shutil.which('pbpaste'):
                    clipboard = subprocess.run(['pbpaste'], capture_output=True, text=True)
                    if clipboard.stdout == value:
                        subprocess.run(['pbcopy'], input='', text=True, check=True)
        finally:
            browser.close()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('\nCancelled.', file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        # Avoid printing library exceptions that might contain browser state.
        print(str(exc) if isinstance(exc, RuntimeError) else f'Refresh failed ({type(exc).__name__}). Try running the helper again.', file=sys.stderr)
        sys.exit(1)
