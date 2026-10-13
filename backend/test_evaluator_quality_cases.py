
from app.ai.answer_evaluator import evaluate_answer


EXPECTED_POINTS = [
    "Giải thích Python là ngôn ngữ lập trình và nêu cách sử dụng Python để giải quyết bài toán.",
    "Mô tả một tình huống thực tế sử dụng Python hoặc FastAPI để xây dựng API, xử lý dữ liệu JSON và trả kết quả.",
    "Giải thích cách sử dụng try/except để xử lý ngoại lệ và viết unit test để kiểm tra kết quả.",
]

TEST_CASES = [
    {
        "name": "A - Cau tra loi day du",
        "answer": """
        Python là ngôn ngữ lập trình bậc cao, có cú pháp dễ đọc
        và hỗ trợ lập trình hướng đối tượng. Em có thể sử dụng
        Python để xây dựng backend API. Ví dụ, em dùng FastAPI
        tạo API nhận JSON, kiểm tra dữ liệu và trả kết quả.
        Khi xử lý lỗi, em dùng try/except; đồng thời viết unit test
        cho cả trường hợp hợp lệ và không hợp lệ để xác minh kết quả.
        """,
    },
    {
        "name": "B - Cau tra loi mot phan",
        "answer": """
        Em biết Python và đã sử dụng FastAPI để xây dựng một API
        nhận dữ liệu JSON. Em có thể chia chương trình thành các hàm
        nhỏ để xử lý yêu cầu.
        """,
    },
    {
        "name": "C - Cau tra loi lac de",
        "answer": """
        Em rất chăm chỉ, có tinh thần trách nhiệm và thích làm việc
        nhóm. Trong thời gian rảnh, em chơi thể thao, xem phim,
        nghe nhạc và tìm hiểu nhiều chủ đề khác nhau. Em luôn cố gắng
        hoàn thành công việc đúng thời hạn và học hỏi từ đồng nghiệp.
        """,
    },
    {
        "name": "D - Chi nhac tu khoa",
        "answer": """
        Python, FastAPI, try/except, unit test, API, JSON.
        """,
    },
]


def main():
    results = []

    for case in TEST_CASES:
        result = evaluate_answer(
            answer_text=case["answer"],
            expected_points=EXPECTED_POINTS,
        )

        results.append({
            "name": case["name"],
            "score": result["total_score"],
            "coverage": result["coverage_score"],
            "matched": len(result["matched_points"]),
            "missing": len(result["missing_points"]),
        })

        print(f"\n{'=' * 60}")
        print(case["name"])
        print(f"Total score: {result['total_score']}")
        print(f"Coverage: {result['coverage_score']}%")
        print("Matched points:")
        for point in result["matched_points"]:
            print(f"  + {point}")
        print("Missing points:")
        for point in result["missing_points"]:
            print(f"  - {point}")
        print("Feedback:", result["feedback"])

    print(f"\n{'=' * 60}")
    print("TONG HOP")
    for item in results:
        print(
            f"{item['name']}: "
            f"score={item['score']}, "
            f"coverage={item['coverage']}%, "
            f"matched={item['matched']}, "
            f"missing={item['missing']}"
        )

    scores = {item["name"]: item["score"] for item in results}

    print("\nKIEM TRA THU TU DIEM:")
    print(
        "A > B:",
        scores["A - Cau tra loi day du"]
        > scores["B - Cau tra loi mot phan"],
    )
    print(
        "B > C:",
        scores["B - Cau tra loi mot phan"]
        > scores["C - Cau tra loi lac de"],
    )
    print(
        "A > D:",
        scores["A - Cau tra loi day du"]
        > scores["D - Chi nhac tu khoa"],
    )


    print("\nKIEM TRA TUNG TIEU CHI")

    criterion_cases = [
        (
            "Python",
            "Python là ngôn ngữ lập trình bậc cao, "
            "có cú pháp dễ đọc và hỗ trợ lập trình hướng đối tượng.",
            "Giải thích khái niệm và cách hoạt động của Python",
        ),
        (
            "Vi du thuc te",
            "Ví dụ, em dùng FastAPI xây dựng REST API nhận "
            "dữ liệu JSON, kiểm tra đầu vào và trả kết quả.",
            "Đưa ra ví dụ hoặc tình huống thực tế",
        ),
        (
            "Xu ly loi",
            "Em sử dụng try/except để bắt ngoại lệ, viết unit test "
            "cho trường hợp hợp lệ và không hợp lệ, sau đó xác minh "
            "kết quả đầu ra.",
            "Giải thích cách kiểm tra kết quả và xử lý lỗi",
        ),
    ]

    for name, answer, point in criterion_cases:
        result = evaluate_answer(answer, [point])
        print(
            f"{name}: score={result['total_score']}, "
            f"coverage={result['coverage_score']}%, "
            f"matched={len(result['matched_points'])}"
        )


if __name__ == "__main__":
    main()
