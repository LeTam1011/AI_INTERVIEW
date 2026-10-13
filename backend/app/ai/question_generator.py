
from typing import Any


def build_expected_points(skill: str, topic: str) -> list[str]:
    """Tạo tiêu chí đánh giá phù hợp với kỹ năng và chủ đề."""
    name = skill.strip() or "công nghệ được hỏi"
    key = f"{name} {topic}".casefold()

    # Câu hỏi kinh nghiệm dự án.
    if any(k in key for k in ("project", "dự án", "website quản lý")):
        return [
            "Nêu mục tiêu, yêu cầu và kiến trúc chính của dự án.",
            "Giải thích rõ phần việc cá nhân và lý do lựa chọn công nghệ.",
            "Nêu một khó khăn kỹ thuật, cách xử lý và kết quả.",
        ]

    # Python.
    if "python" in key:
        return [
            "Giải thích khái niệm hoặc cơ chế Python liên quan trực tiếp câu hỏi.",
            "Đưa ra ví dụ Python phù hợp và giải thích cách hoạt động.",
            "Giải thích cách kiểm tra kết quả hoặc xử lý ngoại lệ khi cần.",
        ]

    # REST API / FastAPI.
    if any(k in key for k in ("rest", "api", "fastapi", "http")):
        return [
            "Giải thích mục đích và nguyên tắc hoạt động của API được hỏi.",
            "Nêu phương thức HTTP, endpoint hoặc cấu trúc request/response phù hợp.",
            "Đưa ra ví dụ thực tế và cách xử lý mã trạng thái hoặc lỗi.",
        ]

    # SQL / PostgreSQL / database.
    if any(k in key for k in ("sql", "postgres", "database", "cơ sở dữ liệu")):
        return [
            "Giải thích khái niệm SQL hoặc cơ chế cơ sở dữ liệu liên quan.",
            "Đưa ra câu truy vấn hoặc ví dụ thao tác dữ liệu phù hợp.",
            "Giải thích cách kiểm tra kết quả và tránh lỗi dữ liệu phổ biến.",
        ]

    # JavaScript / React.
    if any(k in key for k in ("javascript", "js", "react", "frontend")):
        return [
            "Giải thích khái niệm hoặc cơ chế JavaScript/React được hỏi.",
            "Đưa ra ví dụ mã hoặc tình huống sử dụng phù hợp.",
            "Giải thích cách kiểm tra kết quả và xử lý vấn đề thường gặp.",
        ]

    # Git.
    if "git" in key:
        return [
            "Giải thích lệnh hoặc khái niệm Git liên quan đến câu hỏi.",
            "Nêu quy trình sử dụng trong một tình huống phát triển phần mềm.",
            "Giải thích cách kiểm tra trạng thái và xử lý xung đột khi phù hợp.",
        ]

    # Giải quyết vấn đề.
    if any(k in key for k in ("problem_solving", "debug", "debugging")):
        return [
            "Xác định hiện tượng và đưa ra giả thuyết về nguyên nhân.",
            "Trình bày các bước kiểm tra và lý do lựa chọn cách xử lý.",
            "Nêu cách xác minh kết quả và phòng tránh lỗi tái diễn.",
        ]

    # Phù hợp công việc / hành vi.
    if any(k in key for k in ("job_fit", "behavioral", "motivation")):
        return [
            "Liên hệ kinh nghiệm hoặc kỹ năng với yêu cầu công việc.",
            "Đưa ra ví dụ cụ thể thể hiện vai trò và kết quả của bản thân.",
            "Nêu điểm cần cải thiện và kế hoạch thực hiện phù hợp.",
        ]

    return [
        f"Giải thích khái niệm và mục đích sử dụng của {name}.",
        f"Mô tả một tình huống thực tế áp dụng {name} và cách thực hiện.",
        f"Giải thích cách kiểm tra kết quả hoặc xử lý lỗi khi sử dụng {name}.",
    ]


