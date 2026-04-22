#!/usr/bin/env python3
"""
Telegram File Bot - BIN_CHANNEL System
Deployed on ClawCloud 24/7
"""

import os
import json
import time
import hashlib
import requests
import logging
from datetime import datetime

# ============= Configuration from Environment =============
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8737153370:AAFXBLh4RlMMDz7ib2iO-lrVyLIgdtuye3w')
ADMIN_ID = int(os.environ.get('ADMIN_ID', '8034002993'))
PUBLIC_URL = os.environ.get('PUBLIC_URL', 'https://eren-yeager.h.jrnm.app')

# BIN_CHANNEL - The secret sauce for Pakistan video downloads
BIN_CHANNEL = int(os.environ.get('BIN_CHANNEL', '-1003656827536'))

API = f"https://api.telegram.org/bot{BOT_TOKEN}"

# In-memory storage
pending_rename = {}
admin_broadcast_state = {}
blocked_users = set()
approved_users = set()
approval_mode = False
all_users = {}

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# ============= Helper Functions =============

def send_message(chat_id, text, reply_markup=None):
    data = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if reply_markup:
        data["reply_markup"] = json.dumps(reply_markup)
    try:
        requests.post(f"{API}/sendMessage", json=data, timeout=10)
    except Exception as e:
        logger.error(f"Send error: {e}")


def answer_callback(callback_id):
    try:
        requests.post(f"{API}/answerCallbackQuery", json={"callback_query_id": callback_id}, timeout=5)
    except:
        pass


def get_file_from_message(msg):
    if 'document' in msg:
        return msg['document']['file_id'], msg['document'].get('file_name', 'document'), msg['document'].get('file_size', 0)
    elif 'video' in msg:
        return msg['video']['file_id'], f"video_{msg['video']['file_unique_id'][:8]}.mp4", msg['video'].get('file_size', 0)
    elif 'audio' in msg:
        return msg['audio']['file_id'], msg['audio'].get('file_name', 'audio.mp3'), msg['audio'].get('file_size', 0)
    elif 'photo' in msg:
        p = msg['photo'][-1]
        return p['file_id'], f"photo_{p['file_unique_id'][:8]}.jpg", p.get('file_size', 0)
    elif 'voice' in msg:
        return msg['voice']['file_id'], f"voice_{msg['voice']['file_unique_id'][:8]}.ogg", msg['voice'].get('file_size', 0)
    elif 'animation' in msg:
        return msg['animation']['file_id'], msg['animation'].get('file_name', 'animation.gif'), msg['animation'].get('file_size', 0)
    return None, None, 0


def forward_to_bin_channel(file_id, filename, file_size):
    """Forward file to BIN_CHANNEL and get new stable file_id"""
    try:
        resp = requests.post(
            f"{API}/sendDocument",
            json={
                "chat_id": BIN_CHANNEL,
                "document": file_id,
                "disable_notification": True
            },
            timeout=30
        )
        
        data = resp.json()
        if data.get('ok'):
            new_file_id = data['result']['document']['file_id']
            logger.info(f"✅ File backed up to BIN_CHANNEL: {filename}")
            return new_file_id
        else:
            logger.error(f"BIN_CHANNEL forward failed: {data}")
            return None
            
    except Exception as e:
        logger.error(f"BIN_CHANNEL error: {e}")
        return None


def register_file_via_api(file_id, filename, file_size, uploader_id, uploader_name):
    try:
        payload = {
            "file_id": file_id,
            "filename": filename,
            "file_size": file_size,
            "uploader_id": uploader_id,
            "uploader_name": uploader_name
        }
        resp = requests.post(f"{PUBLIC_URL}/register", json=payload, timeout=10)
        if resp.status_code == 200:
            return resp.json()
        else:
            logger.error(f"Register failed: {resp.status_code}")
            return None
    except Exception as e:
        logger.error(f"Register API error: {e}")
        return None


def is_authorized(user_id):
    return str(user_id) == str(ADMIN_ID)


def is_user_allowed(user_id):
    if is_authorized(user_id):
        return True
    if str(user_id) in blocked_users:
        return False
    if approval_mode:
        return str(user_id) in approved_users
    return True


def track_user(user_id, user_info):
    all_users[str(user_id)] = {
        "username": user_info.get('username', ''),
        "first_name": user_info.get('first_name', ''),
        "last_seen": datetime.now().isoformat()
    }


def broadcast_to_all(admin_chat_id, message):
    sent = 0
    for uid in all_users:
        if uid in blocked_users or uid == str(ADMIN_ID):
            continue
        try:
            send_message(int(uid), f"<b>📢 Announcement</b>\n\n{message}")
            sent += 1
            time.sleep(0.05)
        except:
            pass
    send_message(admin_chat_id, f"✅ Broadcast sent to {sent} users.")


def get_admin_keyboard():
    return {
        "inline_keyboard": [
            [{"text": "📊 Stats", "callback_data": "admin_stats"}],
            [{"text": "👥 Users", "callback_data": "admin_users"}],
            [{"text": "🚫 Blocked", "callback_data": "admin_blocked"}],
            [{"text": "✅ Approvals", "callback_data": "admin_approvals"}],
            [{"text": "📁 Files", "callback_data": "admin_files"}],
            [{"text": "📢 Broadcast", "callback_data": "admin_broadcast"}],
            [{"text": "❌ Close", "callback_data": "admin_close"}]
        ]
    }


