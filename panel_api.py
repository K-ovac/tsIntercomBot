import asyncio
import io
import csv
import socket

import aiohttp
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Spacer, PageBreak
from reportlab.lib import colors

from storage import CREDS
from logger import log_error, log_user_action
from config import SELECT_ACTION


# ========= Autolearn =========

async def toggle_autolearn(ip: str, enable: bool = True) -> bool:
    url = f"http://{ip}/cgi-bin/intercom_cgi?action=set&AutoCollectKeys={'on' if enable else 'off'}"
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
        for login, password in CREDS:
            try:
                auth = aiohttp.BasicAuth(login, password)
                async with session.get(url, auth=auth) as resp:
                    text = await resp.text()
                    print(f"Запрос: {url} | Код: {resp.status} | Ответ: {text}")
                    if resp.status == 200:
                        return True
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                log_error(f"Ошибка при запросе к панели {ip} с логином '{login}': {e}")
    return False


# ========= Door code =========

async def toggle_door_code(ip: str, enable: bool = True) -> bool:
    url = f"http://{ip}/cgi-bin/intercom_cgi?action=set&DoorCodeActive={'on' if enable else 'off'}"
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
        for login, password in CREDS:
            try:
                auth = aiohttp.BasicAuth(login, password)
                async with session.get(url, auth=auth) as resp:
                    text = await resp.text()
                    print(f"Запрос: {url} | Код: {resp.status} | Ответ: {text}")
                    if resp.status == 200:
                        return True
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                log_error(f"Ошибка при запросе к панели {ip} с логином '{login}': {e}")
    return False


async def get_current_door_code(ip: str, desc: str) -> str:
    url = f"http://{ip}/cgi-bin/intercom_cgi?action=get"
    for login, password in CREDS:
        auth = aiohttp.BasicAuth(login, password)
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
                async with session.get(url, auth=auth) as resp:
                    if resp.status == 200:
                        text = await resp.text()
                        for line in text.splitlines():
                            if line.startswith("DoorCode="):
                                return line.split("=", 1)[1].strip()
                        return "не удалось получить"
        except Exception as e:
            log_error(f"Ошибка получения текущего кода на {ip} ({desc}): {e}")
    return "не удалось получить"


# ========= Panel summary =========

async def get_panel_summary(ip: str, desc: str) -> str:
    from config import PANEL_INFO_FIELDS

    online = await check_panel(ip)
    online_icon = "🟢" if online == "Панель доступна" else "🔴"
    lines = [f"📋 <b>{desc}</b>", f"{online_icon} Статус: {online}"]

    if online != "Панель доступна":
        return "\n".join(lines)

    for endpoint in PANEL_INFO_FIELDS:
        url = f"http://{ip}{endpoint['url']}"
        keys = endpoint["keys"]
        collected = {}

        for login, password in CREDS:
            auth = aiohttp.BasicAuth(login, password)
            try:
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
                    async with session.get(url, auth=auth) as resp:
                        if resp.status == 200:
                            text = await resp.text()
                            for line in text.splitlines():
                                if "=" in line:
                                    k, _, v = line.partition("=")
                                    if k.strip() in keys:
                                        collected[k.strip()] = v.strip()
                            break
            except Exception as e:
                log_error(f"Ошибка получения данных на {ip} ({desc}): {e}")

        for key, (label, _, formatter) in keys.items():
            value = collected.get(key, "—")
            lines.append(f"{label}: {formatter(value) if value != '—' else '—'}")

    return "\n".join(lines)


# ========= Open door =========

async def open_door(ip: str, door: str, desc: str, update) -> bool:
    url = f"http://{ip}/cgi-bin/intercom_cgi?action={door}"
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
        for login, password in CREDS:
            try:
                auth = aiohttp.BasicAuth(login, password)
                async with session.get(url, auth=auth) as resp:
                    text = await resp.text()
                    print(f"Запрос: {url} | Код: {resp.status} | Ответ: {text}")
                    if resp.status == 200:
                        label = "основная" if door == "maindoor" else "доп"
                        await update.message.reply_text(f"✅ Дверь {label} на панели {desc} открыта")
                        log_user_action(update.effective_user, f"Открытие '{door}' на {ip} ({desc})")
                        return True
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                log_error(f"Ошибка открытия двери '{door}' {ip} ({desc}): {e}")

    await update.message.reply_text(f"❌ Не удалось открыть дверь на панели {desc}")
    return False


# ========= Door magnet =========

