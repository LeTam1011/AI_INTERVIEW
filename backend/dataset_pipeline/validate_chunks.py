
import json
import re
from collections import Counter
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
CHUNK_DIR = BASE_DIR / "data" / "chunk"


def normalize(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^\w\s]", "", text)
    return text


def main():
    files = sorted(CHUNK_DIR.glob("chunked_*.json"))

    if not files:
        print(f"No chunk files found in {CHUNK_DIR}")
        return

    total = 0
    empty_questions = []
    empty_answers = []
    duplicates = []
    missing_metadata = []
    seen_questions = {}

    for path in files:
        try:
            chunks = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            print(f"[ERROR] {path.name}: {exc}")
            continue

        if not isinstance(chunks, list):
            print(f"[ERROR] {path.name}: JSON root must be a list")
            continue

        file_total = len(chunks)
        total += file_total

        for chunk in chunks:
            chunk_id = chunk.get("id", "unknown")
            question = str(chunk.get("question", "")).strip()
            answer = str(chunk.get("answer", "")).strip()
            metadata = chunk.get("metadata") or {}

            if not question:
                empty_questions.append((path.name, chunk_id))

            if not answer:
                empty_answers.append((path.name, chunk_id))

            if not metadata.get("topic") or not metadata.get("source"):
                missing_metadata.append((path.name, chunk_id))

            key = normalize(question)
            if key:
                if key in seen_questions:
                    duplicates.append(
                        (question, seen_questions[key], f"{path.name}:{chunk_id}")
                    )
                else:
                    seen_questions[key] = f"{path.name}:{chunk_id}"

        print(f"{path.name}: {file_total} chunks")

    print("\n" + "=" * 60)
    print(f"Total chunks: {total}")
    print(f"Questions without text: {len(empty_questions)}")
    print(f"Answers without text: {len(empty_answers)}")
    print(f"Duplicate questions: {len(duplicates)}")
    print(f"Missing metadata: {len(missing_metadata)}")

    for title, entries in [
        ("EMPTY QUESTIONS", empty_questions),
        ("EMPTY ANSWERS", empty_answers),
        ("MISSING METADATA", missing_metadata),
    ]:
        if entries:
            print(f"\n--- {title} (first 10) ---")
            for entry in entries[:10]:
                print(entry)

    if duplicates:
        print("\n--- DUPLICATE QUESTIONS (first 10) ---")
        for question, first, duplicate in duplicates[:10]:
            print(f"{question}\n  First: {first}\n  Duplicate: {duplicate}")


if __name__ == "__main__":
    main()
