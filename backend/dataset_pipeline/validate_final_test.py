import json
import re
from pathlib import Path
from collections import Counter

root = Path("dataset_pipeline/data/chunk_final_test")
if not root.is_dir():
    raise SystemExit(f"Khong tim thay thu muc: {root}")

fixes = {
    ("chunked_nodejs_interview_question.json", "nodejs_interview_question-0017"): (
        "Using Node.js's built-in http module:\n\n"
        "```js\n"
        "const http = require('http');\n"
        "const server = http.createServer((req, res) => {\n"
        "  res.writeHead(200, { 'Content-Type': 'text/plain; charset=utf-8' });\n"
        "  res.end('Hello, world!');\n"
        "});\n"
        "server.listen(3000, () => console.log('Server running on port 3000'));\n"
        "```\n\n"
        "The request handler receives the request and response objects. "
        "It sends an HTTP 200 response with a text body, and the server listens "
        "for incoming connections on port 3000."
    ),
    ("chunked_ml_interview_question.json", "ml_interview_question-0022"): (
        "The Box-Cox transformation is a family of power transformations for "
        "strictly positive data. It can help stabilize variance and make data "
        "closer to normally distributed, which may be useful for some statistical "
        "models. It does not guarantee normality, and the transformation's "
        "suitability should be checked against the data and model assumptions."
    ),
    ("chunked_ml_interview_question.json", "ml_interview_question-0023"): (
        "Batch gradient descent computes each gradient using the full training "
        "dataset, which can make updates stable but computationally expensive on "
        "large datasets. Stochastic gradient descent updates parameters using one "
        "training example per step, so each update is cheaper but noisier. SGD can "
        "make progress through noisy regions of the loss surface, but it is not "
        "guaranteed to escape every local minimum or to be faster in every setting. "
        "Mini-batch gradient descent is commonly used as a compromise."
    ),
}

# Validate all targets before modifying any file.
loaded = {}
errors = []

for (filename, rid), new_answer in fixes.items():
    path = root / filename
    if not path.is_file():
        errors.append(f"Missing file: {filename}")
        continue
    if path not in loaded:
        loaded[path] = json.loads(path.read_text(encoding="utf-8-sig"))
    matches = [x for x in loaded[path] if x.get("id") == rid]
    if len(matches) != 1:
        errors.append(f"{filename} | {rid}: found {len(matches)} records")

if errors:
    print("STOP - chua sua file:")
    print("\n".join(errors))
    raise SystemExit(2)

for (filename, rid), new_answer in fixes.items():
    path = root / filename
    item = next(x for x in loaded[path] if x.get("id") == rid)
    item["answer"] = new_answer
    item["content"] = f"Question: {item['question']}\n\nAnswer: {new_answer}"
    item.setdefault("metadata", {})["answer_status"] = "available"

for path, records in loaded.items():
    path.write_text(
        json.dumps(records, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

print("KNOWLEDGE FIXES:")
for (filename, rid) in fixes:
    print("OK:", filename, rid)

# Full read-only validation of the resulting test dataset.
files = sorted(root.glob("chunked_*.json"))
all_ids = []
all_questions = []
empty_q = []
empty_a = []
content_mismatch = []
noise = []
next_headings = []
short_answers = []
total = 0

noise_patterns = {
    "Related Read": re.compile(r"Related\s+Read", re.I),
    "curent_year": re.compile(r"curent_year", re.I),
    "Powered By": re.compile(r"Powered\s+By", re.I),
    "Chapter N": re.compile(r"\bChapter\s+\d+\b", re.I),
    "Spring article": re.compile(
        r"Spring\s+(?:Framework\s+)?Interview Questions for Experienced", re.I
    ),
}
next_heading = re.compile(r"(?m)^\s*\d+\s*[.)]\s*#{1,6}\s+.+$")

for path in files:
    records = json.loads(path.read_text(encoding="utf-8-sig"))
    total += len(records)

    for item in records:
        rid = str(item.get("id", ""))
        q = str(item.get("question", "")).strip()
        a = str(item.get("answer", "")).strip()
        content = str(item.get("content", ""))

        all_ids.append(rid)
        all_questions.append((path.name, re.sub(r"\W+", " ", q.casefold()).strip()))

        if not q:
            empty_q.append((path.name, rid))
        if not a:
            empty_a.append((path.name, rid))
        if content != f"Question: {q}\n\nAnswer: {a}":
            content_mismatch.append((path.name, rid))
        if 0 < len(a.split()) < 15:
            short_answers.append((path.name, rid, q, a[:100]))

        for label, pattern in noise_patterns.items():
            if pattern.search(a):
                noise.append((label, path.name, rid, q))
        if next_heading.search(a):
            next_headings.append((path.name, rid, q))

duplicate_ids = [(k, v) for k, v in Counter(all_ids).items() if v > 1]
duplicate_questions = [
    (k, v) for k, v in Counter(all_questions).items()
    if k[1] and v > 1
]

report = [
    "FINAL TEST DATASET VALIDATION",
    f"Files: {len(files)}",
    f"Records: {total}",
    f"Duplicate IDs: {len(duplicate_ids)}",
    f"Empty questions: {len(empty_q)}",
    f"Empty answers: {len(empty_a)}",
    f"Content field mismatches: {len(content_mismatch)}",
    f"Possible noise matches: {len(noise)}",
    f"Numbered headings inside answers: {len(next_headings)}",
    f"Duplicate question texts across files: {len(duplicate_questions)}",
    f"Answers under 15 words (review only): {len(short_answers)}",
    "",
    "DUPLICATE IDS:", *map(str, duplicate_ids),
    "EMPTY QUESTIONS:", *map(str, empty_q),
    "EMPTY ANSWERS:", *map(str, empty_a),
    "CONTENT MISMATCHES:", *map(str, content_mismatch),
    "POSSIBLE NOISE:", *map(str, noise),
    "NUMBERED HEADINGS:", *map(str, next_headings),
    "DUPLICATE QUESTIONS:", *map(str, duplicate_questions),
    "SHORT ANSWERS:", *map(str, short_answers),
]

report_path = root / "final_validation_report_v2.txt"
report_path.write_text("\n".join(report), encoding="utf-8")
print("\n" + "\n".join(report[:12]))
print("\nFull report:", report_path)
print("ChromaDB: unchanged.")
