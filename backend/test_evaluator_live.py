
import re
from app.ai.semantic_model import get_semantic_model

answer = """
Em sẽ phân tích yêu cầu, chia bài toán thành các hàm nhỏ và sử dụng Python để xử lý dữ liệu.
Ví dụ, khi xây dựng API, em có thể dùng FastAPI để nhận dữ liệu JSON, kiểm tra dữ liệu đầu vào
và trả về kết quả. Em sẽ dùng try/except để xử lý ngoại lệ, viết unit test để kiểm tra các trường hợp
bình thường và trường hợp lỗi, sau đó chạy thử để xác nhận kết quả đúng mong đợi.
"""

points = [
    "Giải thích khái niệm và cách hoạt động của Python",
    "Đưa ra ví dụ hoặc tình huống thực tế",
    "Giải thích cách kiểm tra kết quả và xử lý lỗi",
]

from app.ai.answer_evaluator import evaluate_answer

result = evaluate_answer(
    answer_text=answer,
    expected_points=points,
)

for key, value in result.items():
    print(f"{key}: {value}")