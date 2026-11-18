def print_qr(text):
    N = 25
    grid = [[0 for _ in range(N)] for _ in range(N)]
    func = [[False for _ in range(N)] for _ in range(N)]

    def set_mod(x, y, v, is_f=True):
        if 0 <= x < N and 0 <= y < N:
            grid[y][x] = 1 if v else 0
            if is_f: func[y][x] = True

    for fx, fy in [(0, 0), (N - 7, 0), (0, N - 7)]:
        for dy in range(-1, 8):
            for dx in range(-1, 8):
                on = (0 <= dx <= 6 and 0 <= dy <= 6) and (dx in (0, 6) or dy in (0, 6) or (2 <= dx <= 4 and 2 <= dy <= 4))
                set_mod(fx + dx, fy + dy, on, True)

    for dy in range(-2, 3):
        for dx in range(-2, 3):
            set_mod(18 + dx, 18 + dy, abs(dx) == 2 or abs(dy) == 2 or (dx == 0 and dy == 0), True)

    for i in range(8, N - 8):
        set_mod(i, 6, i % 2 == 0, True)
        set_mod(6, i, i % 2 == 0, True)
    set_mod(8, N - 8, 1, True)

    for i in range(9):
        if i != 6:
            func[8][i] = True
            func[i][8] = True
    for i in range(8):
        func[8][N - 1 - i] = True
        func[N - 1 - i][8] = True

    payload = text.encode("utf-8")[:31]
    bits = []
    def push(val, ln):
        for b in range(ln - 1, -1, -1): bits.append((val >> b) & 1)
    push(0b0100, 4)
    push(len(payload), 8)
    for c in payload: push(c, 8)
    push(0, 4)
    while len(bits) % 8 != 0: push(0, 1)
    cw = [sum(bits[i + j] << (7 - j) for j in range(8)) for i in range(0, len(bits), 8)]
    pad = [0xEC, 0x11]
    while len(cw) < 34: cw.append(pad[len(cw) % 2])

    gen = [1, 216, 194, 159, 111, 199, 94, 95, 113, 157, 193]
    def gf_mul(a, b):
        r = 0
        for _ in range(8):
            if b & 1: r ^= a
            hi = a & 0x80
            a = (a << 1) & 0xFF
            if hi: a ^= 0x1D
            b >>= 1
        return r

    ecc = [0] * 10
    for b in cw:
        f = b ^ ecc.pop(0)
        ecc.append(0)
        for j in range(10): ecc[j] ^= gf_mul(gen[j + 1], f)
    cw.extend(ecc)

    all_bits = [(b >> (7 - j)) & 1 for b in cw for j in range(8)]
    bi, direction, y = 0, -1, N - 1
    x = N - 1
    while x > 0:
        if x == 6: x -= 1
        while 0 <= y < N:
            for dx in range(2):
                cx = x - dx
                if not func[y][cx]:
                    bit = all_bits[bi] if bi < len(all_bits) else 0
                    bi += 1
                    if (cx + y) % 2 == 0: bit ^= 1
                    grid[y][cx] = bit
            y += direction
        direction = -direction
        y += direction
        x -= 2

    fmt = 0x77C4
    for i in range(6): set_mod(8, i, (fmt >> i) & 1, False)
    set_mod(8, 7, (fmt >> 6) & 1, False)
    set_mod(8, 8, (fmt >> 7) & 1, False)
    set_mod(7, 8, (fmt >> 8) & 1, False)
    for i in range(9, 15): set_mod(14 - i, 8, (fmt >> i) & 1, False)
    for i in range(8): set_mod(N - 1 - i, 8, (fmt >> i) & 1, False)
    for i in range(8, 15): set_mod(8, N - 15 + i, (fmt >> i) & 1, False)

    quiet = [[0 for _ in range(N + 4)] for _ in range(N + 4)]
    for r in range(N):
        for c in range(N): quiet[r + 2][c + 2] = grid[r][c]

    print()
    for r in range(0, len(quiet), 2):
        line = ""
        for c in range(len(quiet)):
            top = quiet[r][c]
            bot = quiet[r + 1][c] if r + 1 < len(quiet) else 0
            line += "█" if (top and bot) else ("▀" if top else ("▄" if bot else " "))
        print("  " + line)
    print(f"  QR Payload: {text}\n")

if __name__ == "__main__":
    name = input("Enter Mac Name for QR: ").strip() or "MacTest"
    print_qr(f"2DSMSG:{name}")
