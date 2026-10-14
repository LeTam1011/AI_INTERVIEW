import json
import re
from pathlib import Path
from collections import Counter

root = Path("dataset_pipeline/data/chunk_final_test")
files = sorted(root.glob("chunked_*.json"))
if len(files) != 13:
    raise SystemExit(f"STOP: expected 13 JSON files, found {len(files)}")

records = []
for path in files:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    for item in data:
        records.append((path.name, item))

ids = [str(x.get("id", "")) for _, x in records]
questions = [
    (filename, re.sub(r"\W+", " ", str(x.get("question", "")).casefold()).strip())
    for filename, x in records
]
duplicate_ids = [k for k, n in Counter(ids).items() if n > 1]
duplicate_questions = [k for k, n in Counter(questions).items() if k[1] and n > 1]

checks = {
    "Related Read / article": re.compile(r"related\s+read|read more|must-have resume skills", re.I),
    "Chapter heading": re.compile(r"(?im)^\s*chapter\s+\d+\b"),
    "Injected year placeholder": re.compile(r"curent_year|\[\[current_year\]\]", re.I),
    "Powered By": re.compile(r"powered\s+by", re.I),
    "Question heading in answer": re.compile(
        r"(?im)^\s*\d+\s*[.)]\s*(?:#{1,6}\s*)?(?:what is|how do|how can|explain|define|"
        r"which|why |when |name |list |describe|design |differentiate|does |can )"
    ),
    "Spring editorial heading": re.compile(
        r"(?i)spring\s+(?:framework\s+)?(?:scenario based\s+)?interview questions"
    ),
    "Standalone article headings": re.compile(
        r"(?im)^\s*#{1,6}\s*(?:benefits|conclusion|related articles|see also)\b"
    ),
}

findings = {name: [] for name in checks}
empty_q, empty_a, mismatch, short_answers = [], [], [], []
total = 0

for filename, item in records:
    total += 1
    rid = str(item.get("id", ""))
    q = str(item.get("question", "")).strip()
    a = str(item.get("answer", "")).strip()

    if not q:
        empty_q.append((filename, rid))
    if not a:
        empty_a.append((filename, rid))
    if item.get("content") != f"Question: {q}\n\nAnswer: {a}":
        mismatch.append((filename, rid))
    if 0 < len(a.split()) < 15:
        short_answers.append((filename, rid, q, a[:180]))

    for label, pattern in checks.items():
        if pattern.search(a):
            findings[label].append((filename, rid, q, a[:220]))

lines = [
    "FINAL CONTENT AUDIT",
    f"Files: {len(files)}",
    f"Records: {total}",
    f"Duplicate IDs: {len(duplicate_ids)}",
    f"Duplicate question texts: {len(duplicate_questions)}",
    f"Empty questions: {len(empty_q)}",
    f"Empty answers: {len(empty_a)}",
    f"Content mismatches: {len(mismatch)}",
    f"Answers under 15 words (review, not automatic errors): {len(short_answers)}",
]

for label, matches in findings.items():
    lines.append(f"{label}: {len(matches)}")

lines += ["", "DETAILS"]
for label, matches in findings.items():
    lines.append(f"\n[{label}]")
    lines.extend(map(str, matches))

lines += ["\n[SHORT ANSWERS - REVIEW ONLY]"]
lines.extend(map(str, short_answers))
lines += ["\n[STRUCTURAL ERRORS]"]
lines.extend(map(str, [
    ("duplicate_ids", duplicate_ids),
    ("duplicate_questions", duplicate_questions),
    ("empty_questions", empty_q),
    ("empty_answers", empty_a),
    ("content_mismatches", mismatch),
]))

report = root / "final_content_audit.txt"
report.write_text("\n".join(lines), encoding="utf-8")
print("\n".join(lines[:20]))
print("\nFull report:", report)
print("No JSON or ChromaDB collections were modified.")