async def set_door_magnet(ip: str, door_type: str, state: str, desc: str, update) -> bool:
    url = f"http://{ip}/cgi-bin/intercom_cgi?action=set&{door_type}={state}"
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
        for login, password in CREDS:
            try:
                auth = aiohttp.BasicAuth(login, password)
                async with session.get(url, auth=auth) as resp:
                    text = await resp.text()
                    print(f"Запрос: {url} | Код: {resp.status} | Ответ: {text}")
                    if resp.status == 200:
                        action_label = "включён" if state == "off" else "выключен"
                        door_label = "основной" if door_type == "MainDoorOpenMode" else "доп"
                        await update.message.reply_text(
                            f"✅ Магнит двери {door_label} на панели {desc} {action_label}"
                        )
                        log_user_action(update.effective_user,
                                        f"Управление магнитом '{door_type}' на {ip} ({desc}) - {state}")
                        return True
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                log_error(f"Ошибка управления магнитом '{door_type}' {ip} ({desc}): {e}")

    await update.message.reply_text(f"❌ Не удалось изменить состояние магнита на панели {desc}")
    return False


# ========= Generic poll =========

async def poll_apartment(ip: str, action_url: str, apt: int | None = None) -> str | None:
    url = f"http://{ip}{action_url}" + (f"&Apartment={apt}" if apt is not None else "")
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
        for login, password in CREDS:
            try:
                auth = aiohttp.BasicAuth(login, password)
                async with session.get(url, auth=auth) as resp:
                    if resp.status == 200:
                        text = await resp.text()
                        print(f"Запрос: {url} | Код: {resp.status} | Ответ: {text}")
                        return text
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                log_error(f"Ошибка опроса {ip}, apt={apt}, login={login}: {e}")
    return None


# ========= Line level =========

async def measure_linelevel(ip: str, apt: int) -> int | None:
    text = await poll_apartment(ip, "/cgi-bin/intercom_cgi?action=linelevel", apt)
    if text is None:
        return None
    try:
        return int(text.strip())
    except ValueError:
        return None


# ========= KKM addressing =========

async def get_dks_du(ip: str, desc: str, update) -> bool:
    url = f"http://{ip}/cgi-bin/intercomdu_cgi?action=export"
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
        for login, password in CREDS:
            try:
                auth = aiohttp.BasicAuth(login, password)
                async with session.get(url, auth=auth, timeout=5) as resp:
                    if resp.status != 200:
                        continue

                    content = await resp.text()
                    if not content.strip():
                        continue

                    blocks_text = [b.strip() for b in content.replace("\r", "").split("\n\n") if b.strip()]

                    buffer = io.BytesIO()
                    doc = SimpleDocTemplate(buffer, pagesize=A4)
                    elements = []

                    for block_text in blocks_text:
                        lines = [line for line in block_text.split("\n") if line.strip()]
                        if len(lines) <= 2:
                            continue

                        rows = list(csv.reader(lines))
                        header = [""] + [f"D{i}" for i in range(len(rows[0]))]
                        data = [header]
                        for r_idx, row in enumerate(rows):
                            data.append([f"E{r_idx}"] + row)

                        table = Table(data, repeatRows=1)
                        table.setStyle(TableStyle([
                            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                            ('FONTSIZE', (0, 0), (-1, -1), 8),
                            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
                        ]))
                        elements.append(table)
                        elements.append(Spacer(1, 12))
                        elements.append(PageBreak())

                    if not elements:
                        await update.message.reply_text(f"❌ Не удалось получить таблицы с панели {desc}.")
                        return False

                    doc.build(elements)
                    buffer.seek(0)

                    await update.message.reply_document(
                        document=buffer,
                        filename=f"{desc}_dks_du.pdf",
                        caption=f"📄 Адресация ККМ с панели {desc}"
                    )
                    log_user_action(update.effective_user, f"Выгрузка адресации ККМ (PDF) на {ip} ({desc})")
                    return True

            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                log_error(f"Ошибка выгрузки CSV с панели {ip} ({desc}), login={login}: {e}")

    await update.message.reply_text(f"❌ Не удалось выгрузить адресацию ККМ на панели {desc}.")
    return False


# ========= Ping / availability check =========

async def check_panel(ip: str, ports: tuple = (443, 80), timeout: int = 3) -> str:
    import sys
    try:
        proc = await asyncio.create_subprocess_shell(
            f"ping -c 1 {ip}" if not sys.platform.startswith("win") else f"ping -n 1 {ip}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await proc.communicate()
        if proc.returncode != 0:
            return "Панель недоступна (нет ответа на ping)"
    except Exception as e:
        return f"Ошибка проверки ping: {e}"

    for port in ports:
        try:
            loop = asyncio.get_event_loop()
            fut = loop.run_in_executor(None, lambda: socket.create_connection((ip, port), timeout))
            conn = await asyncio.wait_for(fut, timeout)
            conn.close()
            return "Панель доступна"
        except Exception:
            pass

    return f"Панель в сети, но недоступны порты {ports}"