
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

model = SentenceTransformer(MODEL_NAME)

expected_points = [
    "A decorator modifies the behavior of another function "
    "without changing its source code.",
    "Decorators are commonly used for logging and authentication.",
]

test_cases = {
    "Correct Vietnamese answer": (
        "Decorator cho phép bổ sung hành vi cho một hàm mà không "
        "phải sửa trực tiếp mã nguồn của hàm đó. Có thể dùng "
        "decorator để kiểm tra quyền đăng nhập trước khi gọi chức năng."
    ),
    "Partially correct answer": (
        "Decorator là một hàm dùng để bổ sung hành vi cho hàm khác."
    ),
    "Long but irrelevant answer": (
        "Python là ngôn ngữ lập trình phổ biến. Tôi từng xây dựng "
        "ứng dụng web, làm việc với cơ sở dữ liệu và triển khai API."
    ),
    "Keyword-only answer": (
        "Decorator function behavior logging authentication."
    ),
}

criteria_embeddings = model.encode(
    expected_points,
    normalize_embeddings=True,
)

for name, answer in test_cases.items():
    answer_embedding = model.encode(
        [answer],
        normalize_embeddings=True,
    )

    similarities = cosine_similarity(
        answer_embedding,
        criteria_embeddings,
    )[0]

    print(f"\n=== {name} ===")
    for criterion, score in zip(expected_points, similarities):
        print(f"Similarity: {score:.4f} | {criterion}")

    print(f"Mean similarity: {similarities.mean():.4f}")
