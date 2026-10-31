#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) Copyright 2026 - MateAG
# All rights reserved. Any copy without
# consent of this code will be reported.
#

import base64
import math
import os
import random
import re
import string
import subprocess
import sys
import threading
import time
import traceback

import tkinter as tk
from tkinter import filedialog, messagebox

import customtkinter as ctk

BG = "#060608"
PANEL = "#0a0a0c"
CARD = "#0c0c0f"
ROW = "#0e0e11"
ROW_HOVER = "#17171b"
ROW_SEL = "#161d0a"
HAIR = "#151519"
FG = "#f0f0f3"
FG_SOFT = "#b7b7be"
DIM = "#8b8b94"
DIM2 = "#565660"
ERR = "#ff5f6d"
OK = "#5fe08c"
WARN = "#ffc857"

ACC = "#c8ff2e"
ACC_HOT = "#ffd23f"
ACC_DIM = "#5c7a17"
ACC_DIM_DARK = "#3f5510"

UI_STACK = ("Segoe UI Variable Text", "Segoe UI", "Inter", "Poppins", "Helvetica Neue", "Arial")
MONO_STACK = ("Cascadia Mono", "Consolas", "JetBrains Mono", "Courier New")

MAXBYTES = 6 * 1024 * 1024
VERSION = "3.2"

BANNER = [
    ""
]


class DeobError(Exception):
    pass


def header(ext):
    if ext == ".ps1":
        return ["#" + b[2:] if b.startswith("::") else "#" + b for b in BANNER] + [""]
    return BANNER + ["", "@echo off", "title Ofuscating...",
                     "for /f %%i in (\"certutil.exe\") do if not exist \"%%~$path:i\" (",
                     "  echo CertUtil was not found!",
                     "  pause",
                     "  exit /b",
                     ")", ""]


def b64e(b):
    return base64.b64encode(b).decode()


def b64d(s):
    s = s.replace("-", "+").replace("_", "/")
    s = re.sub(r"[^A-Za-z0-9+/=]", "", s)
    s += "=" * (-len(s) % 4)
    return base64.b64decode(s)


def rname(n=8):
    pool = string.ascii_lowercase + string.digits
    return random.choice(string.ascii_lowercase) + "".join(
        random.choice(pool) for _ in range(max(0, n - 1)))


def rlabel():
    return "".join(random.choice(string.ascii_letters) for _ in range(random.randint(9, 16)))


def rcase(word):
    return "".join(c.upper() if random.random() < 0.5 else c.lower() for c in word)


def printable_ratio(b):
    if not b:
        return 0.0
    ok = sum(1 for c in b if c in (9, 10, 13) or 32 <= c < 127)
    return ok / len(b)


def normalize_text(b):
    if len(b) >= 4 and b.count(b"\x00") > len(b) // 4:
        try:
            return b.decode("utf-16le")
        except UnicodeDecodeError:
            pass
    try:
        return b.decode("utf-8-sig")
    except UnicodeDecodeError:
        return b.decode("latin-1")


def _flat(c):
    if isinstance(c, (tuple, list)):
        return c[1] if len(c) > 1 else c[0]
    return c


