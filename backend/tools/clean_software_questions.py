
import csv
import json
import re
import unicodedata
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]

INPUT_FILE = BACKEND_DIR / "data" / "raw" / "Software Questions.csv"
OUTPUT_DIR = BACKEND_DIR / "data" / "processed"

OUTPUT_CSV = OUTPUT_DIR / "software_questions_clean.csv"
OUTPUT_JSONL = OUTPUT_DIR / "software_questions.jsonl"


def read_csv(path: Path) -> list[dict]:
    raw = path.read_bytes()

    # Nhận diện một số encoding phổ biến của CSV.
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")) or (
        b"\x00" in raw[:200]
    ):
        content = raw.decode("utf-16")
    else:
        try:
            content = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            content = raw.decode("cp1252")

    from io import StringIO

    reader = csv.DictReader(StringIO(content))
    if not reader.fieldnames:
        raise ValueError("CSV không có hàng tiêu đề.")

    # Chuẩn hóa tên cột.
    reader.fieldnames = [
        name.strip().lower() for name in reader.fieldnames
    ]

    required = {
        "question number",
        "question",
        "answer",
        "category",
        "difficulty",
    }
    missing = required - set(reader.fieldnames)

    if missing:
        raise ValueError(
            f"Thiếu các cột bắt buộc: {sorted(missing)}"
        )

    return list(reader)


def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKC", value or "")
    value = re.sub(r"\s+", " ", value.strip())
    return value


def question_key(value: str) -> str:
    # Chỉ dùng để phát hiện câu hỏi trùng.
    # Không thay đổi nội dung câu hỏi gốc.
    return normalize_text(value).casefold()


def main():
    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Không tìm thấy file đầu vào: {INPUT_FILE}"
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    source_rows = read_csv(INPUT_FILE)
    cleaned = []
    seen_questions = set()

    stats = {
        "input_rows": len(source_rows),
        "invalid_rows": 0,
        "duplicate_questions": 0,
        "output_rows": 0,
    }

    for row in source_rows:
        question = normalize_text(row.get("question", ""))
        answer = normalize_text(row.get("answer", ""))
        category = normalize_text(row.get("category", ""))
        difficulty = normalize_text(
            row.get("difficulty", "")
        ).title()

        # Không đưa bản ghi thiếu thông tin chính vào dữ liệu sạch.
        if not question or not answer or not category or not difficulty:
            stats["invalid_rows"] += 1
            continue

        key = question_key(question)

        if key in seen_questions:
            stats["duplicate_questions"] += 1
            continue

        seen_questions.add(key)

        # Sửa một biến thể danh mục đã biết.
        if category.casefold() == "general program":
            category = "General Programming"

        if difficulty not in {"Easy", "Medium", "Hard"}:
            print(
                f"CẢNH BÁO: Độ khó chưa chuẩn hóa: {difficulty!r}"
            )

        cleaned.append({
            "question": question,
            "answer": answer,
            "category": category,
            "difficulty": difficulty,
        })

    stats["output_rows"] = len(cleaned)

    # Xuất CSV đã làm sạch.
    with OUTPUT_CSV.open(
        "w", encoding="utf-8-sig", newline=""
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "question",
                "answer",
                "category",
                "difficulty",
            ],
        )
        writer.writeheader()
        writer.writerows(cleaned)

    # Xuất JSONL để chuẩn bị tích hợp RAG.
    with OUTPUT_JSONL.open(
        "w", encoding="utf-8"
    ) as file:
        for index, row in enumerate(cleaned, start=1):
            record = {
                "id": f"software-question-{index:04d}",
                "question": row["question"],
                "answer": row["answer"],
                "category": row["category"],
                "difficulty": row["difficulty"],
                "text": (
                    f"Question: {row['question']}\n"
                    f"Reference answer: {row['answer']}"
                ),
            }
            file.write(
                json.dumps(record, ensure_ascii=False) + "\n"
            )

    print("\n=== KẾT QUẢ LÀM SẠCH ===")
    for key, value in stats.items():
        print(f"{key}: {value}")

    print(f"\nCSV: {OUTPUT_CSV}")
    print(f"JSONL: {OUTPUT_JSONL}")


if __name__ == "__main__":
    main()
