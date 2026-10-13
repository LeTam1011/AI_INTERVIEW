
from app.ai.answer_evaluator import evaluate_answer

expected_points = [
    "A decorator modifies the behavior of another function "
    "without changing its source code.",
    "Decorators are commonly used for logging and authentication.",
]

test_cases = [
    (
        "Correct Vietnamese answer",
        "Decorator cho phép bổ sung hành vi cho một hàm "
        "mà không phải sửa trực tiếp mã nguồn của hàm đó. "
        "Ví dụ, có thể dùng decorator để kiểm tra quyền đăng nhập "
        "trước khi người dùng gọi một chức năng.",
    ),
    (
        "Partially correct answer",
        "Decorator là một hàm dùng để bổ sung hành vi cho hàm khác.",
    ),
    (
        "Long but irrelevant answer",
        "Python là ngôn ngữ lập trình phổ biến. Tôi từng xây dựng "
        "nhiều ứng dụng web, sử dụng cơ sở dữ liệu, viết API, "
        "làm việc nhóm và triển khai phần mềm.",
    ),
    (
        "Keyword-only answer",
        "Decorator function behavior logging authentication.",
    ),
]

for name, answer in test_cases:
    result = evaluate_answer(answer, expected_points)

    print(f"\n=== {name} ===")
    print(f"Score: {result['total_score']}")
    print(f"Coverage: {result['coverage_score']}")
    print(f"Matched: {result['matched_points']}")
    print(f"Missing: {result['missing_points']}")
    print(f"Feedback: {result['feedback']}")
