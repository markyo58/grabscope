#!/usr/bin/env python3
"""selection judge — GrabScope zone 3 (Mark 2026-10-31; SPEC ~/Polaris/Staging/2026-10-31-grabscope/SPEC.md).
Selection on stdin; stdout = the short result the ring shows.
  link  -> one row in the Links list (Pendulum Notch Links tab), no AI
  code  -> choose() point selection.judge says code/command -> Claude explains (popup)
  else  -> bell ring to the chat Mark used last (also the fallback when Jev is down)
One log row per tap in ~/.config/grabscope/judge.db (utc, kind, route, chars, jev_ok)."""
import os
import re
import sqlite3
import subprocess
import sys
import urllib.parse
from datetime import datetime, timezone

LINKS = os.path.expanduser("~/Polaris/Staging/links/inbox.tsv")
LOGDB = os.path.expanduser("~/.config/grabscope/judge.db")
RING = os.path.expanduser("~/Polaris/Staging/bell/ring")
ASK = os.path.expanduser("~/.config/grabscope/claude-ask.sh")
FBQ = os.path.expanduser("~/ARCdev/TinyDev/TinySync/fbq.py")
CLAUDE_APP = "com.anthropic.claudefordesktop"
JOBNUM = re.compile(r"(?:#|fbq\s*)?(\d{1,5})")
URL = re.compile(r"https?://\S+")


def utc():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def clean_url(text):
    """The one URL a selection means, or None: trims spaces/quotes/brackets/trailing punctuation, unwraps
    <url> and [title](url), and adds https:// to a bare github.com/... or youtube.com/... or www.... form."""
    t = text.strip().strip("\"'`“”‘’")
    m = re.fullmatch(r"\[[^\]]*\]\((\S+?)\)", t) or re.fullmatch(r"<(\S+)>", t)
    if m:
        t = m.group(1)
    t = t.rstrip(".,;:!?)]}>\"'")
    if re.fullmatch(r"(www\.|github\.com/|youtu\.be/|(m\.)?youtube\.com/)\S+", t):
        t = "https://" + t
    return t if URL.fullmatch(t) else None


def link_kind(text):
    """'github'|'youtube'|'web' when the whole selection is one URL, else None."""
    t = clean_url(text)
    if not t:
        return None
    host = (urllib.parse.urlparse(t).hostname or "").lower()
    if host == "github.com" or host.endswith(".github.com"):
        return "github"
    if host in ("youtu.be", "youtube.com") or host.endswith(".youtube.com"):
        return "youtube"
    return "web"


def front_bundle():
    """Bundle id of the frontmost app (the one the text was selected in; GrabScope never takes focus). lsappinfo is
    native and needs no Automation grant. None when unreadable."""
    try:
        asn = subprocess.run(["lsappinfo", "front"], capture_output=True, text=True, timeout=2).stdout.strip()
        out = subprocess.run(["lsappinfo", "info", "-only", "bundleid", asn], capture_output=True, text=True, timeout=2).stdout
        m = re.search(r'bundleID="([^"]+)"', out)
        return m.group(1) if m else None
    except Exception:
        return None


def job_candidate(text):
    """The job number a selection could mean ('1125', '#1125', 'fbq 1125'), else None. Digits only, short."""
    m = JOBNUM.fullmatch(text.strip())
    return int(m.group(1)) if m else None


def ask_sitrep(n):
    """Ask the SM for a briefing on job n: one fbq note, which the tracker's smstandby already shows the SM seat.
    True when the note landed; False when there is no such job."""
    r = subprocess.run([sys.executable, FBQ, "note", str(n), "SITREP ASKED: Mark via GrabScope"], capture_output=True,
                       text=True, timeout=8, env=dict(os.environ, FBQ_HOLDER="grabscope"))
    return r.returncode == 0 and "REFUSED" not in (r.stdout + r.stderr)


def is_jobnumber(text, choose_fn=None):
    """Is this unknown number meant as a job? Jev only (a year, a date or an amount say no). Jev down -> (False, False)."""
    if os.environ.get("ARC_CHOOSE_OFF") == "1":
        return False, False
    try:
        if choose_fn is None:
            sys.path.insert(0, os.path.expanduser("~/ARC/DEV"))
            import choose as _c
            choose_fn = _c.choose
        spec = {"id": "selection.judge.job", "version": 1, "mode": "active", "timeout": 3.0, "fallback_name": "not a job",
                "questions": {"job": {"type": "noul", "instructions": "Is this number an fb job number, not a year, date or amount?",
                                      "criteria": {"true": "A small queue number such as 1125", "false": "A year, date, amount or other number"}}},
                "build_state": lambda i: {"text": i["text"]},
                "policy": lambda a, i: "yes" if a["job"]["noul"] >= 0.8 else "no",
                "fallback": lambda i: "no"}
        got = choose_fn(spec, {"text": text})
    except Exception:
        return False, False
    return got == "yes", True


