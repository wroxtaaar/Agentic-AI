"""Read-only Docker/service monitor with transition-based email alerts.

The monitor never restarts containers or changes application state. Docker access
is intended to go through a docker-socket-proxy with POST disabled.
"""
from __future__ import annotations

import hashlib
import os
import re
import smtplib
import sqlite3
import subprocess
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path

DB_PATH = Path(os.getenv("MONITOR_DB_PATH", "/data/monitor.db"))
INTERVAL = max(60, int(os.getenv("MONITOR_INTERVAL_SECONDS", "300")))
CONTAINERS = [x.strip() for x in os.getenv(
    "MONITOR_CONTAINERS", "home,docker-control-bot,agentic-ai"
).split(",") if x.strip()]
HEALTH_URLS = [x.strip() for x in os.getenv(
    "MONITOR_HEALTH_URLS", "http://host.docker.internal:10000/health"
).split(",") if x.strip()]
LOG_SINCE = os.getenv("MONITOR_LOG_SINCE", "10m")
LOG_TAIL = max(20, min(300, int(os.getenv("MONITOR_LOG_TAIL", "120"))))
RECOVERY_MISSES = max(1, int(os.getenv("MONITOR_RECOVERY_MISSES", "2")))

SECRET_PATTERNS = [
    (re.compile(r"(?i)(authorization\s*[:=]\s*bearer\s+)[^\s,;]+"), r"\1[REDACTED]"),
    (re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._~+/=-]{8,}"), r"\1[REDACTED]"),
    (re.compile(r"(?i)((?:api[_-]?key|access[_-]?token|refresh[_-]?token|password|passwd|secret|client_secret|private[_-]?key)\s*[=:]\s*)['\"]?[^\s,'\";]+"), r"\1[REDACTED]"),
    (re.compile(r"(?s)(-----BEGIN [A-Z ]*PRIVATE KEY-----).*?(-----END [A-Z ]*PRIVATE KEY-----)"), r"\1[REDACTED]\2"),
]
ERROR_RE = re.compile(r"(?i)(\bERROR\b|\bFATAL\b|\bPANIC\b|Traceback \(most recent call last\)|OutOfMemoryError|OOMKilled|segmentation fault|uncaught exception)")
NOISY_VALUES = re.compile(r"\b[0-9a-f]{12,64}\b", re.I)


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def redact(value: str, limit: int = 1800) -> str:
    for pattern, replacement in SECRET_PATTERNS:
        value = pattern.sub(replacement, value)
    return value[:limit] + ("…[TRUNCATED]" if len(value) > limit else "")


def run_docker(args: list[str], timeout: int = 15) -> tuple[bool, str]:
    try:
        result = subprocess.run(
            ["docker", *args], capture_output=True, text=True,
            timeout=timeout, check=False,
        )
        output = result.stdout.strip() or result.stderr.strip()
        return result.returncode == 0, redact(output, 12000)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, redact(str(exc), 1000)


def db_connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH, timeout=10)
    con.execute("""
        CREATE TABLE IF NOT EXISTS incidents (
            fingerprint TEXT PRIMARY KEY,
            subject TEXT NOT NULL,
            details TEXT NOT NULL,
            first_seen TEXT NOT NULL,
            last_seen TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active',
            missed_checks INTEGER NOT NULL DEFAULT 0,
            notified INTEGER NOT NULL DEFAULT 0
        )
    """)
    return con


