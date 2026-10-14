import json
import shutil
from pathlib import Path

root = Path("dataset_pipeline/data/chunk_final_test")
backup = Path("dataset_pipeline/data/chunk_final_test_backup_before_short_answer_fixes")

fixes = {
    ("chunked_da_interview_question.json", "da_interview_question-0051"): {
        "expected": "Do you have experience making data analytics presentations to stakeholders?",
        "answer": (
            "[Personalized response guidance] Describe a real presentation you made "
            "for stakeholders. Explain the business question, the data and tools used "
            "(for example, Tableau or PowerPoint), the main finding, and how your "
            "recommendation helped the audience make a decision. Replace this guidance "
            "with your own experience; do not claim experience you do not have."
        ),
    },
    ("chunked_da_interview_question.json", "da_interview_question-0068"): {
        "expected": "Which steps of a data analytics project do you enjoy working on most and why?",
        "answer": (
            "[Personalized response guidance] Choose the project stage you genuinely "
            "enjoy most, such as data cleaning, exploratory data analysis, modeling, "
            "or visualization. Explain why, give a specific example, and describe "
            "the value your work produced. This is a personal question, so there is "
            "no single correct answer."
        ),
    },
    ("chunked_java_interview_question.json", "java_interview_question-0059"): {
        "expected": "What is a layout manager",
        "answer": (
            "A layout manager in Java AWT/Swing controls how components are sized "
            "and positioned inside a container. Examples include FlowLayout, "
            "BorderLayout, and GridLayout."
        ),
    },
    ("chunked_java_interview_question.json", "java_interview_question-0061"): {
        "expected": "Which Swing methods are thread-safe",
        "answer": (
            "Commonly documented thread-safe Swing methods include repaint(), "
            "revalidate(), and invalidate(). Most other Swing component operations "
            "should be performed on the Event Dispatch Thread (EDT) to avoid "
            "threading problems. Check the documentation for the specific component "
            "and Java version when thread-safety matters."
        ),
    },
    ("chunked_java_interview_question.json", "java_interview_question-0062"): {
        "expected": "Name three Component subclasses that support painting",
        "answer": (
            "Examples of AWT Component subclasses that support painting include "
            "Canvas, Panel, Frame, and Applet. Applet is deprecated and has been "
            "removed from modern Java releases, so Canvas, Panel, and Frame are "
            "more relevant examples for current discussions."
        ),
    },
    ("chunked_java_interview_question.json", "java_interview_question-0104"): {
        "expected": "Which protocol will be used by browser and servlet to communicate",
        "answer": (
            "A browser communicates with a Java servlet using HTTP request and "
            "response messages. HTTPS is HTTP protected by TLS and should be used "
            "when the connection needs confidentiality and integrity."
        ),
    },
    ("chunked_javascript_interview_question.json", "javascript_interview_question-0098"): {
        "expected": "What is the use of preventDefault method",
        "answer": (
            "event.preventDefault() prevents the browser's default action for an "
            "event, provided that the event is cancelable. For example, it can "
            "stop a form's default submission so JavaScript can validate the form "
            "first. It does not stop event propagation; stopPropagation() is used "
            "for that purpose."
        ),
    },
    ("chunked_javascript_interview_question.json", "javascript_interview_question-0136"): {
        "expected": "How do you generate random integers",
        "answer": (
            "For a random integer between min and max, inclusive, use: "
            "Math.floor(Math.random() * (max - min + 1)) + min. For example, "
            "Math.floor(Math.random() * 10) generates an integer from 0 through 9. "
            "Math.random() itself returns a floating-point number greater than or "
            "equal to 0 and less than 1."
        ),
    },
    ("chunked_javascript_interview_question.json", "javascript_interview_question-0176"): {
        "expected": "How do you get enumerable key and value pairs",
        "answer": (
            "Use Object.entries(obj) to get an array of the object's own enumerable "
            "string-keyed [key, value] pairs. Example: "
            "Object.entries({ name: 'An', age: 20 }) returns "
            "[['name', 'An'], ['age', 20]]. It does not include inherited or "
            "symbol-keyed properties."
        ),
    },
    ("chunked_javascript_interview_question.json", "javascript_interview_question-0188"): {
        "expected": "How do you print the contents of web page",
        "answer": (
            "Call window.print() to open the browser's print dialog for the current "
            "document. Example: button.addEventListener('click', () => window.print()). "
            "The user can then print the page or save it as a PDF, depending on "
            "the browser and available options."
        ),
    },
    ("chunked_javascript_interview_question.json", "javascript_interview_question-0211"): {
        "expected": "How do you sort elements in an array",
        "answer": (
            "Use array.sort() to sort an array in place. For numeric ascending order, "
            "use numbers.sort((a, b) => a - b); without a comparator, values are "
            "sorted as strings by default. To keep the original array unchanged, "
            "copy it first, for example [...numbers].sort((a, b) => a - b)."
        ),
    },
}