def is_code(text, choose_fn=None):
    """-> (code?, jev_ok). Jev down, timeout or abstain -> (False, False): the fallback is the chat."""
    if os.environ.get("ARC_CHOOSE_OFF") == "1":
        return False, False
    try:
        if choose_fn is None:
            sys.path.insert(0, os.path.expanduser("~/ARC/DEV"))
            import choose as _c
            choose_fn = _c.choose
        spec = {"id": "selection.judge", "version": 1, "mode": "active", "timeout": 3.0, "fallback_name": "the chat",
                "questions": {"code": {"type": "noul",
                                       "instructions": "Is this selected text source code or a shell command?",
                                       "criteria": {"true": "It is a function, a script or a command line; terminal output with result lines is not",
                                                    "false": "It is prose, a task, an error message or terminal output"}}},
                "build_state": lambda i: {"text": i["text"][:1500]},
                "policy": lambda a, i: "yes" if a["code"]["noul"] >= 0.8 else "no" if a["code"]["noul"] <= 0.2 else "ABSTAIN",
                "fallback": lambda i: "ABSTAIN"}
        got = choose_fn(spec, {"text": text})
    except Exception:
        return False, False
    return got == "yes", got in ("yes", "no")


def log(kind, route, chars, jev_ok):
    try:
        os.makedirs(os.path.dirname(LOGDB), exist_ok=True)
        with sqlite3.connect(LOGDB) as c:
            c.execute("CREATE TABLE IF NOT EXISTS Judge (utc TEXT NOT NULL, kind TEXT NOT NULL, route TEXT NOT NULL, "
                      "chars INTEGER NOT NULL, jev_ok INTEGER NOT NULL) STRICT")
            c.execute("INSERT INTO Judge VALUES (?,?,?,?,?)", (utc(), kind, route, chars, int(jev_ok)))
    except Exception:
        pass   # a log failure never costs the tap


def judge(text, choose_fn=None, links=LINKS, ring=None, explain=None, front=None, sitrep=None):
    """Route one selection. Returns (kind, route, result_text). ring/explain injectable for tests."""
    t = text.strip()
    lk = link_kind(t)
    if lk:
        t = clean_url(t)
        os.makedirs(os.path.dirname(links), exist_ok=True)
        with open(links, "a") as fh:
            fh.write("%s\t%s\t%s\t\t\n" % (utc(), lk, t))
        log(lk, "links", len(t), True)
        return lk, "links", "Added to Links (%s):\n%s" % (lk, t)
    n = job_candidate(t)
    if n is not None and (front or front_bundle)() == CLAUDE_APP:   # job numbers only count inside the Claude app
        if (sitrep or ask_sitrep)(n):
            log("jobnumber", "sm", len(t), True)
            return "jobnumber", "sm", "Job %d → SM briefing asked" % n
        yes, ok = is_jobnumber(t, choose_fn)
        if yes:
            log("jobnumber", "none", len(t), ok)
            return "jobnumber", "none", "no job %d" % n
    code, ok = is_code(t, choose_fn)
    if code:
        out = (explain or (lambda s: subprocess.run([ASK, "Explain what this code or command does, briefly."],
                                                    input=s, capture_output=True, text=True, timeout=9).stdout))(t)
        log("code", "explain", len(t), ok)
        return "code", "explain", out.strip() or "(Claude gave no answer)"
    # ponytail: the bell wakes EVERY watching session, not the one chat Mark used last; pol 5b034bbb owns the last-chat design
    (ring or (lambda s: subprocess.run([RING, "grabscope:judge", s], timeout=5)))(t)
    log("text", "chat", len(t), ok)
    return "text", "chat", "Sent to the bell (every watching session sees it; no single chat yet):\n%s" % (t[:200] + ("…" if len(t) > 200 else ""))


if __name__ == "__main__":
    print(judge(sys.stdin.read())[2])