def generate_questions(
    context_snapshot: dict[str, Any],
    count: int = 10,
) -> list[dict[str, Any]]:
    """Tạo câu hỏi dựa trên CV, JD và cấp độ ứng viên."""
    if count <= 0:
        return []

    context = context_snapshot or {}
    cv_score = context.get("cv_score") or {}
    job = context.get("job") or {}
    profile = context.get("candidate_profile") or {}

    level = context.get("career_level", "intern")
    language = context.get("language", "vi")

    matched = cv_score.get("matched_required_skills") or []
    missing = cv_score.get("missing_required_skills") or []
    preferred = cv_score.get("matched_preferred_skills") or []

    questions: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add(
        question_text: str,
        topic: str,
        expected_points: list[str],
        reason: str,
        difficulty: str = "medium",
        question_type: str = "technical",
    ) -> None:
        if len(questions) >= count:
            return

        normalized = question_text.strip().casefold()
        if not normalized or normalized in seen:
            return

        seen.add(normalized)
        questions.append({
            "position": len(questions) + 1,
            "question_text": question_text,
            "question_type": question_type,
            "topic": topic[:120],
            "expected_points": expected_points,
            "source_context": {
                "reason": reason,
                "difficulty": difficulty,
                "career_level": level,
                "job_title": job.get("title", ""),
                "cv_score": cv_score.get("overall_score"),
                "language": language,
            },
        })

    # 1. Ưu tiên kỹ năng bắt buộc CV chưa thể hiện rõ.
    for skill in missing:
        name = str(skill)
        add(
            f"Bạn sẽ sử dụng {name} như thế nào để giải quyết "
            "một vấn đề thực tế trong công việc?",
            name,
            build_expected_points(name, name),
            f"CV chưa thể hiện rõ kỹ năng bắt buộc: {name}",
        )

    # 2. Xác minh chiều sâu kỹ năng đã có trong CV.
    for skill in matched:
        name = str(skill)
        add(
            f"Hãy mô tả một tình huống cụ thể bạn đã sử dụng "
            f"{name}, lý do lựa chọn và kết quả đạt được.",
            name,
            build_expected_points(name, "project"),
            f"Kiểm tra chiều sâu kỹ năng {name} trong CV",
        )

    # 3. Kỹ năng ưu tiên trong JD.
    for skill in preferred:
        name = str(skill)
        add(
            f"Bạn biết gì về {name} và có thể áp dụng nó "
            "trong trường hợp thực tế nào?",
            name,
            build_expected_points(name, name),
            f"Đánh giá kỹ năng ưu tiên trong JD: {name}",
        )

    # 4. Kinh nghiệm dự án trong CV.
    projects = profile.get("projects") or []
    if isinstance(projects, list):
        for project in projects[:3]:
            if isinstance(project, dict):
                name = (
                    project.get("name")
                    or project.get("title")
                    or "một dự án trong CV"
                )
            else:
                name = str(project)

            add(
                f"Hãy trình bày vai trò của bạn trong {name}, "
                "thách thức lớn nhất và cách giải quyết.",
                "project",
                build_expected_points(str(name), "project"),
                f"Đào sâu kinh nghiệm dự án: {name}",
                question_type="cv_based",
            )

    # 5. Giải quyết vấn đề theo cấp độ.
    if level in ("intern", "fresher"):
        difficulty = "easy"
        problem = (
            "Hãy trình bày cách bạn tiếp cận một lỗi kỹ thuật "
            "chưa từng gặp trước đây."
        )
    elif level == "junior":
        difficulty = "medium"
        problem = (
            "Khi một chức năng hoạt động không đúng mong đợi, "
            "bạn sẽ tìm nguyên nhân và sửa lỗi theo những bước nào?"
        )
    else:
        difficulty = "hard"
        problem = (
            "Bạn sẽ thiết kế và đánh giá giải pháp kỹ thuật "
            "để đáp ứng khả năng mở rộng, độ tin cậy "
            "và khả năng bảo trì như thế nào?"
        )

    add(
        problem,
        "problem_solving",
        build_expected_points("problem solving", "problem_solving"),
        f"Đánh giá giải quyết vấn đề ở cấp độ {level}",
        difficulty,
        question_type="situational",
    )

    # 6. Mức độ phù hợp với công việc.
    job_title = job.get("title") or "vị trí đang ứng tuyển"
    add(
        f"Bạn có thể đóng góp những gì cho vị trí {job_title}, "
        "và cần cải thiện kỹ năng nào để đáp ứng công việc?",
        "job_fit",
        build_expected_points(str(job_title), "job_fit"),
        f"Đánh giá mức độ phù hợp với vị trí {job_title}",
        "easy",
        question_type="behavioral",
    )

    result = questions[:count]
    for index, question in enumerate(result, start=1):
        question["position"] = index

    return result