# Validate every file, ID, and question before changing anything.
loaded = {}
errors = []

for (filename, rid), data in fixes.items():
    path = root / filename
    if not path.is_file():
        errors.append(f"Missing file: {filename}")
        continue

    if path not in loaded:
        try:
            loaded[path] = json.loads(path.read_text(encoding="utf-8-sig"))
        except Exception as exc:
            errors.append(f"Invalid JSON: {filename}: {exc}")
            continue

    matches = [x for x in loaded[path] if x.get("id") == rid]
    if len(matches) != 1:
        errors.append(f"{filename} | {rid}: found {len(matches)} records")
        continue

    question = str(matches[0].get("question", ""))
    if data["expected"].casefold() not in question.casefold():
        errors.append(
            f"Question mismatch: {filename} | {rid} | actual={question!r}"
        )

if errors:
    print("STOP - no files modified:")
    print("\n".join(errors))
    raise SystemExit(2)

if backup.exists():
    raise SystemExit(
        f"STOP: backup already exists: {backup}\n"
        "Rename it or choose a new backup path before running again."
    )

# Preserve the current state, including all earlier knowledge fixes.
shutil.copytree(root, backup)
print("BACKUP:", backup)

# Apply changes only after all targets have passed validation.
for (filename, rid), data in fixes.items():
    path = root / filename
    item = next(x for x in loaded[path] if x.get("id") == rid)
    item["answer"] = data["answer"]
    item["content"] = f"Question: {item['question']}\n\nAnswer: {data['answer']}"

for path, records in loaded.items():
    path.write_text(
        json.dumps(records, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

print(f"\nCHANGED: {len(fixes)}")
for filename, rid in fixes:
    item = next(x for x in loaded[root / filename] if x.get("id") == rid)
    print("OK:", rid, "|", item["question"])

# Basic post-write integrity checks.
all_ids = []
empty_questions = []
empty_answers = []
content_mismatch = []
total = 0

for path in sorted(root.glob("chunked_*.json")):
    records = json.loads(path.read_text(encoding="utf-8"))
    total += len(records)

    for item in records:
        rid = item.get("id", "")
        q = str(item.get("question", "")).strip()
        a = str(item.get("answer", "")).strip()
        all_ids.append(rid)

        if not q:
            empty_questions.append((path.name, rid))
        if not a:
            empty_answers.append((path.name, rid))
        if item.get("content") != f"Question: {q}\n\nAnswer: {a}":
            content_mismatch.append((path.name, rid))

print("\nPOST-CHECK")
print("Files:", len(list(root.glob("chunked_*.json"))))
print("Records:", total)
print("Duplicate IDs:", len(all_ids) - len(set(all_ids)))
print("Empty questions:", len(empty_questions))
print("Empty answers:", len(empty_answers))
print("Content mismatches:", len(content_mismatch))
print("ChromaDB: unchanged.")
