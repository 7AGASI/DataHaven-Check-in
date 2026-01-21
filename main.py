import json
import base64
import requests
from web3 import Web3
from eth_account import Account
from eth_account.messages import encode_defunct
from datetime import datetime, timezone
from colorama import init, Fore
from session import iter_proxies, get_session
from utils.user_agent import get_user_agent
import time
import random
import os
import sys

init(autoreset=True)
web3 = Web3()

API_URL = "https://gql3.absinthe.network/v1/graphql"
CLIENT_SEASON = "d2ct-npic"
POINT_SOURCE_ID = "09b99963-757e-46fa-8b79-95d1cdbed7d5"

def datahaven_daylink():
    def iter_private_keys(path="data/keys.txt"):
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                key = line.strip()
                if key and not key.startswith("#"):
                    yield key

    def get_signature(message, wallet):
        encoded_msg = encode_defunct(text=message)
        signed_msg = web3.eth.account.sign_message(encoded_msg, private_key=wallet.key)
        return signed_msg.signature.hex()

    def get_user_id_from_token(token):
        try:
            parts = token.split('.')
            if len(parts) != 3:
                return None
            
            payload_b64 = parts[1]
            payload_b64 += '=' * (4 - len(payload_b64) % 4)
            payload_b64 = payload_b64.replace('-', '+').replace('_', '/')
            
            payload_bytes = base64.b64decode(payload_b64)
            payload = json.loads(payload_bytes.decode('utf-8'))
            
            user_id = payload.get('userId') or payload.get('user_id')
            if not user_id and "https://hasura.io/jwt/claims" in payload:
                user_id = payload["https://hasura.io/jwt/claims"].get('x-hasura-user-id')
            
            return user_id
        except:
            return None

    def do_checkin(sess, token, user_id, user_agent):
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Origin": "https://camphaven.xyz",
            "Referer": "https://camphaven.xyz/",
            "User-Agent": user_agent,
        }
        
        payload = {
            "operationName": "upsertDailyCheckin",
            "query": "mutation upsertDailyCheckin($object: DailyCheckinInput!) { daily_checkin(point_source_data: $object) { id } }",
            "variables": {
                "object": {
                    "user_id": user_id,
                    "client_season": CLIENT_SEASON,
                    "point_source_id": POINT_SOURCE_ID,
                    "status": "SUCCESS"
                }
            }
        }
        
        try:
            r = sess.post(API_URL, json=payload, headers=headers, timeout=30)
            data = r.json()
            
            if r.status_code == 200:
                if "errors" in data:
                    error_msg = str(data["errors"])
                    if "already checked in" in error_msg.lower() or "duplicate" in error_msg.lower():
                        return "ALREADY_DONE"
                    return "FAILED"
                return "SUCCESS"
            return "FAILED"
        except:
            return "FAILED"

    proxies = iter_proxies("data/proxy.txt")
    if not proxies:
        print(Fore.RED + "No proxies in data/proxy.txt")
        return

    try:
        with open("data/keys.txt", "r", encoding="utf-8") as f:
            private_keys = [line.strip() for line in f if line.strip() and not line.startswith("#")]
    except:
        print(Fore.RED + "No keys in data/keys.txt")
        return

    if not private_keys:
        print(Fore.RED + "No keys found")
        return

    print(Fore.YELLOW + f"\nFound: {len(private_keys)} key, {len(proxies)} proxy")
    print(Fore.YELLOW + "═" * 60)

    successful = 0
    failed = 0
    already_done = 0

    for i, private_key in enumerate(private_keys, 1):
        proxy_str = proxies[(i - 1) % len(proxies)]
        
        print(Fore.YELLOW + f"\nWallet {i}/{len(private_keys)}")
        print(Fore.YELLOW + "═" * 60)
        
        csrf_status = Fore.YELLOW + "PENDING"
        auth_status = Fore.YELLOW + "PENDING"
        user_id_status = Fore.YELLOW + "PENDING"
        checkin_status = Fore.YELLOW + "PENDING"
        debug_status = Fore.YELLOW + "PENDING"

        try:
            session = get_session(proxy_str)
            account = web3.eth.account.from_key(private_key)
            address = account.address
            user_agent = get_user_agent()

            headers = {
                'accept': '*/*',
                'accept-language': 'en-US,en;q=0.9,ru;q=0.8,zh-TW;q=0.7,zh;q=0.6,uk;q=0.5',
                'content-type': 'application/json',
                'priority': 'u=1, i',
                'referer': 'https://camphaven.xyz/connections',
                'sec-ch-ua': '"Google Chrome";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"',
                'sec-fetch-dest': 'empty',
                'sec-fetch-mode': 'cors',
                'sec-fetch-site': 'same-origin',
                'user-agent': user_agent,
            }

            response = session.get('https://camphaven.xyz/api/auth/csrf', headers=headers, timeout=30)
            csrf_token = response.json()['csrfToken']
            full_csrf_token = response.cookies.get('__Host-authjs.csrf-token')
            csrf_status = Fore.GREEN + "SUCCESS"

            headers = {
                'accept': '*/*',
                'accept-language': 'en-US,en;q=0.9,ru;q=0.8,zh-TW;q=0.7,zh;q=0.6,uk;q=0.5',
                'content-type': 'application/x-www-form-urlencoded',
                'origin': 'https://camphaven.xyz',
                'priority': 'u=1, i',
                'referer': 'https://camphaven.xyz/connections',
                'sec-ch-ua': '"Google Chrome";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"',
                'sec-fetch-dest': 'empty',
                'sec-fetch-mode': 'cors',
                'sec-fetch-site': 'same-origin',
                'user-agent': user_agent,
                'x-auth-return-redirect': '1',
            }

            issued_at = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.') + f'{datetime.now(timezone.utc).microsecond // 1000:03d}Z'
            message = f'camphaven.xyz wants you to sign in with your Ethereum account:\n{address}\n\nPlease sign with your account\n\nURI: https://camphaven.xyz\nVersion: 1\nChain ID: 1\nNonce: {csrf_token}\nIssued At: {issued_at}\nResources:\n- connector://injected'
            signature = get_signature(message, account)

            data = {
                'message': message,
                'redirect': 'false',
                'signature': f"0x{signature}",
                'csrfToken': csrf_token,
                'callbackUrl': 'https://camphaven.xyz/connections',
            }
            
            cookies = {
                'client-season': 'd2ct-npic',
                'domain': 'https%3A%2F%2Fcamphaven.xyz',
                'redirect-origin': 'https%3A%2F%2Fcamphaven.xyz',
                '__Secure-authjs.callback-url': 'https%3A%2F%2Fboost.absinthe.network',
                '__Host-authjs.csrf-token': full_csrf_token,
                'redirect-pathname': '%2Fd2ct-npic%2Fhome',
            }

            response = session.post(
                'https://camphaven.xyz/api/auth/callback/credentials',
                headers=headers,
                data=data,
                cookies=cookies,
                timeout=30
            )

            bearer_token = response.cookies.get('__Secure-authjs.session-token')
            if bearer_token:
                auth_status = Fore.GREEN + "SUCCESS"
                
                user_id = get_user_id_from_token(bearer_token)
                if user_id:
                    user_id_status = Fore.GREEN + "SUCCESS"
                    
                    checkin_result = do_checkin(session, bearer_token, user_id, user_agent)
                    
                    if checkin_result == "SUCCESS":
                        checkin_status = Fore.GREEN + "SUCCESS"
                        debug_status = Fore.GREEN + "Status = 200"
                        successful += 1
                    elif checkin_result == "ALREADY_DONE":
                        checkin_status = Fore.GREEN + "ALREADY DONE"
                        debug_status = Fore.GREEN + "Status = 200"
                        already_done += 1
                    else:
                        checkin_status = Fore.RED + "FAILED"
                        debug_status = Fore.RED + "Status != 200"
                        failed += 1
                else:
                    user_id_status = Fore.RED + "FAILED"
                    failed += 1
            else:
                auth_status = Fore.RED + "FAILED"
                failed += 1

        except Exception as e:
            debug_status = Fore.RED + f"Error: {str(e)[:50]}"
            failed += 1

        print(f"CSRF Status: {csrf_status}")
        print(f"Auth Status: {auth_status}")
        print(f"User_id Status: {user_id_status}")
        print(f"Debug: {debug_status}")
        print(f"Check-in Status: {checkin_status}")

        if i < len(private_keys):
            time.sleep(random.uniform(5, 12))

def clear():
    os.system('cls' if os.name == 'nt' else 'clear')

def show_banner():
    banner = r'''
 █████╗  ██████╗  █████╗  ███████╗ ██╗
██╔══██╗██╔════╝ ██╔══██╗ ██╔════╝ ██║
███████║██║  ███╗███████║ ███████╗ ██║
██╔══██║██║   ██║██╔══██║ ╚════██║ ██║
██║  ██║╚██████╔╝██║  ██║ ███████║ ██║
╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝ ╚══════╝ ╚═╝
'''
    clear()
    print(Fore.BLUE + banner)

def menu():
    show_banner()
    print(Fore.CYAN + "╔═══════════════════════════════════════╗")
    print(Fore.CYAN + "║          CAMPHAVEN CHECK-IN           ║")
    print(Fore.CYAN + "║                                       ║")
    print(Fore.CYAN + "║     Contact with me: t.me/xAGASI      ║")
    print(Fore.CYAN + "╠═══════════════════════════════════════╣")
    print(Fore.CYAN + "║  [1] Запустить                        ║")
    print(Fore.CYAN + "║  [2] Выход                            ║")
    print(Fore.CYAN + "╚═══════════════════════════════════════╝")

    choice = input(Fore.YELLOW + "\nВыбор: ").strip()

    if choice == "1":
        datahaven_daylink()
    elif choice == "2":
        sys.exit()
    else:
        sys.exit()

if __name__ == "__main__":
    menu()