import json
import shutil
from pathlib import Path

BASE = Path("dataset_pipeline/data")
ROOT = BASE / "chunk_final_test"
BACKUP = BASE / "chunk_final_test_backup_before_last_fixes"

FIXES = {
    "javascript_interview_question-0293": {
        "question": "What are the list of cases error thrown from non-strict mode to strict mode",
        "answer": """Strict mode ('use strict') applies stricter rules to JavaScript code. Some operations that are allowed or fail silently in non-strict mode become errors.

Examples:

1. Legacy octal literals such as `022` cause a SyntaxError in strict mode.
2. Using a `with` statement causes a SyntaxError.
3. Deleting an unqualified identifier, such as `delete variableName`, causes a SyntaxError.
4. Using `eval` or `arguments` as a variable name or function parameter causes a SyntaxError.
5. Using reserved words as identifiers can cause a SyntaxError.
6. Assigning a value to an undeclared variable causes a ReferenceError.
7. Assigning a value to certain non-writable properties can cause a TypeError.

Note: Function declarations inside blocks have different scoping rules in strict mode. Accessing such a function outside its block may cause a ReferenceError, depending on the code.

These stricter rules help detect programming mistakes earlier."""
    },
    "javascript_interview_question-0331": {
        "question": "What are tasks in event loop",
        "answer": """In JavaScript, a task is a unit of work scheduled for execution by the event loop.

Common sources of tasks include:

1. Executing a script.
2. Processing user interaction events.
3. Running callbacks scheduled by setTimeout() or setInterval().

Tasks are processed through task queues according to the scheduling rules of the JavaScript runtime.

Microtasks are handled separately. For example, Promise reaction callbacks and queueMicrotask() callbacks are placed in the microtask queue.

After a task completes, the runtime typically processes pending microtasks before selecting another task.

This distinction explains why Promise callbacks commonly execute before setTimeout(..., 0) callbacks when both are scheduled during the same task."""
    },
    "react_interview_question-0170": {
        "question": "In which scenarios do error boundaries not catch errors?",
        "answer": """React error boundaries primarily handle errors thrown while rendering descendant components.

They do not normally catch errors in these situations:

1. Event handlers, such as onClick callbacks.
2. Asynchronous callbacks, such as setTimeout() callbacks.
3. Server-side rendering.
4. Errors thrown by the error boundary component itself.

For event handlers and asynchronous operations, use appropriate error handling such as try/catch or Promise rejection handling.

Note: Error boundaries can catch errors during rendering, including certain errors thrown by descendant components. They should not be treated as a universal replacement for application-level error handling."""
    },
    "react_interview_question-0263": {
        "question": "When to use client and server components?",
        "answer": """In applications that support React Server Components, such as Next.js App Router applications, choose Client Components and Server Components according to their responsibilities.

Client Components are appropriate when you need:

1. Interactive event handlers such as onClick or onChange.
2. React state and effects, such as useState, useReducer, or useEffect.
3. Browser-only APIs such as window or localStorage.
4. Custom hooks that depend on client-side state, effects, or browser APIs.
5. Class components that require client-side rendering.

Server Components are appropriate when you need:

1. Data fetching and rendering on the server.
2. Direct access to server-side resources such as databases.
3. To keep secrets and sensitive server-side logic away from client bundles.
4. To reduce the amount of JavaScript sent to the browser.

Server Components cannot use client-only hooks or browser event handlers directly.

Note: Not every React application uses React Server Components. Their availability depends on the framework and application architecture."""
    },
}

if not ROOT.is_dir():
    raise SystemExit(f"STOP: directory not found: {ROOT}")

if BACKUP.exists():
    raise SystemExit(
        f"STOP: backup already exists: {BACKUP}\n"
        "No changes made. Do not delete the backup."
    )

files = sorted(ROOT.glob("chunked_*.json"))
if len(files) != 13:
    raise SystemExit(f"STOP: expected 13 JSON files, found {len(files)}")

loaded = {}
matches = {}

for path in files:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, list):
        raise SystemExit(f"STOP: invalid JSON structure in {path}")

    loaded[path] = data

    for item in data:
        rid = item.get("id")

        if rid not in FIXES:
            continue

        if rid in matches:
            raise SystemExit(f"STOP: duplicate target ID: {rid}")

        expected_question = FIXES[rid]["question"]
        actual_question = item.get("question", "").strip()

        if actual_question != expected_question:
            raise SystemExit(
                f"STOP: question mismatch for {rid}\n"
                f"Expected: {expected_question}\n"
                f"Actual: {actual_question}"
            )

        matches[rid] = path

missing = set(FIXES) - set(matches)

if missing:
    raise SystemExit(f"STOP: missing IDs: {sorted(missing)}")

shutil.copytree(ROOT, BACKUP)
print("BACKUP:", BACKUP)

changed = []

for path, data in loaded.items():
    modified = False

    for item in data:
        rid = item.get("id")

        if rid not in FIXES:
            continue

        answer = FIXES[rid]["answer"].strip()
        question = item["question"].strip()

        item["answer"] = answer
        item["content"] = (
            f"Question: {question}\n\nAnswer: {answer}"
        )

        changed.append(rid)
        modified = True

    if modified:
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

print("\nCHANGED:", len(changed))
for rid in sorted(changed):
    print("OK:", rid)

print("\nPOST-CHECK")

all_records = []

for path in files:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    all_records.extend(data)

ids = [item["id"] for item in all_records]

empty_questions = sum(
    not str(item.get("question", "")).strip()
    for item in all_records
)

empty_answers = sum(
    not str(item.get("answer", "")).strip()
    for item in all_records
)

mismatches = sum(
    item.get("content") != (
        f"Question: {str(item.get('question', '')).strip()}"
        f"\n\nAnswer: {str(item.get('answer', '')).strip()}"
    )
    for item in all_records
)

print("Files:", len(files))
print("Records:", len(all_records))
print("Duplicate IDs:", len(ids) - len(set(ids)))
print("Empty questions:", empty_questions)
print("Empty answers:", empty_answers)
print("Content mismatches:", mismatches)
print("ChromaDB: unchanged")

assert len(changed) == 4
assert len(all_records) == 1783
assert len(ids) == len(set(ids))
assert empty_questions == 0
assert empty_answers == 0
assert mismatches == 0

print("\nFINAL FIXES: PASSED")