def show_admin_stats(chat_id):
    try:
        resp = requests.get(f"{PUBLIC_URL}/stats")
        if resp.status_code == 200:
            data = resp.json()
            text = f"📊 <b>Stats</b>\n\n• Files: {data['total_files']}\n• Users: {len(all_users)}"
        else:
            text = f"📊 <b>Stats</b>\n\n• Users: {len(all_users)}"
    except:
        text = f"📊 <b>Stats</b>\n\n• Users: {len(all_users)}"
    send_message(chat_id, text)


def show_admin_users(chat_id):
    if not all_users:
        send_message(chat_id, "No users yet.")
        return
    recent = list(all_users.items())[-10:]
    text = "<b>👥 Recent Users</b>\n\n"
    for uid, info in recent:
        status = "✅" if uid not in blocked_users else "🚫"
        name = info.get('first_name') or info.get('username') or uid
        text += f"{status} <code>{uid}</code> – {name}\n"
    send_message(chat_id, text)


def show_admin_blocked(chat_id):
    if blocked_users:
        text = "<b>🚫 Blocked Users</b>\n\n" + "\n".join(f"• <code>{uid}</code>" for uid in blocked_users)
    else:
        text = "✅ No blocked users."
    send_message(chat_id, text)


def show_admin_approvals(chat_id):
    if not approval_mode:
        send_message(chat_id, "ℹ️ Approval mode is OFF.")
        return
    pending = [uid for uid in all_users if uid not in approved_users and uid not in blocked_users and uid != str(ADMIN_ID)]
    if not pending:
        send_message(chat_id, "✅ No pending approvals.")
        return
    text = "<b>⏳ Pending</b>\n\n"
    for uid in pending[:5]:
        info = all_users.get(uid, {})
        name = info.get('first_name') or uid
        text += f"• <code>{uid}</code> – {name}\n"
    keyboard = {
        "inline_keyboard": [
            [{"text": f"✅ Approve {uid}", "callback_data": f"approve_{uid}"}] for uid in pending[:5]
        ]
    }
    send_message(chat_id, text, reply_markup=keyboard)


def show_admin_files(chat_id):
    try:
        resp = requests.get(f"{PUBLIC_URL}/stats")
        if resp.status_code == 200:
            data = resp.json()
            files = data.get('files', [])[-5:]
            text = "<b>📁 Recent Files</b>\n\n"
            for f in files:
                size_mb = f['size'] / (1024 * 1024) if f['size'] else 0
                text += f"• {f['filename'][:25]} ({size_mb:.1f} MB)\n"
            send_message(chat_id, text)
            return
    except:
        pass
    send_message(chat_id, "📁 No files yet.")


def handle_admin_callback(chat_id, user_id, data, message_id):
    global approval_mode
    if not is_authorized(user_id):
        return
    if data == "admin_stats":
        show_admin_stats(chat_id)
    elif data == "admin_users":
        show_admin_users(chat_id)
    elif data == "admin_blocked":
        show_admin_blocked(chat_id)
    elif data == "admin_approvals":
        show_admin_approvals(chat_id)
    elif data == "admin_files":
        show_admin_files(chat_id)
    elif data == "admin_broadcast":
        admin_broadcast_state[chat_id] = True
        send_message(chat_id, "📢 Send me the message to broadcast:")
    elif data == "admin_close":
        requests.post(f"{API}/deleteMessage", json={"chat_id": chat_id, "message_id": message_id})
    elif data.startswith("approve_"):
        target = data.split("_")[1]
        approved_users.add(target)
        send_message(chat_id, f"✅ User {target} approved.")
        try:
            send_message(int(target), "✅ Your account has been approved!")
        except:
            pass
    elif data.startswith("block_"):
        target = data.split("_")[1]
        blocked_users.add(target)
        approved_users.discard(target)
        send_message(chat_id, f"✅ User {target} blocked.")
    elif data.startswith("unblock_"):
        target = data.split("_")[1]
        blocked_users.discard(target)
        send_message(chat_id, f"✅ User {target} unblocked.")


# ============= Main Bot Loop =============

