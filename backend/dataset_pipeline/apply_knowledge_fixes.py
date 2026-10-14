import json
from pathlib import Path

root = Path("dataset_pipeline/data/chunk_final_test")
backup = Path("dataset_pipeline/data/chunk_final_test_backup_before_knowledge_fixes")

if not root.is_dir() or not backup.is_dir():
    raise SystemExit("Thieu thu muc du lieu hoac ban sao luu.")

fixes = {
    "chunked_python_interview_question.json": {
        "python_interview_question-0001": (
            "There is no single time complexity for all recursive functions. "
            "It depends on the recurrence relation, including the number of recursive "
            "calls, how the input size changes, and the work done per call. For example, "
            "T(n) = 2T(n-1) + O(1) is exponential, while T(n) = 2T(n/2) + O(n) is "
            "O(n log n). Analyze the specific recurrence to determine the complexity."
        ),
        "python_interview_question-0006": (
            "High-level languages are processed differently depending on the language "
            "and implementation. A compiler may translate source code into machine code "
            "or an intermediate representation; an interpreter may execute instructions "
            "at runtime; some implementations combine both. Java source is compiled to "
            "bytecode and run by the JVM. CPython compiles Python source to bytecode that "
            "its virtual machine executes."
        ),
        "python_interview_question-0008": (
            "Encapsulation is an object-oriented programming principle that groups data "
            "and the methods operating on that data into a class, while controlling access "
            "to internal state through a defined interface. It helps protect invariants "
            "and reduces unintended coupling."
        ),
        "python_interview_question-0013": (
            "Python strings are immutable, so string operations return new values rather "
            "than modifying the original string. str.split() splits a string into a list. "
            "re.sub() replaces regular-expression matches, while re.subn() also returns "
            "the number of replacements. Both re.sub() and re.subn() belong to the re module."
        ),
        "python_interview_question-0014": (
            "In Python 3.7 and later, the built-in dict type guarantees insertion order. "
            "collections.OrderedDict also preserves order and provides additional "
            "order-specific operations, such as move_to_end() and order-sensitive equality "
            "between OrderedDict instances. For most modern Python code, dict is sufficient "
            "when insertion order is needed."
        ),
        "python_interview_question-0017": (
            "Python 2 reached end of life on January 1, 2020, and no longer receives "
            "official security updates or bug fixes. Python 3 is the supported series. "
            "Differences include print() being a function, Unicode text strings by default, "
            "and changes to division and standard-library APIs. Python 2 and Python 3 are "
            "not fully source-compatible."
        ),
        "python_interview_question-0108": (
            "Use profiling tools to identify where execution time is spent. The built-in "
            "cProfile module provides function-level timing and call statistics, and "
            "pstats helps inspect and sort results. A line profiler can provide line-level "
            "detail. Profile representative workloads, identify the main bottleneck, make "
            "a targeted change, and measure again."
        ),
    },
    "chunked_java_interview_question.json": {
        "java_interview_question-0037": (
            "The finalize() method was historically eligible to be called by the garbage "
            "collector before reclaiming an object's memory, but its execution was never "
            "guaranteed or timely. Finalization is deprecated for removal in modern Java "
            "and should not be used for resource management. Prefer try-with-resources for "
            "AutoCloseable resources or other explicit cleanup mechanisms."
        ),
        "java_interview_question-0038": (
            "Setting one reference to null does not guarantee that an object becomes "
            "eligible for garbage collection; other reachable references may still point "
            "to it. If the object becomes unreachable, it may be reclaimed, but collection "
            "is not immediate and is not guaranteed to happen in the next cycle."
        ),
        "java_interview_question-0039": (
            "The JVM heap stores class instances and arrays. Older HotSpot JVM versions "
            "used PermGen for class metadata; PermGen was removed in Java 8 and replaced "
            "by Metaspace, which uses native memory rather than the Java heap. Memory "
            "management and collection behavior depend on the JVM version and collector."
        ),
        "java_interview_question-0042": (
            "In older HotSpot JVMs, PermGen stored class metadata and could be reclaimed "
            "during garbage collection. PermGen was removed in Java 8 and replaced by "
            "Metaspace, which uses native memory. The answer therefore depends on the "
            "Java version being discussed."
        ),
        "java_interview_question-0048": (
            "A finally block is part of exception-handling control flow and normally runs "
            "when execution leaves the associated try/catch structure, although abrupt JVM "
            "termination can prevent it. finalize() was a method the garbage collector "
            "could invoke before reclaiming an object, but it was unreliable and is "
            "deprecated for removal. Use try-with-resources for AutoCloseable resources."
        ),
    },
    "chunked_react_interview_question.json": {
        "react_interview_question-0212": (
            "useEffect lets a function component synchronize with external systems, such "
            "as subscriptions, timers, or network connections. Its setup function runs "
            "after a commit when the component mounts and again when dependencies change; "
            "a returned cleanup function runs before the effect is re-established and "
            "when the component unmounts. An empty dependency array means the effect has "
            "no reactive dependencies, while omitting the array makes it run after every "
            "commit. Effects are not an exact one-to-one replacement for class lifecycle "
            "methods."
        ),
    },
}

# Validate all targets before writing any file.
pending = []
errors = []

for filename, mapping in fixes.items():
    path = root / filename
    if not path.is_file():
        errors.append(f"Missing file: {path}")
        continue

    records = json.loads(path.read_text(encoding="utf-8-sig"))
    by_id = {str(item.get("id", "")): item for item in records}

    for rid in mapping:
        if rid not in by_id:
            errors.append(f"Missing ID: {filename} | {rid}")
        else:
            pending.append((path, by_id[rid], mapping[rid]))

if errors:
    print("KHONG SUA DU LIEU. Can kiem tra:")
    print("\n".join(errors))
    raise SystemExit(2)

# Apply edits only after every target is verified.
records_by_path = {}
for path, item, new_answer in pending:
    if path not in records_by_path:
        records_by_path[path] = json.loads(path.read_text(encoding="utf-8-sig"))

    target = next(x for x in records_by_path[path] if x["id"] == item["id"])
    target["answer"] = new_answer
    target["content"] = f"Question: {target['question']}\n\nAnswer: {new_answer}"
    target.setdefault("metadata", {})["answer_status"] = "available"

for path, records in records_by_path.items():
    path.write_text(
        json.dumps(records, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

print("CHANGED:", len(pending))
for path, item, _ in pending:
    print("OK:", path.name, item["id"], "|", item["question"])
print("BACKUP GIU NGUYEN:", backup)
print("Chua tao hoac sua collection ChromaDB.")