def send_email(subject: str, body: str) -> bool:
    host = os.getenv("SMTP_HOST", "").strip()
    port = int(os.getenv("SMTP_PORT", "587"))
    username = os.getenv("SMTP_USERNAME", "").strip()
    password = os.getenv("SMTP_PASSWORD", "")
    sender = os.getenv("ALERT_EMAIL_FROM", "").strip() or username
    recipient = os.getenv("ALERT_EMAIL_TO", "").strip()
    if not all((host, username, password, sender, recipient)):
        print("Email not configured: set SMTP_HOST, SMTP_USERNAME, SMTP_PASSWORD, ALERT_EMAIL_FROM (optional), ALERT_EMAIL_TO.")
        return False

    message = EmailMessage()
    message["Subject"] = "[Oracle VPS Monitor] " + subject[:160]
    message["From"] = sender
    message["To"] = recipient
    message.set_content(redact(body, 8000))

    try:
        if os.getenv("SMTP_USE_SSL", "false").lower() in {"1", "true", "yes"}:
            with smtplib.SMTP_SSL(host, port, timeout=15) as smtp:
                smtp.login(username, password)
                smtp.send_message(message)
        else:
            with smtplib.SMTP(host, port, timeout=15) as smtp:
                smtp.ehlo()
                smtp.starttls()
                smtp.ehlo()
                smtp.login(username, password)
                smtp.send_message(message)
        return True
    except Exception as exc:
        print(f"Email delivery failed: {redact(str(exc), 500)}")
        return False


def fingerprint(subject: str, details: str) -> str:
    normalized = NOISY_VALUES.sub("[ID]", details.lower())
    normalized = re.sub(r"\b\d{4}-\d{2}-\d{2}[t ][0-9:.+z-]+\b", "[TIME]", normalized)
    normalized = re.sub(r"\b\d{2}:\d{2}:\d{2}(?:\.\d+)?\b", "[TIME]", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()[:800]
    return hashlib.sha256(f"{subject}|{normalized}".encode()).hexdigest()[:24]


def check_http(url: str) -> list[tuple[str, str]]:
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "oracle-vps-monitor/1.0"})
        with urllib.request.urlopen(request, timeout=8) as response:
            if response.status >= 400:
                return [(f"HTTP check failed: {url}", f"HTTP status {response.status}")]
            response.read(1024)
            return []
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return [(f"HTTP check failed: {url}", redact(str(exc), 500))]


def collect_issues() -> dict[str, tuple[str, str]]:
    issues: dict[str, tuple[str, str]] = {}
    for name in CONTAINERS:
        ok, raw = run_docker([
            "inspect", "--format",
            "{{.Name}}|{{.State.Status}}|{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}|{{.RestartCount}}",
            name,
        ])
        if not ok:
            issues[f"container:{name}"] = (f"Container unavailable: {name}", raw or "docker inspect failed")
            continue

        fields = raw.lstrip("/").split("|")
        if len(fields) >= 4:
            status, health, restarts = fields[1], fields[2], fields[3]
            if status != "running":
                issues[f"container:{name}"] = (
                    f"Container not running: {name}",
                    f"Container={name}; status={status}; health={health}; restart_count={restarts}",
                )
            elif health == "unhealthy":
                issues[f"health:{name}"] = (
                    f"Container unhealthy: {name}",
                    f"Container={name}; status={status}; health={health}; restart_count={restarts}",
                )

        stats_ok, stats = run_docker(["stats", "--no-stream", "--format", "{{.CPUPerc}}|{{.MemUsage}}|{{.MemPerc}}", name], timeout=15)
        if stats_ok and stats:
            values = stats.split("|")
            if len(values) == 3:
                try:
                    cpu_pct = float(values[0].strip().rstrip("%"))
                    mem_pct = float(values[2].strip().rstrip("%"))
                    cpu_limit = float(os.getenv("MONITOR_CPU_ALERT_PERCENT", "95"))
                    mem_limit = float(os.getenv("MONITOR_MEMORY_ALERT_PERCENT", "90"))
                    if cpu_pct >= cpu_limit:
                        issues[f"cpu:{name}"] = (
                            f"High CPU usage: {name}",
                            f"Container={name}; cpu_percent={cpu_pct:.1f}; threshold={cpu_limit:.1f}; memory={values[1]}",
                        )
                    if mem_pct >= mem_limit:
                        issues[f"memory:{name}"] = (
                            f"High memory usage: {name}",
                            f"Container={name}; memory_percent={mem_pct:.1f}; threshold={mem_limit:.1f}; memory={values[1]}",
                        )
                except ValueError:
                    pass

        log_ok, logs = run_docker(["logs", "--since", LOG_SINCE, "--tail", str(LOG_TAIL), name], timeout=20)
        if log_ok and logs:
            matches = [line for line in logs.splitlines() if ERROR_RE.search(line)]
            for line in matches[-3:]:
                excerpt = redact(line, 700)
                key = f"log:{name}:{fingerprint(name, excerpt)}"
                issues[key] = (f"Application error observed: {name}", f"Container={name}\nRecent error excerpt: {excerpt}")

    for url in HEALTH_URLS:
        for subject, details in check_http(url):
            issues[f"http:{url}"] = (subject, details)
    return issues


