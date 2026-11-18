import socket, threading, time, struct, readline
from make_qr import print_qr

BROKERS = ["broker.emqx.io", "://hivemq.com", "test.mosquitto.org"]

def rem_len(n):
    out = bytearray()
    while True:
        b = n % 128
        n //= 128
        if n > 0: b |= 0x80
        out.append(b)
        if n == 0: break
    return bytes(out)

def enc_str(s):
    b = s.encode("utf-8")
    return struct.pack(">H", len(b)) + b

def connect_mqtt(host, cid):
    s = socket.create_connection((host, 1883), timeout=5)
    body = b"\x00\x04MQTT\x04\x02\x00\x3C" + enc_str(cid)
    s.sendall(b"\x10" + rem_len(len(body)) + body)
    ack = s.recv(4)
    if len(ack) < 4 or ack != b"\x20\x02\x00\x00":
        s.close()
        raise RuntimeError(f"CONNACK rejected: {ack!r}")
    return s

def mqtt_sub(sock, topic, pid=1):
    body = struct.pack(">H", pid) + enc_str(topic) + b"\x00"
    sock.sendall(b"\x82" + rem_len(len(body)) + body)

def mqtt_pub(sock, topic, payload):
    body = enc_str(topic) + payload
    sock.sendall(b"\x30" + rem_len(len(body)) + body)

my_name = input("Your Mac Name (e.g. MacTest): ").strip() or "MacTest"
target_2ds = input("Your 2DS Mii Name (exact spelling): ").strip() or "Player"
pref = input("Broker on 2DS screen (press Enter for broker.emqx.io): ").strip()
if pref:
    BROKERS = [pref] + [b for b in BROKERS if b != pref]

print_qr(f"2DSMSG:{my_name}")

sock = None
active_host = ""
for host in BROKERS:
    try:
        sock = connect_mqtt(host, f"mac{int(time.time()) & 0xFFFFF}")
        active_host = host
        print(f"[OK] Connected to {host}!")
        break
    except Exception as e:
        print(f"[Skip] {host}: {e}")

if not sock:
    print("Could not connect to any broker.")
    exit(1)

mqtt_sub(sock, "2ds_imsg_v1/community", 1)
mqtt_sub(sock, f"2ds_imsg_v1/dm/{my_name}", 2)
seen_users = set()

def announce_loop():
    name_bytes = my_name.encode("utf-8")[:31].ljust(32, b"\x00")
    mii_bytes = b"\x03" + (b"\x00" * 95)
    ann_payload = name_bytes + mii_bytes
    while True:
        try:
            mqtt_pub(sock, "2ds_imsg_v1/community", ann_payload)
            sock.sendall(b"\xC0\x00")
        except Exception:
            break
        time.sleep(8)

def recv_loop():
    buf = bytearray()
    while True:
        try:
            chunk = sock.recv(4096)
            if not chunk: break
            buf.extend(chunk)
            while len(buf) >= 2:
                hdr = buf.pop(0)
                mult, rlen = 1, 0
                while True:
                    if not buf: break
                    b = buf.pop(0)
                    rlen += (b & 127) * mult
                    if (b & 128) == 0: break
                    mult *= 128
                while len(buf) < rlen:
                    more = sock.recv(4096)
                    if not more: break
                    buf.extend(more)
                body = bytes(buf[:rlen])
                del buf[:rlen]
                if (hdr & 0xF0) == 0x30 and len(body) >= 2:
                    (tlen,) = struct.unpack(">H", body[:2])
                    topic = body[2:2+tlen].decode("utf-8", errors="ignore")
                    pay = body[2+tlen:]
                    if topic == "2ds_imsg_v1/community" and len(pay) >= 32:
                        who = pay[:32].split(b"\x00", 1).pop(0).decode("utf-8", errors="ignore")
                        if who and who != my_name and who not in seen_users:
                            seen_users.add(who)
                            print(f"\r\033[K[Online] {who}\n> {readline.get_line_buffer()}", end="", flush=True)
                    elif topic == f"2ds_imsg_v1/dm/{my_name}" and len(pay) > 32:
                        who = pay[:32].split(b"\x00", 1).pop(0).decode("utf-8", errors="ignore")
                        txt = pay[32:].decode("utf-8", errors="ignore")
                        print(f"\r\033[K[2DS -> Mac] {who}: {txt}\n> {readline.get_line_buffer()}", end="", flush=True)
        except Exception:
            break

threading.Thread(target=announce_loop, daemon=True).start()
threading.Thread(target=recv_loop, daemon=True).start()

print(f"\nReady on {active_host}! Type a message and press Enter:")
while True:
    msg = input("> ").strip()
    if not msg: continue
    pkt = my_name.encode("utf-8")[:31].ljust(32, b"\x00") + msg.encode("utf-8")
    mqtt_pub(sock, f"2ds_imsg_v1/dm/{target_2ds}", pkt)
    print(f"[Sent -> {target_2ds}] {msg}")
