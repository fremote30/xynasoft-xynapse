from __future__ import annotations

from pathlib import Path
from email.message import EmailMessage
from datetime import datetime

from openpyxl import Workbook


BASE = Path("sample_files")
BASE.mkdir(exist_ok=True)


def make_xlsx():
    wb = Workbook()
    ws = wb.active
    ws.title = "Employees"

    ws.append(["Name", "Role", "Department"])
    ws.append(["Alice Johnson", "Attorney", "Immigration"])
    ws.append(["Bob Smith", "Paralegal", "Litigation"])
    ws.append(["Carol Lee", "Analyst", "Compliance"])

    path = BASE / "sample.xlsx"
    wb.save(path)
    print(f"✔ Created {path}")


def make_html():
    html = """<!DOCTYPE html>
<html>
<head>
    <title>Xynasoft Xynapse – Sample HTML</title>
</head>
<body>
    <h1>Xynasoft Xynapse</h1>
    <p>This is a <strong>sample HTML</strong> document.</p>

    <h2>Key Features</h2>
    <ul>
        <li>Document ingestion</li>
        <li>Chunking</li>
        <li>Search & retrieval</li>
    </ul>

    <script>
        console.log("This script tag should be ignored");
    </script>
</body>
</html>
"""
    path = BASE / "sample.html"
    path.write_text(html, encoding="utf-8")
    print(f"✔ Created {path}")


def make_eml():
    msg = EmailMessage()
    msg["Subject"] = "Sample Email for Xynapse"
    msg["From"] = "sender@example.com"
    msg["To"] = "receiver@example.com"
    msg["Date"] = datetime.now().strftime("%a, %d %b %Y %H:%M:%S")

    msg.set_content(
        """Hello,

This is a sample EMAIL (.eml) file.

It is used to test:
- Email ingestion
- Header parsing
- Body extraction

Regards,
Xynasoft
"""
    )

    path = BASE / "sample.eml"
    path.write_bytes(msg.as_bytes())
    print(f"✔ Created {path}")


if __name__ == "__main__":
    make_xlsx()
    make_html()
    make_eml()

    print("\nAll sample files generated in ./sample_files/")
