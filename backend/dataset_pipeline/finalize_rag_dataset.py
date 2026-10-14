import json
import re
from pathlib import Path
from collections import Counter

src = Path("dataset_pipeline/data/chunk_clean_test")
dst = Path("dataset_pipeline/data/chunk_final_test")

if not src.is_dir():
    raise SystemExit(f"Khong tim thay thu muc: {src}")

files = sorted(src.glob("chunked_*.json"))
if len(files) != 13:
    raise SystemExit(f"Can 13 file JSON, nhung tim thay {len(files)}. Dung de kiem tra.")

# Khong ghi de ket qua cu neu da ton tai.
if dst.exists():
    raise SystemExit(f"Thu muc {dst} da ton tai. Hay doi ten hoac sao luu thu muc nay truoc.")

noise = re.compile(
    r"^\s*(?:#{1,6}\s*)?(?:"
    r"Chapter\s+\d+\b|Related\s+Read\b|Powered\s+By\b|"
    r"Technical\s+SQL\s+Interview\s+Questions\b|"
    r"Spring\s+(?:Framework\s+)?Interview\s+Questions\s+for\s+Experienced\b|"
    r"Spring\s+Interview\s+Questions\s+for\s+\d+\s+Years?\s+Experienced\b|"
    r"Spring\s+Scenario\s+Based\s+Interview\s+Questions\b"
    r")",
    re.I,
)
numbered_heading = re.compile(r"^\s*\d+\s*[.)]\s*#{1,6}\s+.+$")

git_fix = """1. Run `git status` to locate the conflicted files.
2. Open each conflicted file and locate `<<<<<<<`, `=======`, and `>>>>>>>`.
3. Edit the file to keep the intended changes and remove the conflict markers.
4. Save the file and run `git add <file_name>`.
5. Run `git commit` to complete the merge commit process."""

dst.mkdir(parents=True)
total = 0
all_ids = []
empty = []
residual = []
edited = []

for file in files:
    records = json.loads(file.read_text(encoding="utf-8-sig"))
    for item in records:
        rid = item.get("id", "")
        q = str(item.get("question", "")).strip()
        answer = str(item.get("answer", "")).replace("\r\n", "\n")
        kept = []

        for line in answer.split("\n"):
            # Cat phan noi dung bat dau tu heading cau hoi/phan tiep theo.
            if numbered_heading.match(line) or noise.match(line):
                edited.append((file.name, rid, line.strip()[:100]))
                break
            # Xoa dong chua marker nam trong noi dung quang ba.
            if "curent_year" in line.lower():
                edited.append((file.name, rid, "curent_year"))
                continue
            kept.append(line)

        answer = "\n".join(kept).strip()

        if rid == "git_interview_question-0022":
            answer = git_fix
            edited.append((file.name, rid, "Sua danh sach buoc Merge Conflict"))

        item["question"] = q
        item["answer"] = answer
        item["content"] = f"Question: {q}" + (f"\n\nAnswer: {answer}" if answer else "")
        item.setdefault("metadata", {})["answer_status"] = "available" if answer else "pending"

        if not q or not answer:
            empty.append((file.name, rid, bool(q), bool(answer)))
        all_ids.append(rid)

    (dst / file.name).write_text(
        json.dumps(records, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    total += len(records)
    print(f"{file.name}: {len(records)} records")

duplicates = [x for x, n in Counter(all_ids).items() if n > 1]

report = [
    f"Files: {len(files)}",
    f"Records: {total}",
    f"Duplicate IDs: {len(duplicates)}",
    f"Empty question/answer: {len(empty)}",
    f"Changed/truncated lines: {len(edited)}",
    "",
    "EMPTY:",
    *map(str, empty),
    "",
    "DUPLICATE IDS:",
    *map(str, duplicates),
    "",
    "EDITS:",
    *map(str, edited),
]
(dst / "validation_report.txt").write_text("\n".join(report), encoding="utf-8")
print("\n".join(report[:6]))
print(f"\nKet qua: {dst}")
print(f"Bao cao: {dst / 'validation_report.txt'}")
print("Chua tao hoac sua bat ky collection ChromaDB nao.")