def lerp_hex(c1, c2, t):
    c1, c2 = _flat(c1), _flat(c2)
    if not isinstance(c1, str) or len(c1) < 7 or not c1.startswith("#"):
        return c2
    if not isinstance(c2, str) or len(c2) < 7 or not c2.startswith("#"):
        return c1
    a = tuple(int(c1[i:i + 2], 16) for i in (1, 3, 5))
    b = tuple(int(c2[i:i + 2], 16) for i in (1, 3, 5))
    return "#" + "".join("%02x" % int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


def dim_of(color, amount=0.5):
    return lerp_hex(color, BG, amount)


_ECHO_ESC = (("^", "^^"), ("&", "^&"), ("|", "^|"), ("<", "^<"), (">", "^>"), ("(", "^("), (")", "^)"))

_UNESC = re.compile(r"\^(.)")


def _echo_escape(s):
    s = s.replace("%", "%%")
    for a, b in _ECHO_ESC:
        s = s.replace(a, b)
    return s


def _echo_unescape(s):
    return _UNESC.sub(lambda m: m.group(1), s).replace("%%", "%")


def _ps_write_bat():
    return ("$f=Join-Path $env:TEMP ('o_' + [guid]::NewGuid().ToString('N') + '.bat');"
            "[IO.File]::WriteAllBytes($f,$b);Start-Process $f")


_AES_IMPL = None


def aes_impl():
    global _AES_IMPL
    if _AES_IMPL is not None:
        return _AES_IMPL
    try:
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        _AES_IMPL = ("cryptography", Cipher, algorithms, modes)
        return _AES_IMPL
    except Exception:
        pass
    try:
        from Crypto.Cipher import AES
        _AES_IMPL = ("pycryptodome", AES, None, None)
        return _AES_IMPL
    except Exception:
        pass
    _AES_IMPL = (None, None, None, None)
    return _AES_IMPL


def aes_available():
    return aes_impl()[0] is not None


def _pkcs7(data):
    pad = 16 - (len(data) % 16)
    return data + bytes([pad]) * pad


def aes_encrypt(key, iv, data):
    impl, Cipher, algorithms, modes = aes_impl()
    data = _pkcs7(data)
    if impl == "cryptography":
        enc = Cipher(algorithms.AES(key), modes.CBC(iv)).encryptor()
        return enc.update(data) + enc.finalize()
    return Cipher.new(key, Cipher.MODE_CBC, iv).encrypt(data)


def aes_decrypt(key, iv, data):
    impl, Cipher, algorithms, modes = aes_impl()
    if impl == "cryptography":
        dec = Cipher(algorithms.AES(key), modes.CBC(iv)).decryptor()
        out = dec.update(data) + dec.finalize()
    else:
        out = Cipher.new(key, Cipher.MODE_CBC, iv).decrypt(data)
    if out:
        pad = out[-1]
        if 1 <= pad <= 16 and out[-pad:] == bytes([pad]) * pad:
            out = out[:-pad]
    return out


def aes_try_keys(raw, candidates):
    if len(raw) < 32:
        return None
    iv, ct = raw[:16], raw[16:]
    for key in candidates:
        if len(key) not in (16, 24, 32):
            continue
        try:
            out = aes_decrypt(key, iv, ct)
        except Exception:
            continue
        if printable_ratio(out) > 0.85:
            return out
    return None


WORDS = ("alpha bravo delta sigma vector quartz harbor lantern cobalt marble nectar "
         "orbit piston quarry ripple sable timber umber velvet willow xenon yacht zephyr "
         "anchor beacon cinder dagger ember fathom granite hollow indigo juniper kettle "
         "ledger meadow nickel orchard pepper raven saddle tundra upland vapour wallet").split()


def decoy_echo():
    return rcase("echo") + " " + " ".join(random.sample(WORDS, 3)) + " 2>nul"


def decoy_rem():
    w = random.sample(WORDS, 2)
    tail = "".join(random.choice("[]{}_Sfk") for _ in range(random.randint(2, 6)))
    return rcase("rem") + " " + "".join(w) + tail


def noise_block(n=3):
    out = []
    for _ in range(n):
        r = random.random()
        if r < 0.45:
            out.append(decoy_rem())
        elif r < 0.85:
            out.append(decoy_echo())
        else:
            out.append(rname() + " 2>nul")
    return out


def errorlevel_noise():
    return ("if %erRoRLeVeL% geq " + str(random.randint(0, 2)) + " " + rcase("echo") + " "
            + random.choice(WORDS) + " 2>nul && " + rcase("rem") + " " + random.choice(WORDS))


def _runner(ext):
    if ext == ".ps1":
        return ("Start-Process powershell -WindowStyle Hidden -ArgumentList "
                "'-nop','-ep','bypass','-w','hidden','-f','%F%'")
    return "Start-Process '%F%'"


def _shard_writer(out, blob, sep, ext):
    tag = rname(6)
    chunks = [blob[i:i + 60] for i in range(0, len(blob), 60)]
    out += [rcase("setlocal"),
            "set \"B=%%TEMP%%\\b_%s.b64\"" % tag,
            "set \"F=%%TEMP%%\\o_%s.%s\"" % (tag, ext.lstrip(".")),
            ">\"%B%\" " + rcase("echo") + "."]
    for i in range(0, len(chunks), 6):
        n = rname(10)
        out.append(rcase("set") + " \"" + n + "=" + sep + sep.join(chunks[i:i + 6]) + "\"")
        out.append(">>\"%B%\" " + rcase("echo") + " %" + n + (":\\=%" if sep else "%"))
        if random.random() < 0.3:
            out.extend(noise_block(1))


def obf_aes(text, ext):
    if not aes_available():
        raise DeobError("no AES backend available")
    key = os.urandom(32)
    iv = os.urandom(16)
    blob = b64e(iv + aes_encrypt(key, iv, text.encode("utf-8")))
    key_b64 = b64e(key)
    chunks = [blob[i:i + 76] for i in range(0, len(blob), 76)]
    out = header(ext)
    if ext == ".ps1":
        out.extend("#" + c for c in chunks)
        out.append("#++++")
        out.append("# " + rlabel())
        out.append((
            "$P=$PSCommandPath\n"
            "if(-not $P){$P=$MyInvocation.MyCommand.Path}\n"
            "$T=[IO.File]::ReadAllText($P)\n"
            "$B=((($T -split '\\r?\\n') | ?{$_ -match '^#[A-Za-z0-9+/=]+$'}) -replace '^#','') -join ''\n"
            "$R=[Convert]::FromBase64String($B)\n"
            "$K=[Convert]::FromBase64String('@KEY@')\n"
            "$A=[Security.Cryptography.Aes]::Create()\n"
            "$A.Mode='CBC'\n$A.Padding='PKCS7'\n$A.Key=$K\n$A.IV=$R[0..15]\n"
            "$D=$A.CreateDecryptor()\n"
            "$X=$D.TransformFinalBlock($R,16,$R.Length-16)\n"
            "iex([Text.Encoding]::UTF8.GetString($X))\n"
        ).replace("@KEY@", key_b64))
    else:
        out.extend("::" + c for c in chunks)
        out.append("::++++")
        out.append((
            "powershell -nop -w hidden -ep bypass -c \""
            "$p='%~f0';"
            "$t=[IO.File]::ReadAllText($p);"
            "$b=((($t -split '\\r?\\n') | ?{$_ -match '^::[A-Za-z0-9+/=]+$'}) -replace '^::','') -join '';"
            "$r=[Convert]::FromBase64String($b);"
            "$k=[Convert]::FromBase64String('@KEY@');"
            "$a=[Security.Cryptography.Aes]::Create();"
            "$a.Mode='CBC';$a.Padding='PKCS7';$a.Key=$k;$a.IV=$r[0..15];"
            "$d=$a.CreateDecryptor();"
            "$x=$d.TransformFinalBlock($r,16,$r.Length-16);"
            "$f=Join-Path $env:TEMP ('o_' + [guid]::NewGuid().ToString('N') + '.bat');"
            "[IO.File]::WriteAllBytes($f,$x);"
            "Start-Process $f\""
        ).replace("@KEY@", key_b64))
    return "\n".join(out)


def obf_pathshards(text, ext):
    out = header(ext)
    _shard_writer(out, b64e(text.encode("utf-8")), "\\", ext)
    out.append("powershell -nop -w hidden -ep bypass -c \""
               "$b=[Convert]::FromBase64String((Get-Content -Raw '%B%'));"
               "[IO.File]::WriteAllBytes('%F%',$b);" + _runner(ext) + "\"")
    return "\n".join(out)


def obf_varind(text, ext):
    label = rlabel()
    tag = rname(6)
    table = []
    body = []
    for line in text.split("\n"):
        if not line:
            body.append("")
            continue
        esc = _echo_escape(line)
        pos = 0
        tokens = []
        while pos < len(esc):
            nm = rname(random.randint(7, 11))
            chunk = esc[pos:pos + random.randint(6, 15)]
            table.append((nm, chunk))
            tokens.append("%" + nm + "%")
            pos += len(chunk)
        body.append("".join(tokens))

    out = header(ext) + ["set \"F=%%TEMP%%\\o_%s.%s\"" % (tag, ext.lstrip(".")),
                         ">\"%F%\" " + rcase("echo") + "(",
                         rcase("goto") + " :" + label]
    for nm, ch in table:
        out.append(rcase("set") + " \"" + nm + "=" + ch + "\"")
        if random.random() < 0.12:
            out.append(noise_block(1)[0])
    out.append(":" + label)
    out.append(errorlevel_noise())
    for b in body:
        out.append(">>\"%F%\" " + rcase("echo") + "(" + b)
    out.append(rcase("call") + " \"%F%\" %*")
    return "\n".join(out)


def obf_certutil(text, ext):
    tag = rname(6)
    blob = b64e(text.encode("utf-8"))
    chunks = [blob[i:i + 64] for i in range(0, len(blob), 64)]
    block = ["-----BEGIN CERTIFICATE-----"] + chunks + ["-----END CERTIFICATE-----"]
    out = header(ext)
    if ext == ".ps1":
        out = ["<#"] + block + ["#>"] + header(ext) + [
            "$f=Join-Path $env:TEMP 'o_%s.ps1'" % tag,
            "certutil -decode $PSCommandPath $f | Out-Null",
            "powershell -nop -ep bypass -w hidden -f $f"]
        return "\n".join(out)
    out += ["set \"F=%%TEMP%%\\o_%s.%s\"" % (tag, ext.lstrip(".")),
            "certutil -f -decode \"%~f0\" \"%F%\" >nul 2>&1",
            "call \"%F%\" %*",
            "exit /b"]
    return "\n".join(out + block)


def obf_encodedcommand(text, ext):
    enc = b64e(text.encode("utf-16le"))
    out = header(ext) + ["$c=[Convert]::FromBase64String('" + enc + "')",
                         "$t=[Text.Encoding]::Unicode.GetString($c)"]
    if ext == ".ps1":
        out.append("iex($t)")
    else:
        out.append("$b=[Text.Encoding]::UTF8.GetBytes($t)")
        out.append(_ps_write_bat())
    out.append("")
    return "\n".join(out)


def obf_charcode(text, ext):
    codes = ",".join(str(b) for b in text.encode("utf-8"))
    out = header(ext) + ["$b=[byte[]]@(" + codes + ")"]
    out.append("iex([Text.Encoding]::UTF8.GetString($b))" if ext == ".ps1" else _ps_write_bat())
    out.append("")
    return "\n".join(out)


def obf_xor(text, ext):
    key = random.randint(11, 240)
    out = header(ext)
    _shard_writer(out, b64e(bytes(b ^ key for b in text.encode("utf-8"))), "", ext)
    out.append("powershell -nop -w hidden -ep bypass -c \""
               "$b=[Convert]::FromBase64String((Get-Content -Raw '%B%'));"
               "$k=0x" + format(key, "02X") + ";"
               "for($i=0;$i -lt $b.Length;$i++){$b[$i]=$b[$i] -bxor $k};"
               "[IO.File]::WriteAllBytes('%F%',$b);" + _runner(ext) + "\"")
    return "\n".join(out)


def obf_plain(text, ext):
    out = header(ext)
    _shard_writer(out, b64e(text.encode("utf-8")), "", ext)
    out.append("powershell -nop -w hidden -ep bypass -c \""
               "$b=[Convert]::FromBase64String((Get-Content -Raw '%B%'));"
               "[IO.File]::WriteAllBytes('%F%',$b);" + _runner(ext) + "\"")
    return "\n".join(out)


def _collect_chunks(text):
    table = {}
    for m in re.finditer(r"(?im)^\s*s(?:e)?t\s+\"?([A-Za-z0-9_]+)=([A-Za-z0-9+/=]+)\"?\s*$", text):
        table[m.group(1)] = m.group(2)
    if not table:
        return None
    order = [table[m.group(1)] for m in
             re.finditer(r"(?im)^.*?echo\s+%([A-Za-z0-9_]+)%", text) if m.group(1) in table]
    return "".join(order) or None


def _key_candidates(text):
    out = []
    pats = (r"FromBase64String\(\s*'([A-Za-z0-9+/=]{16,})'\s*\)",
            r"(?im)^\s*\$?\w*(?:key|k)\w*\s*=\s*['\"]([A-Za-z0-9+/=]{16,})['\"]",
            r"['\"]([A-Za-z0-9+/=]{16,})['\"]")
    for p in pats:
        for m in re.finditer(p, text):
            try:
                k = b64d(m.group(1))
            except Exception:
                continue
            if len(k) in (16, 24, 32):
                out.append(k)
    return out


def deob_aes(text, ext):
    marker = re.search(r"\+{4,}A?", text)
    if not marker:
        raise DeobError("no ++++ separator found")
    keys = _key_candidates(text)
    if not keys:
        raise DeobError("no key material found")
    for part in (text[:marker.start()], text[marker.end():]):
        clean = []
        for line in part.splitlines():
            s = re.sub(r"(?i)^\s*(::|#|rem\b|'')\s*", "", line).strip()
            if re.fullmatch(r"[A-Za-z0-9+/=]{40,}", s):
                clean.append(s)
        blob = "".join(clean)
        if len(blob) < 40:
            continue
        try:
            raw = b64d(blob)
        except Exception:
            continue
        out = aes_try_keys(raw, keys)
        if out:
            return normalize_text(out)
    raise DeobError("AES decrypt failed")


def deob_varind(text, ext):
    lines = text.split("\n")
    start = 0
    for i, line in enumerate(lines):
        if re.match(r"(?i)^\s*goto\s+:", line):
            start = i + 1
            break
    table = {}
    for m in re.finditer(r"(?im)^\s*s(?:e)?t\s+\"?([A-Za-z0-9_]+)=(.*?)\"?\s*$", text):
        table[m.group(1)] = m.group(2)
    if len(table) < 4:
        raise DeobError("indirection table too small")
    pat = re.compile(r"%([A-Za-z0-9_]+)%")
    body = re.compile(r"(?i)^\s*>>\s*\"[^\"]*\"\s*echo\(")

    def expand(line, depth=8):
        for _ in range(depth):
            new = pat.sub(lambda m: table.get(m.group(1), m.group(0)), line)
            if new == line:
                break
            line = new
        return line

    out = []
    for line in lines[start:]:
        if not body.match(line):
            continue
        payload = body.sub("", line)
        if not pat.findall(payload):
            out.append("")
            continue
        out.append(_echo_unescape(expand(payload)))
    result = "\n".join(out)
    if len(result.strip()) < 8:
        raise DeobError("expansion produced nothing")
    return result


def deob_pathshards(text, ext):
    table = {}
    for m in re.finditer(r"(?im)^\s*s(?:e)?t\s+\"?([A-Za-z0-9_]+)=(\\[^\"\r\n]*)\"?\s*$", text):
        table[m.group(1)] = m.group(2)
    if not table:
        raise DeobError("no path shards found")
    pieces = [table[m.group(1)].replace("\\", "") for m in
              re.finditer(r"(?im)^.*?echo\s+%([A-Za-z0-9_]+)(?::\\=)?%", text)
              if m.group(1) in table]
    if not pieces:
        raise DeobError("no shard writes found")
    blob = "".join(pieces)
    if len(blob) < 40:
        raise DeobError("reassembled blob too short")
    try:
        return normalize_text(b64d(blob))
    except Exception as exc:
        raise DeobError("base64 decode failed: " + str(exc))


def deob_certutil(text, ext):
    m = re.search(r"-----BEGIN CERTIFICATE-----(.*?)-----END CERTIFICATE-----", text, re.S)
    if not m:
        raise DeobError("no certificate block found")
    try:
        return normalize_text(b64d(m.group(1)))
    except Exception as exc:
        raise DeobError("base64 decode failed: " + str(exc))


def deob_encodedcommand(text, ext):
    m = re.search(r"(?:-e|-enc|-encodedcommand)\s+\"?([A-Za-z0-9+/=]{40,})", text, re.I)
    if m:
        try:
            return normalize_text(b64d(m.group(1)))
        except Exception as exc:
            raise DeobError("base64 decode failed: " + str(exc))
    m = re.search(r"FromBase64String\(\s*'([A-Za-z0-9+/=]{40,})'\s*\)", text)
    if not m:
        raise DeobError("no -EncodedCommand payload found")
    try:
        return b64d(m.group(1)).decode("utf-16le", "replace")
    except Exception as exc:
        raise DeobError("base64 decode failed: " + str(exc))


def deob_xor(text, ext):
    m = re.search(r"0x([0-9A-Fa-f]{1,2})", text)
    if not m:
        raise DeobError("no xor key found")
    key = int(m.group(1), 16)
    blob = _collect_chunks(text)
    if not blob:
        cands = re.findall(r"['\"]([A-Za-z0-9+/=]{60,})['\"]", text)
        blob = cands[0] if cands else None
    if not blob:
        raise DeobError("no xor blob found")
    try:
        data = b64d(blob)
    except Exception as exc:
        raise DeobError("base64 decode failed: " + str(exc))
    for k in [key] + [k for k in range(1, 256) if k != key]:
        out = bytes(b ^ k for b in data)
        if printable_ratio(out) > 0.92:
            return normalize_text(out)
    raise DeobError("xor brute force failed")


def deob_plain(text, ext):
    best = None
    blob = _collect_chunks(text)
    if blob:
        try:
            raw = b64d(blob)
            if printable_ratio(raw) >= 0.85:
                best = raw
        except Exception:
            pass
    if best is None:
        for m in re.finditer(r"[A-Za-z0-9+/=]{200,}", text):
            try:
                raw = b64d(m.group(0))
            except Exception:
                continue
            if printable_ratio(raw) < 0.85:
                continue
            if best is None or len(raw) > len(best):
                best = raw
    if not best:
        raise DeobError("no printable base64 blob found")
    return normalize_text(best)


def deob_charcode(text, ext):
    m = re.search(r"@\(([\d,]{40,})\)", text)
    if not m:
        raise DeobError("no char code array found")
    try:
        raw = bytes(int(x) for x in m.group(1).split(",") if x)
    except ValueError as exc:
        raise DeobError(str(exc))
    return normalize_text(raw)


METHODS = [
    {"key": "aes", "label": "AES-256-CBC self-read stub", "strength": 5,
     "desc": "Payload encrypted with AES-256-CBC/PKCS7 inside a comment block, split by "
             "++++ from a stub that reads its own file, derives the IV and key from base64 "
             "and decrypts in memory.",
     "targets": {".bat", ".cmd", ".ps1"}, "obf": obf_aes, "deob": deob_aes, "needs_aes": True},
    {"key": "pathshards", "label": "Path shard reassembly", "strength": 4,
     "desc": "Base64 payload split into fake \\directory\\segments held in random variables, "
             "rebuilt through concatenation and flushed to a temporary .b64 with the "
             "backslashes stripped before decoding.",
     "targets": {".bat", ".cmd", ".ps1"}, "obf": obf_pathshards, "deob": deob_pathshards},
    {"key": "varind", "label": "Variable indirection + decoys", "strength": 4,
     "desc": "Source split into shards inside randomly named variables and written line by "
             "line into a temporary batch through echo redirection, wrapped in random labels, "
             "case-mangled keywords and REM/ECHO filler, then called.",
     "targets": {".bat", ".cmd"}, "obf": obf_varind, "deob": deob_varind},
    {"key": "certutil", "label": "certutil polyglot", "strength": 3,
     "desc": "Payload base64 inside a fake CERTIFICATE block at the end of the file, "
             "extracted and decoded at runtime with certutil -decode, then called.",
     "targets": {".bat", ".cmd", ".ps1"}, "obf": obf_certutil, "deob": deob_certutil},
    {"key": "encodedcommand", "label": "PowerShell -EncodedCommand", "strength": 2,
     "desc": "Payload as base64 UTF-16LE. On a ps1 payload it is invoked with iex, on a "
             "batch payload it is written to temp and started. No artifacts left behind.",
     "targets": {".bat", ".cmd", ".ps1"}, "obf": obf_encodedcommand,
     "deob": deob_encodedcommand, "out_ext": ".ps1"},
    {"key": "charcode", "label": "Character code array", "strength": 2,
     "desc": "Every byte of the payload as a decimal array, rebuilt with byte[] and UTF8 then "
             "invoked. Readable structure, weak protection.",
     "targets": {".bat", ".cmd", ".ps1"}, "obf": obf_charcode,
     "deob": deob_charcode, "out_ext": ".ps1"},
    {"key": "xor", "label": "Single byte XOR + eval", "strength": 2,
     "desc": "Payload XORed with one random byte, wrapped in base64, rebuilt and written to "
             "temp. The key is brute forced in an instant.",
     "targets": {".bat", ".cmd", ".ps1"}, "obf": obf_xor, "deob": deob_xor},
    {"key": "plain", "label": "Plain base64 blob", "strength": 1,
     "desc": "Single base64 blob written to temp and launched. Weakest, no key at all.",
     "targets": {".bat", ".cmd", ".ps1"}, "obf": obf_plain, "deob": deob_plain},
]

SIGNATURES = [
    ("aes", lambda t: 100 if re.search(r"\+{4,}", t) and "FromBase64String" in t else 0),
    ("certutil", lambda t: 90 if "BEGIN CERTIFICATE" in t and "certutil" in t.lower() else 0),
    ("encodedcommand", lambda t: 85 if "Unicode.GetString" in t and "FromBase64String" in t else 0),
    ("encodedcommand", lambda t: 80 if re.search(r"(?i)-e(?:nc|ncodedcommand)\s+\"?[A-Za-z0-9+/=]{80,}", t) else 0),
    ("pathshards", lambda t: 70 if len(re.findall(r'(?m)^\s*set\s+"?\w+=\\\S', t, re.I)) >= 2 else 0),
    ("varind", lambda t: 60 if len(re.findall(r'(?m)^\s*>>\s*"[^"]*"\s*echo\(', t, re.I)) >= 4 else 0),
    ("charcode", lambda t: 55 if re.search(r"@\([\d,]{60,}\)", t) else 0),
    ("xor", lambda t: 50 if re.search(r"0x[0-9A-Fa-f]{1,2}", t) and "-bxor" in t.lower() else 0),
    ("plain", lambda t: 40 if re.search(r"[A-Za-z0-9+/=]{300,}", t) else 0),
]


def detect(text):
    scores = []
    for key, fn in SIGNATURES:
        try:
            s = fn(text)
        except Exception:
            s = 0
        if s:
            scores.append((s, key))
    scores.sort(reverse=True)
    return scores


def method_by_key(key):
    for m in METHODS:
        if m["key"] == key:
            return m
    return None


class BlurBG(tk.Canvas):
    MARGIN = 90
    TICK = 90

    def __init__(self, master):
        super().__init__(master, bg=BG, highlightthickness=0, bd=0)
        self._base = None
        self._photo = None
        self._item = None
        self._job = None
        self._build_job = None
        self._t = 0.0
        self._size = (0, 0)
        self.glow = ACC
        self.pil = True
        try:
            import PIL  # noqa
        except Exception:
            self.pil = False
        self.bind("<Configure>", self._on_resize)
        self.bind("<Map>", self._start)
        self.bind("<Unmap>", self._stop)
        self._draw_fallback()

    def set_glow(self, color):
        self.glow = color
        self._schedule_build()

    def _on_resize(self, _=None):
        self._schedule_build()

    def _schedule_build(self):
        if self._build_job:
            try:
                self.after_cancel(self._build_job)
            except Exception:
                pass
        self._build_job = self.after(170, self._build)

    def _build(self):
        self._build_job = None
        w, h = self.winfo_width(), self.winfo_height()
        if w < 60 or h < 60:
            return
        self._size = (w, h)
        if not self.pil:
            self._draw_fallback()
            return
        from PIL import Image, ImageDraw, ImageFilter, ImageTk
        m = self.MARGIN
        sw, sh = (w + m * 2) // 2, (h + m * 2) // 2
        img = Image.new("RGB", (sw, sh), (7, 7, 10))
        d = ImageDraw.Draw(img)
        warm = self._rgb(self.glow)
        blobs = [
            (0.15, 0.13, warm, 1.0),
            (0.87, 0.80, (58, 52, 104), 0.85),
            (0.63, 0.20, (22, 40, 12), 0.7),
            (0.26, 0.93, (40, 30, 60), 0.6),
        ]
        for bx, by, col, power in blobs:
            cx, cy = sw * bx, sh * by
            rad = max(sw, sh) * 0.74
            steps = 26
            for i in range(steps):
                f = 1.0 - i / steps
                r = rad * f
                mix = (f ** 2.4) * 0.32 * power
                c = tuple(int(7 + (col[k] - 7) * mix) for k in range(3))
                d.ellipse((cx - r, cy - r * 0.82, cx + r, cy + r * 0.82), fill=c)
        img = img.filter(ImageFilter.GaussianBlur(radius=22))
        self._base = img.resize((w + m * 2, h + m * 2), Image.BILINEAR)
        self._paint()

    def _rgb(self, color):
        try:
            return tuple(int(color[i:i + 2], 16) for i in (1, 3, 5))
        except Exception:
            return (200, 255, 46)

    def _paint(self):
        if self._base is None:
            return
        from PIL import ImageTk
        w, h = self._size
        if w < 2 or h < 2:
            return
        m = self.MARGIN
        ox = m + int(math.sin(self._t * 0.34) * m * 0.85)
        oy = m + int(math.cos(self._t * 0.23) * m * 0.85)
        crop = self._base.crop((ox, oy, ox + w, oy + h))
        self._photo = ImageTk.PhotoImage(crop)
        if self._item is None:
            self._item = self.create_image(0, 0, image=self._photo, anchor="nw")
        else:
            self.itemconfigure(self._item, image=self._photo)

    def _draw_fallback(self):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w < 40 or h < 40:
            return
        self.create_rectangle(0, 0, w, h, fill=BG, outline="")
        cx, cy = w * 0.18, h * 0.16
        rad = max(w, h) * 0.95
        for i in range(22):
            f = 1.0 - i / 22
            col = lerp_hex(BG, self.glow, (f ** 2.6) * 0.15)
            r = rad * f
            self.create_oval(cx - r, cy - r, cx + r, cy + r, outline=col)

    def _start(self, _=None):
        self._schedule_build()
        if self._job is None:
            self._tick()

    def _stop(self, _=None):
        if self._job:
            try:
                self.after_cancel(self._job)
            except Exception:
                pass
            self._job = None

    def _tick(self):
        self._t += 1.0
        if self.pil and self._base is not None:
            self._paint()
        else:
            self._draw_fallback()
        self._job = self.after(self.TICK, self._tick)


def apply_icon(app):
    try:
        from PIL import Image, ImageDraw, ImageTk
    except Exception:
        return
    try:
        size = 128
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.rounded_rectangle((4, 4, size - 5, size - 5), radius=26,
                            fill=(8, 8, 9, 255), outline=(34, 34, 38, 255), width=3)
        d.line((34, 42, 56, 64, 34, 86), fill=(200, 255, 46, 255), width=9, joint="curve")
        d.line((94, 42, 72, 64, 94, 86), fill=(200, 255, 46, 255), width=9, joint="curve")
        d.line((64, 34, 64, 94), fill=(110, 148, 18, 255), width=6)
        ico = os.path.join(os.environ.get("TEMP", "."), "obflab.ico")
        img.save(ico, format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (64, 64)])
        photo = ImageTk.PhotoImage(img)
        app.iconphoto(True, photo)
        app._icon_ref = photo
        app.iconbitmap(ico)
        if sys.platform.startswith("win"):
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("MateAG.BatchOfuscator.Lab.3")
    except Exception:
        pass


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("dark")
        self.title("BatchOfuscator")
        self.geometry("1230x812")
        self.minsize(1120, 750)
        self.configure(fg_color=BG)

        self.ui_font = self._pick(UI_STACK, "Segoe UI")
        self.mono_font = self._pick(MONO_STACK, "Consolas")
        self.option_add("*Font", (self.ui_font, 11))

        self.busy = False
        self.mode = "obf"
        self.accent = ACC
        self.obf_inputs = {}
        self.deob_inputs = {}
        self.log_box = {}
        self.preview_box = {}
        self.desc = {}
        self.run_btn = {}
        self.seg_btn = {}
        self.page = {}
        self.tab_btn = {}
        self._jobs = {}
        self._bgstate = {}
        self._toasts = []
        self._pulse_job = None
        self._accent_job = None
        self._prog_job = None
        self._mark_items = []

        self.bg = BlurBG(self)
        self.bg.place(relx=0, rely=0, relwidth=1, relheight=1)

        self.build_header()
        self.body = ctk.CTkFrame(self, fg_color="transparent")
        self.body.pack(fill="both", expand=True, padx=18, pady=(12, 16))

        self.build_page("obf")
        self.build_page("deob")
        self.show("obf")

        self.bind_all("<Control-o>", lambda _: self.browse(self.mode, "input"))
        self.bind_all("<Control-r>", lambda _: self.run(self.mode))
        self.bind_all("<Control-l>", lambda _: self.clear_log(self.mode))
        self.bind_all("<F1>", lambda _: self.about())

        apply_icon(self)
        self.log("[i] ready  ·  v" + VERSION)
        if not aes_available():
            self.log("[!] no AES backend (pip install cryptography)")
            self.toast("AES backend missing", "warn")

    def _pick(self, candidates, fallback):
        try:
            import tkinter.font as tkfont
            fams = set(tkfont.families(self))
        except Exception:
            return fallback
        for c in candidates:
            if c in fams:
                return c
        return fallback

    def store(self, mode):
        return self.obf_inputs if mode == "obf" else self.deob_inputs

    def _descendants(self, w):
        out = []
        for c in w.winfo_children():
            out.append(c)
            out.extend(self._descendants(c))
        return out

    def anim(self, w, attr, target, ms=170):
        key = (id(w), attr)
        job = self._jobs.get(key)
        if job:
            try:
                self.after_cancel(job)
            except Exception:
                pass
        cur = self._bgstate.get(key)
        if cur is None:
            try:
                cur = _flat(w.cget(attr))
            except Exception:
                cur = target
        self._bgstate[key] = target
        steps = max(4, ms // 16)

        def run(i):
            try:
                w.configure(**{attr: lerp_hex(cur, target, i / steps)})
            except Exception:
                return
            if i < steps:
                self._jobs[key] = self.after(16, run, i + 1)
            else:
                self._jobs[key] = None

        run(0)

    def bind_hover(self, w, base, over, cursor="hand2"):
        key = (id(w), "fg_color")
        self._bgstate[key] = base

        def enter(_=None):
            try:
                w.configure(cursor=cursor)
            except Exception:
                pass
            self.anim(w, "fg_color", over, 120)

        def leave(_=None):
            self.anim(w, "fg_color", base, 180)

        for t in [w] + self._descendants(w):
            t.bind("<Enter>", enter, add="+")
            t.bind("<Leave>", leave, add="+")

    def flash(self, w, attr, color, ms=260):
        cur = _flat(w.cget(attr))
        self.anim(w, attr, color, 90)
        self.after(ms, lambda: self.anim(w, attr, cur, 320))

    def soft_button(self, parent, text, cmd, width=84, accent=False):
        base, over, fg = ("#1b250d", "#26330f", self.accent) if accent else ("#141418", "#1e1e23", FG)
        b = ctk.CTkButton(parent, text=text, width=width, height=28,
                          font=(self.mono_font, 9), fg_color=base, hover_color=base,
                          text_color=fg, corner_radius=6, command=cmd)
        self.bind_hover(b, base, over)
        return b

    def shift_accent(self, target, ms=300):
        if self._accent_job:
            try:
                self.after_cancel(self._accent_job)
            except Exception:
                pass
        start = self.accent
        steps = max(4, ms // 16)

        def run(i):
            self.accent = lerp_hex(start, target, i / steps)
            self.apply_accent()
            if i < steps:
                self._accent_job = self.after(16, run, i + 1)
            else:
                self._accent_job = None

        run(0)

    def apply_accent(self):
        a = self.accent
        for mode in ("obf", "deob"):
            store = self.store(mode)
            for key, info in store.get("rows", {}).items():
                if info["off"]:
                    continue
                if store.get("sel") == key:
                    info["bar"].configure(fg_color=a)
                    info["num"].configure(text_color=a)
                    info["txt"].configure(text_color=a)
                    info["dots"].configure(text_color=dim_of(a, 0.45))
                elif info["accent"]:
                    info["txt"].configure(text_color=dim_of(a, 0.32))
            btn = self.run_btn.get(mode)
            if btn is not None and not self.busy:
                btn.configure(fg_color=a)
                self._bgstate[(id(btn), "fg_color")] = a
        for (m, tid), b in self.tab_btn.items():
            if self.store(m).get("preview_tab") == tid:
                b.configure(text_color=a, fg_color=lerp_hex(BG, a, 0.12))
        for m, b in self.seg_btn.items():
            if m == self.mode:
                b.configure(fg_color=a, hover_color=a, text_color="#0a0b06")
        for item in getattr(self, "_mark_items", []):
            try:
                self.mark.itemconfigure(item, fill=a)
            except Exception:
                pass
        self.bg.set_glow(a)

    def toast(self, text, kind="info"):
        color = {"info": self.accent, "warn": WARN, "err": ERR, "ok": OK}.get(kind, self.accent)
        frame = ctk.CTkFrame(self, fg_color=PANEL, corner_radius=8,
                             border_width=1, border_color="#1f1f24")
        frame.place(relx=0.99, rely=1.03, anchor="se")
        ctk.CTkFrame(frame, fg_color=color, width=2, corner_radius=1).pack(side="left", fill="y", padx=(0, 8))
        ctk.CTkLabel(frame, text=text, font=(self.mono_font, 10), text_color=FG_SOFT).pack(
            padx=(0, 12), pady=8)
        self._toasts.append(frame)
        if len(self._toasts) > 4:
            try:
                self._toasts.pop(0).destroy()
            except Exception:
                pass
        frame.lift()
        self._slide(frame, 1.03, 0.972, 0, lambda: self._fade_out(frame))

    def _slide(self, w, frm, to, step, done):
        steps = 12
        if not w.winfo_exists():
            return
        if step > steps:
            done()
            return
        try:
            w.place_configure(rely=frm + (to - frm) * (step / steps))
        except Exception:
            return
        self.after(14, self._slide, w, frm, to, step + 1, done)

    def _fade_out(self, w):
        self.after(2400, lambda: self._fade_step(w, 0))

    def _fade_step(self, w, step):
        if not w.winfo_exists():
            return
        if step >= 22:
            try:
                w.destroy()
                self._toasts.remove(w)
            except Exception:
                pass
            return
        try:
            w.configure(border_color=lerp_hex("#1f1f24", BG, step / 22))
            w.place_configure(rely=0.972 - 0.010 * (step / 22))
        except Exception:
            return
        self.after(22, self._fade_step, w, step + 1)

    def build_header(self):
        head = ctk.CTkFrame(self, fg_color="transparent")
        head.pack(fill="x", padx=20, pady=(16, 0))

        self.mark = tk.Canvas(head, width=32, height=32, bg=BG, highlightthickness=0)
        self.mark.pack(side="left", padx=(0, 11))
        self._mark_items = [
            self.mark.create_line(8, 9, 15, 16, 8, 23, fill=ACC, width=2,
                                  capstyle="round", joinstyle="round"),
            self.mark.create_line(24, 9, 17, 16, 24, 23, fill=ACC, width=2,
                                  capstyle="round", joinstyle="round"),
        ]
        self.mark.create_line(16, 6, 16, 26, fill=ACC_DIM_DARK, width=1)

        left = ctk.CTkFrame(head, fg_color="transparent")
        left.pack(side="left")
        ctk.CTkLabel(left, text="BatchOfuscator", font=(self.ui_font, 15, "bold"),
                     text_color=FG).pack(anchor="w")
        ctk.CTkLabel(left, text="An advanced batch and PowerShell obfuscation tool.", font=(self.mono_font, 9),
                     text_color=DIM2).pack(anchor="w")

        right = ctk.CTkFrame(head, fg_color="transparent")
        right.pack(side="right")
        self.state_dot = ctk.CTkLabel(right, text="●", font=(self.mono_font, 9), text_color=DIM2)
        self.state_dot.pack(side="left", padx=(0, 5))
        self.state_txt = ctk.CTkLabel(right, text="idle", font=(self.mono_font, 9),
                                      text_color=DIM2)
        self.state_txt.pack(side="left")
        ctk.CTkLabel(right, text="   v" + VERSION, font=(self.mono_font, 9),
                     text_color="#35353c").pack(side="left")

        ctk.CTkFrame(self, fg_color=HAIR, height=1).pack(fill="x", padx=20, pady=(12, 0))

    def build_page(self, mode):
        store = self.store(mode)
        store["var"] = tk.StringVar(value="")
        store["rows"] = {}
        store["sel"] = None
        store["input"] = None
        store["output"] = None
        store["preview_tab"] = "log"

        page = ctk.CTkFrame(self.body, fg_color="transparent")
        self.page[mode] = page

        cols = ctk.CTkFrame(page, fg_color="transparent")
        cols.pack(fill="both", expand=True)

        rail = ctk.CTkFrame(cols, fg_color=PANEL, corner_radius=11, width=372,
                            border_width=1, border_color="#16161a")
        rail.pack(side="left", fill="both", padx=(0, 12))
        rail.pack_propagate(False)

        seg = ctk.CTkFrame(rail, fg_color="#0d0d10", corner_radius=8, border_width=1,
                           border_color=HAIR)
        seg.pack(fill="x", padx=11, pady=(11, 10))
        for m, label in (("obf", "OBFUSCATE"), ("deob", "DEOBFUSCATE")):
            b = ctk.CTkButton(seg, text=label, height=27, corner_radius=6,
                              font=(self.mono_font, 9, "bold"), fg_color="#0d0d10",
                              hover_color="#18181d", text_color=DIM2,
                              command=lambda md=m: self.show(md))
            b.pack(side="left", expand=True, fill="x", padx=2, pady=2)
            self.seg_btn[m] = b

        top = ctk.CTkFrame(rail, fg_color="transparent")
        top.pack(fill="x", padx=13)
        ctk.CTkLabel(top, text="M E T H O D", font=(self.mono_font, 8, "bold"),
                     text_color="#43434b").pack(side="left")
        store["count"] = ctk.CTkLabel(top, text="", font=(self.mono_font, 8), text_color="#3a3a41")
        store["count"].pack(side="right")

        scroll = ctk.CTkScrollableFrame(rail, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=7, pady=(5, 7))

        if mode == "deob":
            self.make_row(scroll, mode, "auto", 0, "AUTO detect + chain", 5, accent=True)
        for idx, m in enumerate(METHODS, start=1):
            self.make_row(scroll, mode, m["key"], idx, m["label"], m["strength"])

        self.desc[mode] = ctk.CTkLabel(rail, text="select a method", font=(self.ui_font, 10),
                                       text_color=DIM, wraplength=336, justify="left",
                                       anchor="nw", height=96)
        self.desc[mode].pack(fill="x", padx=13, pady=(0, 12))

        work = ctk.CTkFrame(cols, fg_color="transparent")
        work.pack(side="left", fill="both", expand=True)

        card = ctk.CTkFrame(work, fg_color=CARD, corner_radius=11, border_width=1,
                            border_color="#16161a")
        card.pack(fill="x")

        self.path_row(card, mode, "IN", "input")
        self.path_row(card, mode, "OUT", "output")

        opts = ctk.CTkFrame(card, fg_color="transparent")
        opts.pack(fill="x", padx=13, pady=(3, 11))
        if mode == "deob":
            ctk.CTkLabel(opts, text="chain depth", font=(self.mono_font, 9),
                         text_color=DIM2).pack(side="left")
            sp = ctk.CTkOptionMenu(opts, values=["1", "2", "3", "4", "5"], width=58,
                                   height=25, fg_color="#16161a", button_color="#212126",
                                   button_hover_color="#2c2c32", text_color=FG,
                                   font=(self.mono_font, 10), dropdown_font=(self.mono_font, 10),
                                   corner_radius=6)
            sp.set("3")
            sp.pack(side="left", padx=(8, 0))
            store["depth"] = sp
        else:
            ctk.CTkLabel(opts, text="wrap: full loader stub  ·  banner included",
                         font=(self.mono_font, 9), text_color="#3d3d45").pack(side="left")

        bar = ctk.CTkFrame(work, fg_color="transparent")
        bar.pack(fill="x", pady=10)

        self.run_btn[mode] = ctk.CTkButton(
            bar, text="RUN", height=37, font=(self.mono_font, 12, "bold"),
            fg_color=self.accent, hover_color=self.accent, text_color="#08090a",
            corner_radius=8, command=lambda md=mode: self.run(md))
        self.run_btn[mode].pack(side="left", fill="x", expand=True)
        self.bind_hover(self.run_btn[mode], self.accent, "#e2ff74")

        ctk.CTkLabel(bar, text="ctrl+r", font=(self.mono_font, 8),
                     text_color="#35353c").pack(side="left", padx=(8, 0))
        self.soft_button(bar, "OPEN", lambda md=mode: self.open_output(md),
                         width=64).pack(side="left", padx=(10, 0))
        self.soft_button(bar, "CLEAR", lambda md=mode: self.clear_log(md),
                         width=64).pack(side="left", padx=(6, 0))

        store["prog"] = tk.Canvas(work, height=1, bg=BG, highlightthickness=0)
        store["prog"].pack(fill="x", pady=(0, 9))

        tabs = ctk.CTkFrame(work, fg_color="transparent")
        tabs.pack(fill="x", pady=(0, 5))
        for tid, label in (("log", "CONSOLE"), ("preview", "PREVIEW")):
            b = ctk.CTkButton(tabs, text=label, width=94, height=23, corner_radius=6,
                              font=(self.mono_font, 8, "bold"), fg_color="#0d0d10",
                              hover_color="#18181d", text_color="#41414a",
                              command=lambda md=mode, t=tid: self.switch_tab(md, t))
            b.pack(side="left", padx=(0, 6))
            self.tab_btn[(mode, tid)] = b

        holder = ctk.CTkFrame(work, fg_color="#08080b", corner_radius=10, border_width=1,
                              border_color="#16161a")
        holder.pack(fill="both", expand=True)

        self.log_box[mode] = ctk.CTkTextbox(holder, font=(self.mono_font, 10),
                                            fg_color="transparent", text_color="#c7c7ce",
                                            corner_radius=9, wrap="none")
        self.preview_box[mode] = ctk.CTkTextbox(holder, font=(self.mono_font, 10),
                                                fg_color="transparent", text_color="#9ba189",
                                                corner_radius=9, wrap="none")
        for box in (self.log_box[mode], self.preview_box[mode]):
            box.configure(state="disabled")
            self._tagcfg(box, "acc", foreground=ACC)
            self._tagcfg(box, "ok", foreground=OK)
            self._tagcfg(box, "err", foreground=ERR)
            self._tagcfg(box, "warn", foreground=WARN)
            self._tagcfg(box, "dim", foreground="#3a3a41")
        self.log_box[mode].pack(fill="both", expand=True, padx=2, pady=2)
        self.switch_tab(mode, "log")

    def _tagcfg(self, box, name, **kw):
        try:
            box.tag_config(name, **kw)
        except Exception:
            try:
                box._textbox.tag_config(name, **kw)
            except Exception:
                pass

    def make_row(self, parent, mode, key, index, label, strength, accent=False):
        store = self.store(mode)
        row = ctk.CTkFrame(parent, fg_color=ROW, height=30, corner_radius=6)
        row.pack(fill="x", pady=1)
        row.pack_propagate(False)

        bar = ctk.CTkFrame(row, width=2, fg_color="transparent", corner_radius=1)
        bar.pack(side="left", fill="y")
        num = ctk.CTkLabel(row, text="%02d" % index, width=23, font=(self.mono_font, 8),
                           text_color="#3d3d45")
        num.pack(side="left", padx=(6, 0))

        dots = ctk.CTkLabel(row, text="●" * strength + "○" * (5 - strength),
                            font=(self.mono_font, 7), text_color="#313f14")
        dots.pack(side="right", padx=(5, 9))

        txt = ctk.CTkLabel(row, text=label, font=(self.ui_font, 11),
                           text_color=dim_of(self.accent, 0.32) if accent else FG_SOFT, anchor="w")
        txt.pack(side="left", fill="x", expand=True, padx=(2, 5))

        info = {"row": row, "bar": bar, "num": num, "txt": txt, "dots": dots,
                "key": key, "off": False, "accent": accent}
        store["rows"][key] = info

        def enter(_=None):
            if info["off"] or store["sel"] == key:
                return
            row.configure(cursor="hand2")
            self.paint_row(info, "hover")

        def leave(_=None):
            if info["off"] or store["sel"] == key:
                return
            self.paint_row(info, "idle")

        def click(_=None):
            if info["off"]:
                return
            self.select(mode, key)

        for t in [row] + self._descendants(row):
            t.bind("<Enter>", enter, add="+")
            t.bind("<Leave>", leave, add="+")
            t.bind("<Button-1>", click, add="+")
        return info

    def paint_row(self, info, state):
        if info["off"]:
            info["row"].configure(fg_color="#0b0b0e", cursor="arrow")
            info["bar"].configure(fg_color="transparent")
            info["num"].configure(text_color="#2f2f36")
            info["txt"].configure(text_color="#43434b")
            info["dots"].configure(text_color="#232329")
            return
        if state == "sel":
            self.anim(info["row"], "fg_color", ROW_SEL)
            info["bar"].configure(fg_color=self.accent)
            info["num"].configure(text_color=self.accent)
            info["txt"].configure(text_color=self.accent)
            info["dots"].configure(text_color=dim_of(self.accent, 0.45))
        elif state == "hover":
            self.anim(info["row"], "fg_color", ROW_HOVER, 110)
            info["bar"].configure(fg_color=dim_of(self.accent, 0.5))
            info["num"].configure(text_color=DIM)
            info["txt"].configure(text_color=FG)
            info["dots"].configure(text_color="#4d6813")
        else:
            self.anim(info["row"], "fg_color", ROW, 180)
            info["bar"].configure(fg_color="transparent")
            info["num"].configure(text_color="#3d3d45")
            info["txt"].configure(text_color=dim_of(self.accent, 0.32) if info["accent"] else FG_SOFT)
            info["dots"].configure(text_color="#313f14")

    def set_off(self, info, flag):
        info["off"] = flag
        self.paint_row(info, "idle")

    def select(self, mode, key):
        store = self.store(mode)
        store["sel"] = key
        store["var"].set(key)
        for k, info in store["rows"].items():
            self.paint_row(info, "sel" if k == key else "idle")
        self.describe(mode, key)

    def describe(self, mode, key):
        if key == "auto":
            self.desc[mode].configure(
                text="Signature scan, best match first, then repeat on the result up to the "
                     "chain depth. Stops when nothing matches.")
            return
        m = method_by_key(key)
        if m:
            self.desc[mode].configure(text=m["desc"])

    def path_row(self, parent, mode, caption, which):
        store = self.store(mode)
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=13, pady=(11 if which == "input" else 5, 0))
        ctk.CTkLabel(row, text=caption, font=(self.mono_font, 8, "bold"),
                     text_color="#43434b", width=30, anchor="w").pack(side="left")
        entry = ctk.CTkEntry(row, height=28, font=(self.mono_font, 10), fg_color="#08080b",
                             border_color="#1e1e23", text_color=FG, corner_radius=6,
                             placeholder_text=("path to .bat / .cmd / .ps1" if which == "input"
                                               else "output path"))
        entry.pack(side="left", fill="x", expand=True, padx=(0, 7))
        store[which] = entry
        if which == "input":
            self.soft_button(row, "BROWSE", lambda: self.browse(mode, which)).pack(side="left")
            self.soft_button(row, "ANALYZE", lambda: self.analyze(mode),
                             accent=True).pack(side="left", padx=(7, 0))
        else:
            self.soft_button(row, "COPY", lambda: self.copy_output(mode)).pack(side="left")
            self.soft_button(row, "BROWSE", lambda: self.browse(mode, which)).pack(side="left", padx=(7, 0))

    def switch_tab(self, mode, tab):
        store = self.store(mode)
        store["preview_tab"] = tab
        if tab == "log":
            self.preview_box[mode].pack_forget()
            self.log_box[mode].pack(fill="both", expand=True, padx=2, pady=2)
        else:
            self.log_box[mode].pack_forget()
            self.preview_box[mode].pack(fill="both", expand=True, padx=2, pady=2)
        for (m, tid), b in self.tab_btn.items():
            if m != mode:
                continue
            on = tid == tab
            b.configure(text_color=self.accent if on else "#41414a",
                        fg_color=lerp_hex(BG, self.accent, 0.12) if on else "#0d0d10")

    def log(self, line, mode=None, kind=None):
        mode = mode or self.mode
        if not getattr(self, "log_box", None):
            return
        box = self.log_box.get(mode) or self.log_box.get("obf")
        if box is None:
            return
        if kind is None:
            if line.startswith("[!]"):
                kind = "err"
            elif line.startswith("[+"):
                kind = "ok"
            elif line.startswith("[i]"):
                kind = "dim"
            elif line.startswith("[>"):
                kind = "acc"
        box.configure(state="normal")
        if line:
            box.insert("end", time.strftime("%H:%M:%S") + "  ", "dim")
            box.insert("end", line + "\n", kind or "")
        else:
            box.insert("end", "\n")
        box.see("end")
        box.configure(state="disabled")

    def clear_log(self, mode=None):
        mode = mode or self.mode
        box = self.log_box.get(mode)
        if box is None:
            return
        box.configure(state="normal")
        box.delete("1.0", "end")
        box.configure(state="disabled")
        self.set_preview(mode, "")

    def set_preview(self, mode, text):
        box = self.preview_box.get(mode)
        if box is None:
            return
        box.configure(state="normal")
        box.delete("1.0", "end")
        if text:
            box.insert("1.0", text[:200000])
        box.configure(state="disabled")

    def copy_output(self, mode):
        store = self.store(mode)
        path = store["output"].get().strip()
        if path and os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8-sig") as fh:
                    self.clipboard_clear()
                    self.clipboard_append(fh.read())
                self.toast("output copied", "ok")
            except Exception as exc:
                self.toast("copy failed", "err")
                self.log("[!] " + str(exc), mode)
        else:
            self.toast("no output yet", "warn")

    def start_progress(self):
        canvas = self.store(self.mode).get("prog")
        if canvas is None:
            return
        pos = [-0.08]

        def tick():
            try:
                canvas.delete("all")
                w = canvas.winfo_width() or 1
                block = max(90, w * 0.26)
                x = pos[0] * (w + block) - block
                canvas.create_rectangle(x, 0, x + block, 2, fill=self.accent, outline="")
            except Exception:
                return
            pos[0] += 0.012
            if pos[0] > 1.15:
                pos[0] = -0.08
            self._prog_job = self.after(18, tick)

        tick()

    def stop_progress(self):
        if self._prog_job:
            try:
                self.after_cancel(self._prog_job)
            except Exception:
                pass
            self._prog_job = None
        for store in (self.obf_inputs, self.deob_inputs):
            canvas = store.get("prog")
            if canvas is not None:
                try:
                    canvas.delete("all")
                except Exception:
                    pass

    def pulse_state(self):
        if not self.busy:
            return
        cur = _flat(self.state_dot.cget("text_color"))
        nxt = lerp_hex(self.accent, "#ffffff", 0.4) if cur != WARN else dim_of(self.accent, 0.5)
        self.state_dot.configure(text_color=nxt)
        self._pulse_job = self.after(430, self.pulse_state)

    def show(self, mode):
        if self.busy:
            return
        self.mode = mode
        for m, page in self.page.items():
            if m == mode:
                page.pack(fill="both", expand=True)
            else:
                page.pack_forget()
        for m, btn in self.seg_btn.items():
            on = m == mode
            btn.configure(text_color="#0a0b06" if on else DIM2,
                          fg_color=self.accent if on else "#0d0d10",
                          hover_color=self.accent if on else "#18181d")
        self.log("", mode)

    def browse(self, mode, which):
        store = self.store(mode)
        if which == "input":
            path = filedialog.askopenfilename(
                title="select target",
                filetypes=[("batch / powershell", "*.bat *.cmd *.ps1"), ("all files", "*.*")])
            if path:
                store["input"].delete(0, "end")
                store["input"].insert(0, path)
                self.autofill_output(mode, path)
                self.flash(store["input"], "border_color", dim_of(self.accent, 0.35))
        else:
            path = filedialog.asksaveasfilename(title="output path")
            if path:
                store["output"].delete(0, "end")
                store["output"].insert(0, path)

    def autofill_output(self, mode, path):
        store = self.store(mode)
        root, ext = os.path.splitext(path)
        if mode == "obf":
            m = method_by_key(store["sel"] or "")
            if m and m.get("out_ext"):
                ext = m["out_ext"]
            suffix = "_obf"
        else:
            suffix = "_deob"
        store["output"].delete(0, "end")
        store["output"].insert(0, root + suffix + ext)

    def open_output(self, mode):
        store = self.store(mode)
        path = store["output"].get().strip()
        if path and os.path.exists(path):
            folder = os.path.dirname(os.path.abspath(path))
            try:
                if sys.platform.startswith("win"):
                    os.startfile(folder)
                else:
                    subprocess.Popen(["xdg-open", folder])
            except Exception as exc:
                self.log("[!] " + str(exc), mode)
        else:
            self.toast("output does not exist yet", "warn")

    def analyze(self, mode):
        store = self.store(mode)
        path = store["input"].get().strip()
        if not path or not os.path.isfile(path):
            self.toast("pick an existing input file", "warn")
            self.flash(store["input"], "border_color", ERR)
            return
        try:
            size = os.path.getsize(path)
            if size > MAXBYTES:
                self.log("[!] file larger than %d MB" % (MAXBYTES // 1024 // 1024), mode)
                return
            with open(path, "rb") as fh:
                text = normalize_text(fh.read())
        except Exception as exc:
            self.log("[!] read failed: " + str(exc), mode)
            return

        ext = os.path.splitext(path)[1].lower()
        self.log("[>] %s  %d bytes  %d lines"
                 % (os.path.basename(path), size, text.count("\n") + 1), mode)

        hits = detect(text)
        if hits:
            self.log("[i] signatures:", mode)
            for score, key in hits:
                self.log("      %3d  %s" % (score, method_by_key(key)["label"]), mode)
        else:
            self.log("[i] no known signature", mode)

        if mode == "obf":
            usable = []
            for m in METHODS:
                ok = ext in m["targets"] and (aes_available() or not m.get("needs_aes"))
                self.set_off(store["rows"][m["key"]], not ok)
                if ok:
                    usable.append(m)
            store["count"].configure(text="%d/%d valid" % (len(usable), len(METHODS)))
            self.log("[i] %d of %d methods support %s"
                     % (len(usable), len(METHODS), ext or "?"), mode)
            if usable:
                self.select("obf", usable[0]["key"])
                self.toast("%d methods available" % len(usable), "ok")
            else:
                self.toast("no method supports that extension", "err")
        else:
            if hits:
                best = method_by_key(hits[0][1])
                self.select("deob", best["key"])
                self.log("[i] preselected: " + best["label"], mode)
            else:
                self.select("deob", "auto")

    def run(self, mode):
        if self.busy:
            return
        store = self.store(mode)
        src = store["input"].get().strip()
        dst = store["output"].get().strip()
        if not src or not os.path.isfile(src):
            self.toast("invalid input path", "err")
            self.flash(store["input"], "border_color", ERR)
            return
        if not dst:
            self.autofill_output(mode, src)
            dst = store["output"].get().strip()
        key = store["sel"]
        if not key:
            self.toast("no method selected", "warn")
            return
        depth = int(store["depth"].get()) if mode == "deob" else 1
        self.busy = True
        self.shift_accent(ACC_HOT)
        self.state_txt.configure(text="working", text_color=WARN)
        self.state_dot.configure(text_color=ACC_HOT)
        self.pulse_state()
        self.start_progress()
        self.run_btn[mode].configure(state="disabled", text="WORKING",
                                     fg_color=dim_of(ACC_HOT, 0.45))
        threading.Thread(target=self.worker, args=(mode, src, dst, key, depth),
                         daemon=True).start()

    def worker(self, mode, src, dst, key, depth):
        try:
            with open(src, "rb") as fh:
                text = normalize_text(fh.read())
            ext = os.path.splitext(src)[1].lower()

            if mode == "obf":
                m = method_by_key(key)
                if ext not in m["targets"]:
                    self.log("[!] %s does not support %s" % (m["label"], ext), mode)
                    return
                if m.get("needs_aes") and not aes_available():
                    self.log("[!] AES backend missing", mode)
                    return
                self.log("[>] applying %s" % m["label"], mode)
                result = m["obf"](text, ext)
                self.write(dst, result)
                self.log("[+] %d bytes -> %s" % (len(result), dst), mode)
                self.log("[+] done", mode)
            else:
                if key == "auto":
                    self.chain(text, dst, depth)
                else:
                    m = method_by_key(key)
                    self.log("[>] applying %s" % m["label"], mode)
                    result = self.step(text, m)
                    for _ in range(depth - 1):
                        hits = detect(result)
                        if not hits:
                            break
                        nxt = method_by_key(hits[0][1])
                        self.log("[i] layer: %s" % nxt["label"], mode)
                        result = self.step(result, nxt)
                    self.write(dst, result)
                    self.log("[+] %d bytes -> %s" % (len(result), dst), mode)
                    self.log("[+] done", mode)
        except DeobError as exc:
            self.log("[!] " + str(exc), mode)
        except Exception:
            self.log("[!] unhandled exception", mode)
            for line in traceback.format_exc().splitlines():
                self.log("    " + line, mode)
        finally:
            self.busy = False
            self.after(0, self.finish, mode)

    def step(self, text, m):
        out = m["deob"](text, ".bat")
        if not out or not out.strip():
            raise DeobError("empty result from " + m["label"])
        return out

    def chain(self, text, dst, depth):
        current = text
        applied = 0
        for _ in range(depth):
            hits = detect(current)
            if not hits:
                break
            m = method_by_key(hits[0][1])
            self.log("[i] layer %d: %s (%d)" % (applied + 1, m["label"], hits[0][0]), "deob")
            try:
                nxt = self.step(current, m)
            except DeobError as exc:
                self.log("[!] " + str(exc), "deob")
                break
            if nxt == current:
                break
            current = nxt
            applied += 1
        if not applied:
            self.log("[!] nothing could be reversed", "deob")
            return
        self.write(dst, current)
        self.log("[+] %d layer(s) removed, %d bytes -> %s" % (applied, len(current), dst), "deob")

    def write(self, dst, text):
        folder = os.path.dirname(os.path.abspath(dst))
        if folder and not os.path.isdir(folder):
            os.makedirs(folder, exist_ok=True)
        if dst.lower().endswith((".bat", ".cmd")):
            with open(dst, "w", encoding="utf-8", newline="") as fh:
                fh.write(text.replace("\r\n", "\n").replace("\n", "\r\n"))
        else:
            with open(dst, "w", encoding="utf-8-sig", newline="\n") as fh:
                fh.write(text)

    def finish(self, mode):
        self.stop_progress()
        if self._pulse_job:
            try:
                self.after_cancel(self._pulse_job)
            except Exception:
                pass
            self._pulse_job = None
        self.state_txt.configure(text="idle", text_color=DIM2)
        self.state_dot.configure(text_color=DIM2)
        self.run_btn[mode].configure(state="normal", text="RUN", fg_color=self.accent)
        self._bgstate[(id(self.run_btn[mode]), "fg_color")] = self.accent
        self.shift_accent(ACC, 420)
        store = self.store(mode)
        path = store["output"].get().strip()
        if path and os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8-sig", errors="replace") as fh:
                    self.set_preview(mode, fh.read())
                self.toast("file written", "ok")
            except Exception:
                pass

    def about(self):
        messagebox.showinfo(
            "BatchOfuscator",
            "BatchOfuscator %s\n\n"
            "Obfuscation and reversal lab for .bat / .cmd / .ps1.\n\n"
            "Ctrl+O  browse input\n"
            "Ctrl+R  run\n"
            "Ctrl+L  clear console\n"
            "F1      this window\n\n"
            "(c) 2026 MateAG" % VERSION)


def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()