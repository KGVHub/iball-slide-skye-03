#!/usr/bin/env python3
"""Minimal Spreadtrum download-mode client for the SPRD U2S COM port (Windows).

Port of the parts of tools/spd_dump (common.c, spd_dump.c) needed to load
FDL1/FDL2 and write one small partition, then reset. Framing, CRC16 and
checksum follow common.c exactly.
usage: spd_misc_win.py COMx fdl1 fdl2 partition image
"""
import struct
import sys
import time

import serial

HDLC = 0x7E
ESC = 0x7D
CONNECT, START, MIDST, END, EXEC, RESET = 0x00, 0x01, 0x02, 0x03, 0x04, 0x05
KEEP_CHARGE, DISABLE_TRANSCODE = 0x13, 0x21
REP_ACK, REP_VER, REP_INCOMPAT = 0x80, 0x81, 0x96


def crc16(data):
    crc = 0
    for b in data:
        crc ^= b << 8
        for _ in range(8):
            crc = (crc << 1) ^ (0x11021 if crc & 0x8000 else 0)
    return crc & 0xFFFF


def checksum(data, final):
    crc, n = 0, len(data)
    for i in range(0, n - 1, 2):
        crc += data[i + 1] << 8 | data[i]
    if n & 1:
        crc += data[-1]
    crc = (crc >> 16) + (crc & 0xFFFF)
    crc += crc >> 16
    crc = ~crc & 0xFFFF
    if (n & 1) < final:
        crc = (crc >> 8) | ((crc & 0xFF) << 8)
    return crc


class Spd:
    def __init__(self, port):
        self.s = serial.Serial(port, 115200, timeout=1)
        self.crc = True
        self.transcode = True

    def send(self, typ, data=b''):
        raw = struct.pack('>HH', typ, len(data)) + data
        chk = crc16(raw) if self.crc else checksum(raw, 1)
        raw += struct.pack('>H', chk)
        if self.transcode:
            body = bytearray()
            for b in raw:
                if b in (HDLC, ESC):
                    body += bytes((ESC, b ^ 0x20))
                else:
                    body.append(b)
        else:
            body = raw
        self.s.write(bytes((HDLC,)) + bytes(body) + bytes((HDLC,)))

    def recv(self, timeout=3):
        end = time.time() + timeout
        buf, started, esc = bytearray(), False, False
        while time.time() < end:
            c = self.s.read(1)
            if not c:
                continue
            b = c[0]
            if b == HDLC:
                if not started:
                    started = True
                    continue
                if not buf:
                    continue
                break
            if not started:
                continue
            if self.transcode and b == ESC:
                esc = True
                continue
            buf.append(b ^ 0x20 if esc else b)
            esc = False
            if not self.transcode and len(buf) >= 4 and len(buf) == struct.unpack('>H', buf[2:4])[0] + 6:
                c = self.s.read(1)
                break
        else:
            return None
        if len(buf) < 6:
            return None
        body, chk = bytes(buf[:-2]), struct.unpack('>H', buf[-2:])[0]
        want = crc16(body) if self.crc else checksum(body, 2)
        if chk != want:
            raise SystemExit(f'bad checksum 0x{chk:04x}, expected 0x{want:04x}')
        return struct.unpack('>H', body[:2])[0], body[4:]

    def cmd(self, typ, data=b'', timeout=3, ok=(REP_ACK,)):
        self.send(typ, data)
        r = self.recv(timeout)
        if r is None:
            self.send(typ, data)
            r = self.recv(timeout)
        if r is None:
            raise SystemExit(f'timeout on command 0x{typ:02x}')
        if r[0] not in ok:
            raise SystemExit(f'command 0x{typ:02x}: unexpected reply 0x{r[0]:04x}')
        return r

    def check_baud(self, tries=3):
        for _ in range(tries):
            self.s.write(bytes((HDLC,)))
            r = self.recv(2)
            if r and r[0] == REP_VER:
                return r[1]
            time.sleep(0.5)
        raise SystemExit('no CHECK_BAUD reply: wrong mode, re-enter download mode')

    def send_file(self, data, addr, step=528):
        self.cmd(START, struct.pack('>II', addr, len(data)))
        for i in range(0, len(data), step):
            self.cmd(MIDST, data[i:i + step])
        self.cmd(END)


def main():
    port, fdl1, fdl2, part, img = sys.argv[1:6]
    d = Spd(port)
    print('bootrom:', d.check_baud().rstrip(b'\0').decode(errors='replace'))
    d.cmd(CONNECT)
    d.send_file(open(fdl1, 'rb').read(), 0x50002E00)
    d.cmd(EXEC)
    print('FDL1 sent and started')
    d.crc = False
    time.sleep(0.5)
    print('fdl1:', d.check_baud().rstrip(b'\0').decode(errors='replace'))
    d.cmd(CONNECT)
    try:
        d.cmd(KEEP_CHARGE)
    except SystemExit:
        pass
    d.send_file(open(fdl2, 'rb').read(), 0x9EFFFE00)
    typ, info = d.cmd(EXEC, timeout=15, ok=(REP_ACK, REP_INCOMPAT))
    print('FDL2 started')
    disable_hdlc = False
    if typ == REP_INCOMPAT and len(info) >= 4:
        if info[:4] == b'newt':
            pos = 4
            while pos + 4 <= len(info):
                tag, ln = struct.unpack('<HH', info[pos:pos + 4])
                pos += 4
                if tag == 0:
                    disable_hdlc = struct.unpack('<I', info[pos:pos + 4])[0] != 0
                pos += ln
        else:
            disable_hdlc = struct.unpack('<I', info[:4])[0] != 0
    if disable_hdlc:
        d.cmd(DISABLE_TRANSCODE)
        d.transcode = False
        print('transcode disabled')
    data = open(img, 'rb').read()
    name = part.encode('utf-16-le').ljust(72, b'\0')
    d.cmd(START, name + struct.pack('<I', len(data)))
    for i in range(0, len(data), 0x1000):
        d.cmd(MIDST, data[i:i + 0x1000], timeout=15)
    d.cmd(END, timeout=15)
    print(f'wrote {len(data)} bytes to {part}')
    d.cmd(RESET)
    print('reset sent')


if __name__ == '__main__':
    main()
