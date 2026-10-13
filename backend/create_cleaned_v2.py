
from pathlib import Path

source = Path("dataset_pipeline/data/raw/python_interview_question.cleaned_test.md")
output = Path("dataset_pipeline/data/raw/python_interview_question.cleaned_test_v2.md")

text = source.read_text(encoding="utf-8-sig")
lines = text.splitlines()

fixes = [
    ("The GIL (``Global Interpreter Lock``)",
     "The GIL (Global Interpreter Lock) affects CPU-bound tasks by limiting multi-threading performance but has less impact on I/O-bound tasks."),
    ("multiprocessing``is used for CPU-bound tasks",
     "Multiprocessing is used for CPU-bound tasks and creates separate processes, while threading is used for I/O-bound tasks and creates threads."),
    ("The `logging` module allows you to log messages with different levels",
     "The `logging` module allows you to log messages with different levels (e.g., INFO, DEBUG) to various outputs (e.g., console, file) with flexible configurations."),
    ("`unittest` is Python's built-in library",
     "`unittest` is Python's built-in library for writing unit tests. You create test cases by subclassing `unittest.TestCase` and defining test methods."),
    ("Virtual environments isolate project dependencies",
     "Virtual environments isolate project dependencies, preventing conflicts. You can create them using `venv` or `virtualenv` and activate or deactivate them as needed."),
    ("The `subprocess` module allows you to spawn new processes",
     "The `subprocess` module allows you to spawn new processes, connect to their input, output, and error pipes, and obtain return codes."),
    ("`map` applies a function to elements of an iterable",
     "`map` applies a function to elements of an iterable, `filter` filters elements based on a function's result, and `reduce` applies a function cumulatively to elements of an iterable."),
    ("You can use the `pd.read_csv()` function",
     "You can use the `pd.read_csv()` function, providing the path to the CSV file as an argument. For example: `df = pd.read_csv('data.csv')`."),
    ("The `index_col` parameter is used to specify",
     "The `index_col` parameter specifies which column from the CSV file should be used as the index (row labels) of the DataFrame."),
    ("You can select a single column by using square brackets",
     "You can select a single column using square brackets and the column name as a string. For example: `df['column_name']`."),
    ("You can filter rows by specifying a condition",
     "You can filter rows by specifying a condition within square brackets. For example: `df[df['column_name'] > 50]` filters rows where `column_name` is greater than 50."),
    ("You can drop a column using the",
     "You can drop a column using the `.drop()` method and specifying the column name and `axis=1`. For example: `df.drop('column_name', axis=1, inplace=True)`."),
    ("You can use the `.astype()` method to change",
     "You can use the `.astype()` method to change a column's data type. For example: `df['column_name'] = df['column_name'].astype('new_data_type')`."),
    ("The `.```corr```()` method",
     "The `.corr()` method computes the correlation between numeric columns in a DataFrame."),
    ("You can use methods like `.mean()`",
     "You can use methods like `.mean()`, `.median()`, `.sum()`, and `.std()` to calculate basic statistics for columns in a DataFrame."),
    ("You can use the `.```unique```()` method",
     "You can use the `.unique()` method to find unique values in a column of a Pandas DataFrame."),
    ("You can create a new column by simply assigning values",
     "You can create a new column by assigning values, for example: `df['new_column'] = values`. The new column will be added to the DataFrame."),
    ("You can identify and handle outliers by using statistical methods",
     "You can identify and handle outliers using statistical methods such as z-scores or the interquartile range (IQR)."),
]

used = set()
for prefix, replacement in fixes:
    matches = [
        i for i, line in enumerate(lines)
        if i not in used and line.strip().startswith(prefix)
    ]
    if len(matches) != 1:
        raise RuntimeError(
            f"Pattern {prefix!r}: expected 1 match, found {len(matches)}"
        )
    idx = matches[0]
    lines[idx] = "    " + replacement
    used.add(idx)

output.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("Created:", output)
print("Lines replaced:", len(used))
