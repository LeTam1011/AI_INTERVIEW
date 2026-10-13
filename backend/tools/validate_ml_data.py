
import csv
import json
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BACKEND_DIR / "data" / "ml"

ANSWER_FILE = DATA_DIR / "answer_scoring" / "train.csv"
CV_FILE = DATA_DIR / "cv_scoring" / "train.csv"
QUESTION_FILE = DATA_DIR / "question_generation" / "train.jsonl"

ANSWER_COLUMNS = {
    "question_text",
    "expected_points",
    "answer_text",
    "score",
    "feedback",
    "career_level",
}

CV_COLUMNS = {
    "cv_text",
    "job_description",
    "career_level",
    "score",
    "matched_skills",
    "missing_skills",
    "feedback",
}

QUESTION_FIELDS = {
    "cv_summary",
    "job_description",
    "career_level",
    "language",
    "question",
    "expected_points",
}



def validate_csv(path: Path, required_columns: set[str]) -> int:
    print(f"\n[CSV] {path.relative_to(BACKEND_DIR)}")

    if not path.exists():
        print("ERROR: Chưa tạo file.")
        return 1

    errors = 0
    valid_rows = 0

    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)

        actual_columns = set(reader.fieldnames or [])
        missing_columns = required_columns - actual_columns

        if not reader.fieldnames:
            print("ERROR: File chưa có hàng tiêu đề.")
            return 1

        if missing_columns:
            print(f"ERROR: Thiếu cột: {sorted(missing_columns)}")
            errors += 1

        for line, row in enumerate(reader, start=2):
            # DictReader dùng key None khi dòng có nhiều cột hơn tiêu đề.
            extra_values = row.pop(None, [])
            if extra_values and any(str(v).strip() for v in extra_values):
                print(
                    f"ERROR dòng {line}: Có dữ liệu thừa "
                    "do sai số lượng cột hoặc dấu phẩy chưa được đặt trong dấu nháy."
                )
                errors += 1
                continue

            # Chuẩn hóa giá trị để không gọi strip() trên list hoặc None.
            row = {
                key: (value.strip() if isinstance(value, str) else "")
                for key, value in row.items()
            }

            if not any(row.values()):
                continue

            row_errors = []

            for column in required_columns:
                if column in actual_columns and not row.get(column):
                    row_errors.append(f"{column} bị trống")

            if "score" in actual_columns:
                try:
                    score = float(row.get("score", ""))
                    if not 0 <= score <= 100:
                        row_errors.append("score phải nằm trong [0, 100]")
                except (TypeError, ValueError):
                    row_errors.append("score phải là số từ 0 đến 100")

            if "career_level" in actual_columns:
                allowed_levels = {"intern", "junior", "middle", "senior"}
                level = row.get("career_level", "").lower()
                if level and level not in allowed_levels:
                    row_errors.append(
                        f"career_level không hợp lệ: {level}"
                    )

            if row_errors:
                errors += 1
                print(f"ERROR dòng {line}: {'; '.join(row_errors)}")
            elif not missing_columns:
                valid_rows += 1

    print(f"Số mẫu hợp lệ: {valid_rows}")

    if valid_rows == 0:
        print("WARNING: Chưa có mẫu hợp lệ để huấn luyện.")

    return errors


def validate_jsonl(path: Path, required_fields: set[str]) -> int:
    print(f"\n[JSONL] {path.relative_to(BACKEND_DIR)}")

    if not path.exists():
        print("ERROR: Chưa tạo file.")
        return 1

    errors = 0
    valid_rows = 0

    with path.open("r", encoding="utf-8-sig") as file:
        for line_number, raw_line in enumerate(file, start=1):
            if not raw_line.strip():
                continue

            try:
                item = json.loads(raw_line)
            except json.JSONDecodeError as exc:
                print(f"ERROR dòng {line_number}: JSON không hợp lệ: {exc}")
                errors += 1
                continue

            if not isinstance(item, dict):
                print(f"ERROR dòng {line_number}: Mỗi dòng phải là object JSON.")
                errors += 1
                continue

            missing = [
                field
                for field in required_fields
                if field not in item or item[field] is None
                or item[field] == ""
            ]

            if missing:
                print(
                    f"ERROR dòng {line_number}: "
                    f"Thiếu trường {sorted(missing)}"
                )
                errors += 1
                continue

            if not isinstance(item["expected_points"], list):
                print(
                    f"ERROR dòng {line_number}: "
                    "expected_points phải là một danh sách."
                )
                errors += 1
                continue

            valid_rows += 1

    print(f"Số mẫu hợp lệ: {valid_rows}")

    if valid_rows == 0:
        print("WARNING: Chưa có mẫu sinh câu hỏi.")

    return errors


def main() -> None:
    total_errors = 0

    total_errors += validate_csv(ANSWER_FILE, ANSWER_COLUMNS)
    total_errors += validate_csv(CV_FILE, CV_COLUMNS)
    total_errors += validate_jsonl(QUESTION_FILE, QUESTION_FIELDS)

    print("\n" + "=" * 50)

    if total_errors:
        print(f"HOÀN TẤT: Phát hiện {total_errors} lỗi dữ liệu.")
        raise SystemExit(1)

    print("HOÀN TẤT: Không phát hiện lỗi cấu trúc.")
    print("Lưu ý: Điều này chưa chứng minh dữ liệu đủ tốt để huấn luyện.")


if __name__ == "__main__":
    main()