def process_issues(issues: dict[str, tuple[str, str]]) -> None:
    timestamp = now()
    con = db_connect()
    try:
        rows = {row[0]: row for row in con.execute(
            "SELECT fingerprint, subject, details, first_seen, last_seen, status, missed_checks, notified FROM incidents"
        ).fetchall()}

        current_fps = set()
        for key, (subject, details) in issues.items():
            fp = fingerprint(key, details)
            current_fps.add(fp)
            old = rows.get(fp)
            if old is None:
                con.execute(
                    "INSERT INTO incidents(fingerprint,subject,details,first_seen,last_seen,status,missed_checks,notified) VALUES(?,?,?,?,?,'active',0,0)",
                    (fp, subject, details, timestamp, timestamp),
                )
                print(f"NEW INCIDENT: {subject}: {details}")
            else:
                con.execute(
                    """UPDATE incidents
                       SET subject=?, details=?, last_seen=?, status='active', missed_checks=0,
                           first_seen=CASE WHEN status='recovered' THEN ? ELSE first_seen END,
                           notified=CASE WHEN status='recovered' THEN 0 ELSE notified END
                       WHERE fingerprint=?""",
                    (subject, details, timestamp, timestamp, fp),
                )

            row = con.execute(
                "SELECT subject,details,first_seen,last_seen,notified FROM incidents WHERE fingerprint=?", (fp,)
            ).fetchone()
            if row and not row[4]:
                body = (
                    f"Status: ACTIVE\nFirst seen: {row[2]}\nLast seen: {row[3]}\n\n"
                    f"{row[0]}\n\n{row[1]}\n\n"
                    "This monitor is read-only. No restart or deployment was attempted."
                )
                if send_email(row[0], body):
                    con.execute("UPDATE incidents SET notified=1 WHERE fingerprint=?", (fp,))

        for fp, row in rows.items():
            if fp in current_fps or row[5] != "active":
                continue
            missed = row[6] + 1
            if missed >= RECOVERY_MISSES:
                con.execute(
                    "UPDATE incidents SET status='recovered',missed_checks=?,last_seen=? WHERE fingerprint=?",
                    (missed, timestamp, fp),
                )
                print(f"RECOVERED: {row[1]}")
                if row[7]:
                    send_email(
                        f"RECOVERED: {row[1]}",
                        f"Status: RECOVERED\nFirst seen: {row[3]}\nRecovery observed: {timestamp}\n\n"
                        f"{row[1]}\n\nThe issue was absent for {RECOVERY_MISSES} consecutive checks.",
                    )
            else:
                con.execute("UPDATE incidents SET missed_checks=? WHERE fingerprint=?", (missed, fp))
        con.commit()
    finally:
        con.close()


def main() -> None:
    print(f"Oracle VPS monitor starting; interval={INTERVAL}s; containers={','.join(CONTAINERS)}")
    print("Read-only mode: no container mutations are available in this worker.")
    while True:
        started = time.monotonic()
        try:
            issues = collect_issues()
            process_issues(issues)
            print(f"{now()} check complete; current issue fingerprints={len(issues)}")
        except Exception as exc:
            print(f"Monitor iteration failed: {redact(str(exc), 500)}")
        elapsed = time.monotonic() - started
        time.sleep(max(5, INTERVAL - elapsed))


if __name__ == "__main__":
    main()
