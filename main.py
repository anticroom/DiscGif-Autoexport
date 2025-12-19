import os
import re
import json
import base64
import requests
import win32crypt
from Crypto.Cipher import AES

LOCAL = os.getenv("LOCALAPPDATA")
ROAMING = os.getenv("APPDATA")
# Only discord dirs cus fuck doing it to browsers lol
PATHS = {
    'Discord': ROAMING + '\\discord',
    'Discord Canary': ROAMING + '\\discordcanary',
    'Lightcord': ROAMING + '\\Lightcord',
    'Discord PTB': ROAMING + '\\discordptb',
}
def extract():
    def get_tokens(path):
        path += "\\Local Storage\\leveldb\\"
        if not os.path.exists(path):
            return []
        tokens = []
        for file in os.listdir(path):
            if not file.endswith((".ldb", ".log")):
                continue
            try:
                with open(os.path.join(path, file), "r", errors="ignore") as f:
                    for line in f:
                        tokens.extend(re.findall(r"[\w-]{24}\.[\w-]{6}\.[\w-]{27,}", line))
                        tokens.extend(re.findall(r"dQw4w9WgXcQ:[^\"]+", line))
            except:
                continue
        return tokens

    def get_key(path):
        try:
            with open(os.path.join(path, "Local State"), "r", encoding="utf-8") as f:
                local_state = json.load(f)
            encrypted_key = base64.b64decode(local_state['os_crypt']['encrypted_key'])[5:]
            return win32crypt.CryptUnprotectData(encrypted_key, None, None, None, 0)[1]
        except:
            return None

    def decrypt_token(raw_token, key):
        if raw_token.startswith("dQw4w9WgXcQ:"):
            try:
                encrypted_token_bytes = base64.b64decode(raw_token[12:])
                nonce = encrypted_token_bytes[3:15]
                cipher_bytes = encrypted_token_bytes[15:-16]
                tag = encrypted_token_bytes[-16:]
                cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
                return cipher.decrypt_and_verify(cipher_bytes, tag).decode()
            except:
                return None
        return raw_token

    def get_user_id(token):
        headers = {"Authorization": token, "Content-Type": "application/json"}
        try:
            response = requests.get("https://discord.com/api/v9/users/@me", headers=headers, timeout=10)
            if response.status_code == 200:
                return response.json()["id"]
        except:
            pass
        return None

    found_tokens = []
    seen = set()

    for platform, base_path in PATHS.items():
        if not os.path.exists(base_path):
            continue
        paths_to_check = [base_path]
        try:
            for folder in os.listdir(base_path):
                full = os.path.join(base_path, folder)
                if os.path.isdir(full):
                    lname = folder.lower()
                    if lname.startswith("profile") or lname == "default" or os.path.exists(os.path.join(full, "Local State")):
                        paths_to_check.append(full)
        except:
            pass
        for path in paths_to_check:
            key = get_key(path)
            for raw_token in get_tokens(path):
                token = decrypt_token(raw_token, key) if raw_token.startswith("dQw4w9WgXcQ:") and key else raw_token
                if token and token not in seen:
                    seen.add(token)
                    user_id = get_user_id(token)
                    if user_id:
                        found_tokens.append((token, user_id))

    for token, user_id in found_tokens:
        req_url = "https://discord.com/api/v9/users/@me/settings-proto/2"
        headers = {
            "accept": "*/*",
            "authorization": token,
            "content-type": "application/json",
        }
        try:
            response = requests.get(req_url, headers=headers)
            response.raise_for_status()
            gifs_base64 = response.json().get("settings", "")
            b64 = gifs_base64.strip()
            if len(b64) % 4:
                b64 += "=" * (4 - (len(b64) % 4))
            raw = base64.b64decode(b64)
            cleaned = re.compile(rb"[\x00-\x1F]+").sub(b" ", raw)
            raw_urls = re.compile(rb"https?://(?:[a-zA-Z0-9\-._~:/?#\[\]@!$&'()*+,;=%]|\\[xu][0-9A-Fa-f]{1,4])+").findall(cleaned)
            urls = set()
            for u in raw_urls:
                text = u.decode("unicode_escape", errors="ignore")
                text = text.replace("\\/", "/")
                text = text.rstrip(".,;)]}<>\"' ")
                if "media.discordapp.net" in text:
                    text = text.replace("media.discordapp.net", "cdn.discordapp.com")
                    text = text.split("?")[0]
                    urls.add(text)
                elif "images-ext-1.discordapp.net" in text:
                    continue
                else:
                    urls.add(text)
            if urls:
                downloads_dir = os.path.join(os.path.expanduser("~"), "Downloads")
                try:
                    os.makedirs(downloads_dir, exist_ok=True)
                except:
                    downloads_dir = os.getcwd()
                output_file = os.path.join(downloads_dir, f"favorited_gifs_{user_id}.txt")
                with open(output_file, "w", encoding="utf-8") as f:
                    f.write("\n".join(sorted(urls)))
        except:
            continue
if __name__ == "__main__":
    extract()
    