def main():
    global approval_mode
    logger.info("🤖 Bot starting on ClawCloud...")
    logger.info(f"BIN_CHANNEL: {BIN_CHANNEL}")
    logger.info(f"Public URL: {PUBLIC_URL}")

    try:
        r = requests.get(f"{API}/getMe", timeout=10)
        if r.status_code == 200:
            me = r.json()['result']
            logger.info(f"✅ Connected as @{me['username']}")
        else:
            logger.error("❌ Cannot reach Telegram API")
            return
    except Exception as e:
        logger.error(f"❌ API error: {e}")
        return

    offset = 0

    while True:
        try:
            resp = requests.get(f"{API}/getUpdates", params={"timeout": 30, "offset": offset}, timeout=35)
            data = resp.json()
            if not data.get('ok'):
                continue

            for update in data['result']:
                offset = update['update_id'] + 1

                if 'callback_query' in update:
                    cq = update['callback_query']
                    chat_id = cq['message']['chat']['id']
                    user_id = cq['from']['id']
                    callback_data = cq['data']
                    message_id = cq['message']['message_id']

                    answer_callback(cq['id'])

                    if is_authorized(user_id):
                        handle_admin_callback(chat_id, user_id, callback_data, message_id)
                    else:
                        if callback_data.startswith('rename:'):
                            file_hash = callback_data.split(':')[1]
                            pending_rename[chat_id] = file_hash
                            send_message(chat_id, "✏️ Send me the new filename:")
                        elif callback_data.startswith('delete:'):
                            send_message(chat_id, "Delete via web dashboard.")
                    continue

                msg = update.get('message')
                if not msg:
                    continue

                chat_id = msg['chat']['id']
                user_id = msg['from']['id']
                user_info = msg['from']
                text = msg.get('text', '')

                track_user(user_id, user_info)

                if not is_user_allowed(user_id):
                    if approval_mode and str(user_id) not in approved_users:
                        send_message(chat_id, "⏳ Your account is pending approval.")
                        send_message(ADMIN_ID, f"🆕 New user: {user_id} – {user_info.get('first_name')}")
                    else:
                        send_message(chat_id, "⛔ You are blocked.")
                    continue

                if chat_id in admin_broadcast_state and is_authorized(user_id):
                    broadcast_msg = text
                    del admin_broadcast_state[chat_id]
                    broadcast_to_all(chat_id, broadcast_msg)
                    continue

                if chat_id in pending_rename and text:
                    file_hash = pending_rename.pop(chat_id)
                    send_message(chat_id, f"✅ Rename requested for {file_hash}")
                    continue

                if text.startswith('/'):
                    command = text.split()[0].lower()
                    if command == '/start':
                        send_message(chat_id, "<b>🤖 File to Link Bot</b>\n\nSend me any file!\n\n<b>Admin:</b> /admin")
                    elif command == '/admin' and is_authorized(user_id):
                        send_message(chat_id, "<b>🔐 Admin Panel</b>", reply_markup=get_admin_keyboard())
                    elif command == '/ping':
                        send_message(chat_id, "🏓 Pong!")
                    elif command == '/broadcast' and is_authorized(user_id):
                        admin_broadcast_state[chat_id] = True
                        send_message(chat_id, "📢 Send me the message to broadcast:")
                    elif command == '/block' and is_authorized(user_id):
                        parts = text.split()
                        if len(parts) > 1:
                            blocked_users.add(parts[1])
                            send_message(chat_id, f"✅ User {parts[1]} blocked.")
                    elif command == '/unblock' and is_authorized(user_id):
                        parts = text.split()
                        if len(parts) > 1:
                            blocked_users.discard(parts[1])
                            send_message(chat_id, f"✅ User {parts[1]} unblocked.")
                    elif command == '/approve' and is_authorized(user_id):
                        parts = text.split()
                        if len(parts) > 1:
                            approved_users.add(parts[1])
                            send_message(chat_id, f"✅ User {parts[1]} approved.")
                    elif command == '/approvalmode' and is_authorized(user_id):
                        parts = text.split()
                        if len(parts) > 1:
                            if parts[1].lower() == 'on':
                                approval_mode = True
                                send_message(chat_id, "✅ Approval mode ON.")
                            elif parts[1].lower() == 'off':
                                approval_mode = False
                                send_message(chat_id, "✅ Approval mode OFF.")
                    continue

                file_id, file_name, file_size = get_file_from_message(msg)
                if file_id:
                    send_message(chat_id, "⚡ Processing...")
                    
                    backup_file_id = forward_to_bin_channel(file_id, file_name, file_size)
                    final_file_id = backup_file_id if backup_file_id else file_id
                    
                    uploader_name = user_info.get('username', user_info.get('first_name', 'Unknown'))
                    result = register_file_via_api(final_file_id, file_name, file_size, user_id, uploader_name)

                    if result and result.get('success'):
                        download_url = result['download_url']
                        size_mb = file_size / (1024 * 1024) if file_size else 0
                        response = f"""
<b>✅ Link Generated!</b>

<b>📁 File:</b> {file_name}
<b>📊 Size:</b> {size_mb:.2f} MB

<b>🔗 Download:</b> {download_url}
"""
                        keyboard = {
                            "inline_keyboard": [
                                [{"text": "📥 Download", "url": download_url}],
                                [
                                    {"text": "✏️ Rename", "callback_data": f"rename:{result['hash']}"},
                                    {"text": "🗑️ Delete", "callback_data": f"delete:{result['hash']}"}
                                ]
                            ]
                        }
                        send_message(chat_id, response, reply_markup=keyboard)
                    else:
                        send_message(chat_id, "❌ Failed to process file.")

        except KeyboardInterrupt:
            logger.info("Bot stopped")
            break
        except Exception as e:
            logger.error(f"Loop error: {e}")
            time.sleep(3)


if __name__ == '__main__':
    main()
