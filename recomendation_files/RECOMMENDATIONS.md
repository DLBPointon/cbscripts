# cbscripts — Code Review & Recommendations

Generated: 2026-07-25  
Scope: All Python source files in `src/cbscripts/`

---

## Legend

| Icon | Severity                                                          |
| ---- | ----------------------------------------------------------------- |
| 🔴   | Bug / Critical — incorrect behaviour or data loss risk            |
| 🟠   | Bad Practice — will cause maintainability or correctness problems |
| 🟡   | Performance Bottleneck — measurable speed/memory cost at scale    |
| 🔵   | Minor / Style — low risk, but worth cleaning up                   |

---

## Table of Contents

1. [scan_dir.py](#scan_dirpy)
2. [comic_class.py](#comic_classpy)
3. [utils.py](#utilspy)
4. [sort_cb.py](#sort_cbpy)
5. [cli.py](#clipy)
6. [xml_dataclass.py](#xml_dataclasspy)
7. [sql_statements.py](#sql_statementspy)
8. [pyproject.toml](#pyprojecttoml)
9. [Converters (empty files)](#converters)
10. [Cross-cutting / Architectural](#cross-cutting--architectural)

---

## scan_dir.py

---

### ~~🔴 #1 — Broken import from NumPy private API~~

|            |                                                                                                                                                                                                                                                              |
| ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **File**   | `scan_dir.py`                                                                                                                                                                                                                                                |
| **Line**   | 2                                                                                                                                                                                                                                                            |
| **Issue**  | `from numpy._core.multiarray import scalar` — imports from NumPy's private internal API (`_core`). The symbol `scalar` is also **never used** anywhere in the file. This import will break across NumPy versions and raises an `ImportError` on some builds. |
| **Fix**    | Remove the line entirely.                                                                                                                                                                                                                                    |
| **Impact** | **Critical** — will cause an `ImportError` crash on NumPy version changes; dead code otherwise.                                                                                                                                                              |

```python
# REMOVE this line:
from numpy._core.multiarray import scalar
```

> ✅ **Done** — import removed.

---

### ~~🟠 #2 — Ternary expression used as a void statement~~

|            |                                                                                                                                                                                                                                                         |
| ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **File**   | `scan_dir.py`                                                                                                                                                                                                                                           |
| **Line**   | 39                                                                                                                                                                                                                                                      |
| **Issue**  | `comicbook.send_to_sqlite(sql_connection) if update_database else None` — using a ternary expression purely for its side effect is anti-Pythonic. The `else None` branch allocates and discards a `None` object on every iteration and obscures intent. |
| **Fix**    | Use a plain `if` statement.                                                                                                                                                                                                                             |
| **Impact** | Minor performance (allocates `None` needlessly); primarily a readability issue.                                                                                                                                                                         |

```python
# Before:
comicbook.send_to_sqlite(sql_connection) if update_database else None  # type: ignore

# After:
if update_database:
    comicbook.send_to_sqlite(sql_connection)
```

---

### ~~🟠 #3 — `# type: ignore` masks a real None-safety problem~~

|            |                                                                                                                                                                                                                                                                                                      |
| ---------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **File**   | `scan_dir.py`                                                                                                                                                                                                                                                                                        |
| **Line**   | 39                                                                                                                                                                                                                                                                                                   |
| **Issue**  | The `# type: ignore` comment exists because `sql_connection` can be `None` when `update_database=False`. Suppressing the type error doesn't fix the underlying design: if `send_to_sqlite` were accidentally called with `None`, it would crash deep inside SQLite code with an unhelpful traceback. |
| **Fix**    | The guard `if update_database:` in fix #2 above removes this entirely. Delete the `# type: ignore`.                                                                                                                                                                                                  |
| **Impact** | Correctness/safety.                                                                                                                                                                                                                                                                                  |

---

### 🟡 #4 — Comic files processed sequentially, one at a time

|            |                                                                                                                                                                                                                   |
| ---------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **File**   | `scan_dir.py`                                                                                                                                                                                                     |
| **Lines**  | 37–39                                                                                                                                                                                                             |
| **Issue**  | The main loop processes each comic book serially. For a large library (hundreds of files), the dominant costs — archive decompression, image hashing, XML parsing — are all CPU/IO-bound and can be parallelised. |
| **Fix**    | Use `concurrent.futures.ThreadPoolExecutor` (IO-bound) or `ProcessPoolExecutor` (CPU-bound hashing). Collect results, then batch-insert into SQLite (SQLite writes must remain on a single thread).               |
| **Impact** | High — on a 500-comic library, parallel processing can reduce wall-clock scan time by 3–8×.                                                                                                                       |

```python
from concurrent.futures import ThreadPoolExecutor, as_completed

def process_one(comic, hash_pages, rename_format, scanner_db):
    return ComicBook(comic, hash_pages=hash_pages, rename_format=rename_format, scanner_db=scanner_db)

with ThreadPoolExecutor() as pool:
    futures = {
        pool.submit(process_one, comic, hash_pages, context.obj.rename_format, scanner_db): comic
        for comic in comic_files
    }
    for future in as_completed(futures):
        comicbook = future.result()
        if update_database:
            comicbook.send_to_sqlite(sql_connection)
```

---

## comic_class.py

---

### ~~🔴 #5 — `sys.exit(1)` inside a library class method~~

|            |                                                                                                                                                                                                                                                                |
| ---------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **File**   | `comic_class.py`                                                                                                                                                                                                                                               |
| **Line**   | 162                                                                                                                                                                                                                                                            |
| **Issue**  | `sys.exit(1)` inside `extract_archive` terminates the **entire process** if a single corrupt/unreadable archive is encountered. Every other comic in the scan queue is silently abandoned. This is appropriate for a top-level CLI script, not a class method. |
| **Fix**    | Raise a specific exception (e.g., `RuntimeError` or a custom `ComicReadError`). Catch it in the calling loop in `scan_dir.py` and log + continue.                                                                                                              |
| **Impact** | Critical data loss risk — one bad file kills the whole scan.                                                                                                                                                                                                   |

```python
# comic_class.py extract_archive — replace sys.exit(1):
except Exception as ex:
    logger.error(f"Exception w/ file: {self.current_file_path}\nError: {ex}")
    raise RuntimeError(f"Could not open archive: {self.current_file_path}") from ex

# scan_dir.py loop — catch gracefully:
try:
    comicbook = ComicBook(comic, ...)
except RuntimeError as e:
    logger.warning(f"Skipping file due to error: {e}")
    continue
```

---

### ~~🔴 #6 — `self.collection` generator is exhausted after first use~~

|            |                                                                                                                                                                                                                                           |
| ---------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **File**   | `comic_class.py`                                                                                                                                                                                                                          |
| **Lines**  | 61, 64–65, 70–74                                                                                                                                                                                                                          |
| **Issue**  | `self.collection = self.__iter__()` stores a **generator** object. Generators can only be iterated once. After `__str__` (or any other caller) iterates it, `self.collection` is permanently empty. Any subsequent access yields nothing. |
| **Fix**    | Remove `self.collection` entirely. Call `self.__iter__()` (or `self.__dict__.items()`) directly in `__str__`.                                                                                                                             |
| **Impact** | Bug — silent data loss on second access to `collection`.                                                                                                                                                                                  |

```python
# Remove line 61:
# self.collection = self.__iter__()   <-- DELETE

# In __str__, iterate directly:
for a, b in self.__dict__.items():
    if a not in {"block", "collection", "contents", "code_data", "pages"}:
        txt.write(f"\t- {a}: {b} \n")
```

---

### ~~🔴 #7 — Archive opened twice per comic (double I/O)~~

|            |                                                                                                                                                                                                                                                                         |
| ---------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **File**   | `comic_class.py`                                                                                                                                                                                                                                                        |
| **Lines**  | 101, 296                                                                                                                                                                                                                                                                |
| **Issue**  | When `hash_pages=True`, every CBZ/CBR archive is opened **twice**: once in `extract_archive` (to read `ComicInfo.xml` and list pages), and again in `check_for_scanner_page` (to open each image for hashing). For a 300 MB archive, this is substantial redundant I/O. |
| **Fix**    | Refactor `__init__` so the archive is opened once; pass the open file handle (or the extracted image bytes) into the hashing step.                                                                                                                                      |
| **Impact** | High — doubled disk I/O and decompression overhead per file.                                                                                                                                                                                                            |

---

### ~~🔴 #8 — `json.load(open(...))` — unclosed file handle~~

|            |                                                                                                                                                                                                                                   |
| ---------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **File**   | `comic_class.py`                                                                                                                                                                                                                  |
| **Line**   | 270                                                                                                                                                                                                                               |
| **Issue**  | `scanner_dict = json.load(open(scanner_db))` opens a file handle that is **never explicitly closed**. Python's GC will eventually close it, but this is a resource leak — especially inside a loop processing hundreds of comics. |
| **Fix**    | Use a `with` statement. Also, `scanner_db` is re-read from disk on **every single page-hash check**. Cache it at the call site or as a module-level constant.                                                                     |
| **Impact** | Resource leak + significant unnecessary I/O; reading the same JSON file hundreds of times per scan.                                                                                                                               |

```python
# Load once, outside the per-comic loop (e.g., in scan_dir.py main()):
with open(scanner_db) as f:
    scanner_dict = json.load(f)

# Pass scanner_dict into ComicBook instead of scanner_db path
```

---

### ~~🟠 #9 — `imagehash.ImageHash("")` is an invalid sentinel~~

|            |                                                                                                                                                                                                                                             |
| ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **File**   | `comic_class.py`                                                                                                                                                                                                                            |
| **Line**   | 57                                                                                                                                                                                                                                          |
| **Issue**  | `imagehash.ImageHash("")` is used as a "no hash" placeholder, but `ImageHash` expects a valid numpy array or hex string internally. Passing an empty string may produce unexpected comparison results (`hash1 - hash2`) further downstream. |
| **Fix**    | Use `None` as the sentinel and guard comparisons with `if self.diff_hash is not None`.                                                                                                                                                      |
| **Impact** | Potential silent incorrect comparisons.                                                                                                                                                                                                     |

---

### ~~🟠 #10 — List comprehension used for side effects in `__str__`~~

|            |                                                                                                                                                                                                                      |
| ---------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **File**   | `comic_class.py`                                                                                                                                                                                                     |
| **Lines**  | 70–74                                                                                                                                                                                                                |
| **Issue**  | A list comprehension is used solely to call `txt.write(...)` for its side effect, then the resulting list is immediately discarded. This is a well-known Python anti-pattern — it wastes memory allocating the list. |
| **Fix**    | Replace with a `for` loop (see fix for #6 above).                                                                                                                                                                    |
| **Impact** | Minor memory waste; readability issue.                                                                                                                                                                               |

---

### ~~🟠 #11 — List used for `in` membership test (should be a set)~~

|            |                                                                                                                                                                                         |
| ---------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **File**   | `comic_class.py`                                                                                                                                                                        |
| **Line**   | 73                                                                                                                                                                                      |
| **Issue**  | `if a not in ["block", "collection", "contents","code_data", "pages"]` — membership testing against a `list` is O(n). For a fixed set of exclusions, a `set` literal gives O(1) lookup. |
| **Fix**    | Change `[...]` to `{...}`.                                                                                                                                                              |
| **Impact** | Micro-performance (called per attribute in `__str__`); primarily clarity.                                                                                                               |

```python
if a not in {"block", "collection", "contents", "code_data", "pages"}:
```

---

### ~~🟠 #12 — Unused import: `from pikepdf.models import image`~~

|            |                                                                                           |
| ---------- | ----------------------------------------------------------------------------------------- |
| **File**   | `comic_class.py`                                                                          |
| **Line**   | 9                                                                                         |
| **Issue**  | `from pikepdf.models import image` is imported but never referenced anywhere in the file. |
| **Fix**    | Remove the import.                                                                        |
| **Impact** | Slightly increases import time; causes linter warnings.                                   |

---

### 🟠 #13 — Inline split of `teams` and `story_arc` inconsistent with other M2M fields

|            |                                                                                                                                                                                                                                                                                                                                                                                                         |
| ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **File**   | `comic_class.py`                                                                                                                                                                                                                                                                                                                                                                                        |
| **Lines**  | 432–433                                                                                                                                                                                                                                                                                                                                                                                                 |
| **Issue**  | `x.teams.split(",") if x.teams else []` and `x.story_arc.split(",") if x.story_arc else []` are split inline here, but `teams` and `story_arc` are declared as `str` fields in `XML_data` and are **not** normalised by `__post_init__` like other M2M fields (writer, penciller, etc.). This inconsistency means they could contain `"NA"`, `""`, or `"UNKNOWN"` strings being passed to `split(",")`. |
| **Fix**    | Move `teams` and `story_arc` into the `__post_init__` split loop in `xml_dataclass.py` as `list` fields, consistent with all other M2M fields.                                                                                                                                                                                                                                                          |
| **Impact** | Correctness — "NA" could be inserted as a team or story arc name in the database.                                                                                                                                                                                                                                                                                                                       |

---

### 🟡 #14 — O(n²) mode calculation for single-page width

|            |                                                                                                                                                                                                                                                                            |
| ---------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **File**   | `comic_class.py`                                                                                                                                                                                                                                                           |
| **Line**   | 174                                                                                                                                                                                                                                                                        |
| **Issue**  | `max(set(widths), key=widths.count)` computes the mode by calling `list.count()` once per unique width value. Each `count()` call is O(n), making the whole operation O(n²) where n is the number of pages. For a 500-page oversized volume, this is ~250,000 comparisons. |
| **Fix**    | Use `collections.Counter` for O(n) mode computation.                                                                                                                                                                                                                       |
| **Impact** | Moderate — noticeable on very large archives.                                                                                                                                                                                                                              |

```python
from collections import Counter

# Before:
single_page_width = max(set(widths), key=widths.count)

# After:
single_page_width = Counter(widths).most_common(1)[0][0]
```

---

### 🟡 #15 — Per-row `INSERT` in loop; should use `executemany`

|            |                                                                                                                                                                                                                                                 |
| ---------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **File**   | `comic_class.py`                                                                                                                                                                                                                                |
| **Lines**  | 404–419, 450–462                                                                                                                                                                                                                                |
| **Issue**  | Pages are inserted one by one inside a `for` loop, each calling `cursor.execute(...)`. For a 200-page comic this is 200 individual round-trips to SQLite. The same pattern in `_insert_m2m_data` multiplies this further across 10+ M2M tables. |
| **Fix**    | Build a list of tuples and use `cursor.executemany(...)` for batch inserts.                                                                                                                                                                     |
| **Impact** | High — `executemany` can be 10–50× faster than per-row `execute` in a loop for bulk inserts.                                                                                                                                                    |

```python
# Instead of:
for page in self.pages:
    cursor.execute("INSERT INTO pages (...) VALUES (?, ...)", (...))

# Use:
page_rows = [
    (issue_id, self._to_int(p.get("Image")), ...) for p in self.pages
]
cursor.executemany("INSERT INTO pages (...) VALUES (?, ...)", page_rows)
```

---

### ~~🟡 #16 — Image hashing is single-threaded and sequential~~

|            |                                                                                                                                                                                                                                           |
| ---------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **File**   | `comic_class.py`                                                                                                                                                                                                                          |
| **Lines**  | 296–301                                                                                                                                                                                                                                   |
| **Issue**  | Each page image is opened and hashed one-by-one inside a `for` loop. `imagehash.average_hash` involves PIL image decoding and a DCT-like transform — both CPU-bound. For a 200-page comic, this is the single biggest time cost per file. |
| **Fix**    | Use `concurrent.futures.ThreadPoolExecutor` (PIL releases the GIL during image decode) to hash pages in parallel.                                                                                                                         |
| **Impact** | Very high — hashing is typically the dominant cost of the scan command; parallelising it can halve processing time per comic.                                                                                                             |

---

### 🟡 #17 — `send_to_sqlite` commits once per comic, inside the loop

|            |                                                                                                                                                                                                                                          |
| ---------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **File**   | `comic_class.py`                                                                                                                                                                                                                         |
| **Line**   | 435                                                                                                                                                                                                                                      |
| **Issue**  | `conn.commit()` is called at the end of every comic insert. SQLite commits are expensive (they flush to disk). When processing hundreds of comics, this causes hundreds of individual fsync calls.                                       |
| **Fix**    | Commit in batches (e.g., every 50 comics) or wrap the entire scan in a single transaction with one commit. Add a final commit in `scan_dir.py` after the loop. Only accept the increased risk of losing progress on crash if it matters. |
| **Impact** | Moderate to high — batch commits can be 10–100× faster than per-row commits on spinning disk.                                                                                                                                            |

---

### 🔵 #18 — `send_to_sqlite` is 120+ lines; should be decomposed

|            |                                                                                                                                                                                                 |
| ---------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **File**   | `comic_class.py`                                                                                                                                                                                |
| **Lines**  | 321–443                                                                                                                                                                                         |
| **Issue**  | `send_to_sqlite` handles series upsert, publisher upsert, issue insert, page batch insert, and all M2M relationships in a single method. It is difficult to test, read, or modify in isolation. |
| **Fix**    | Extract into `_upsert_series`, `_upsert_publisher`, `_insert_issue`, `_insert_pages`. `send_to_sqlite` becomes a coordinator calling these.                                                     |
| **Impact** | Maintainability only.                                                                                                                                                                           |

---

### 🔵 #19 — `file_size` uses `os.path.getsize` instead of `Path.stat()`

|            |                                                                                                          |
| ---------- | -------------------------------------------------------------------------------------------------------- |
| **File**   | `comic_class.py`                                                                                         |
| **Line**   | 31                                                                                                       |
| **Issue**  | `os.path.getsize(file_path)` is used despite `file_path` already being a `Path` object.                  |
| **Fix**    | `self.file_size = file_path.stat().st_size / 1024` — stays in the pathlib idiom already used throughout. |
| **Impact** | Style only.                                                                                              |

---

## utils.py

---

### ~~🔴 #20 — `open()` without `with` statement (resource leak)~~

|            |                                                                                                                                                                                                                                                                                |
| ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **File**   | `utils.py`                                                                                                                                                                                                                                                                     |
| **Line**   | 92                                                                                                                                                                                                                                                                             |
| **Issue**  | `publisher_map: dict = json.load(open("publisher_mapping.json"))` — the file handle is never closed. Under CPython this is usually cleaned up by reference counting, but it is still a resource leak and will not be cleaned up reliably on PyPy or in long-running processes. |
| **Fix**    | Use a `with` block.                                                                                                                                                                                                                                                            |
| **Impact** | Resource leak; bad practice.                                                                                                                                                                                                                                                   |

```python
with open("publisher_mapping.json") as f:
    publisher_map: dict = json.load(f)
```

---

### ~~🔴 #21 — `publisher_mapping.json` read from disk on every call~~

|            |                                                                                                                                                                                                                           |
| ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **File**   | `utils.py`                                                                                                                                                                                                                |
| **Lines**  | 91–92                                                                                                                                                                                                                     |
| **Issue**  | `publisher_mapping()` reads and parses the JSON file **every time it is called**. If called once per comic (e.g., in `_process_publisher`), this is hundreds of redundant disk reads and JSON parses for a large library. |
| **Fix**    | Cache the result with `@functools.lru_cache` or load the map once at module level.                                                                                                                                        |
| **Impact** | High I/O overhead at scale.                                                                                                                                                                                               |

```python
import functools

@functools.lru_cache(maxsize=1)
def _load_publisher_map() -> dict:
    with open(Path(__file__).parent / "assets" / "publisher_mapping.json") as f:
        return json.load(f)

def publisher_mapping(query_publisher: str) -> str:
    query_publisher_flat = "".join(query_publisher.lower().split("_"))
    return _load_publisher_map().get(query_publisher_flat, query_publisher)
```

---

### ~~🟠 #22 — Hardcoded relative path for `publisher_mapping.json`~~

|            |                                                                                                                                                                                   |
| ---------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **File**   | `utils.py`                                                                                                                                                                        |
| **Line**   | 92                                                                                                                                                                                |
| **Issue**  | `open("publisher_mapping.json")` relies on the **current working directory** being the project root. If the CLI is run from any other directory, this raises `FileNotFoundError`. |
| **Fix**    | Use `Path(__file__).parent / "publisher_mapping.json"` to make the path relative to the package directory.                                                                        |
| **Impact** | Correctness — will fail if run from any directory other than the project root.                                                                                                    |

---

### 🟠 #23 — `fetchall()` used where `fetchone()` is correct

|            |                                                                                                                                                                                                                                    |
| ---------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **File**   | `utils.py`                                                                                                                                                                                                                         |
| **Lines**  | 39–41                                                                                                                                                                                                                              |
| **Issue**  | `cursor.fetchall()` is called after a `SELECT sqlite_version()` query that always returns exactly one row. `fetchall()` returns a list, but only `result[0][0]` is used. `fetchone()` is the correct and more efficient call here. |
| **Fix**    | Replace `cursor.fetchall()` with `cursor.fetchone()` and access `result[0]`.                                                                                                                                                       |
| **Impact** | Minor — allocates an unnecessary list object.                                                                                                                                                                                      |

---

### 🟠 #24 — Foreign keys not enabled on the SQLite connection

|            |                                                                                                                                                                                                                                                                                           |
| ---------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **File**   | `utils.py`                                                                                                                                                                                                                                                                                |
| **Line**   | 32                                                                                                                                                                                                                                                                                        |
| **Issue**  | SQLite disables foreign key enforcement by default. The schema in `sql_statements.py` defines many `FOREIGN KEY` constraints, but they will be **silently ignored** without `PRAGMA foreign_keys = ON`. Orphaned rows can accumulate in junction tables without any database-level error. |
| **Fix**    | Execute `PRAGMA foreign_keys = ON` immediately after opening the connection.                                                                                                                                                                                                              |
| **Impact** | Data integrity — referential integrity constraints are not enforced.                                                                                                                                                                                                                      |

```python
sql_connection = sqlite3.connect(database_file)
sql_connection.execute("PRAGMA foreign_keys = ON")
```

---

### 🟠 #25 — `initialize_database` only checks for one table

|            |                                                                                                                                                                                                                                                                                                |
| ---------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **File**   | `utils.py`                                                                                                                                                                                                                                                                                     |
| **Lines**  | 65–74                                                                                                                                                                                                                                                                                          |
| **Issue**  | The database is considered "already initialised" if the `series` table exists. If a previous run crashed mid-way through schema creation, the `series` table could exist while 20 other tables are missing, and the function would silently skip re-initialisation, causing errors at runtime. |
| **Fix**    | Check for all required tables, or use a schema version table (e.g., `schema_version`) with a version integer to manage migrations properly.                                                                                                                                                    |
| **Impact** | Correctness/robustness in crash-recovery scenarios.                                                                                                                                                                                                                                            |

---

## sort_cb.py

---

### 🔴 #26 — `get_comic_files` return value not unpacked (bug)

|            |                                                                                                                                                                                                                                                                                                                                                                     |
| ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **File**   | `sort_cb.py`                                                                                                                                                                                                                                                                                                                                                        |
| **Line**   | 21                                                                                                                                                                                                                                                                                                                                                                  |
| **Issue**  | `get_comic_files` returns a **tuple** `(comic_files, counter)`, but `sort_cb.py` assigns it directly: `comic_files = get_comic_files(path, subdirectory_search)`. This means `comic_files` is the tuple, not the list. Any iteration over it will iterate over `(list, int)` — yielding exactly two items (the list and the count), not the individual comic files. |
| **Fix**    | Unpack the return value: `comic_files, counter = get_comic_files(path, subdirectory_search)`.                                                                                                                                                                                                                                                                       |
| **Impact** | Critical bug — the sort function will not process any comics correctly.                                                                                                                                                                                                                                                                                             |

```python
# Before:
comic_files = get_comic_files(path, subdirectory_search)

# After:
comic_files, counter = get_comic_files(path, subdirectory_search)
```

---

### 🟠 #27 — `sort_cb.py` function body is an incomplete stub

|            |                                                                                                                                                                                                                                        |
| ---------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **File**   | `sort_cb.py`                                                                                                                                                                                                                           |
| **Lines**  | 1–21                                                                                                                                                                                                                                   |
| **Issue**  | The `main` function ends after getting the file list. There is no renaming, moving, dry-run output, or any other logic. The `sort` CLI command is advertised in the help text ("Rename comics in a given directory") but does nothing. |
| **Fix**    | Implement the sort/rename logic or add a `raise NotImplementedError("sort is not yet implemented")` so users get a clear error rather than silent no-op.                                                                               |
| **Impact** | Feature is completely non-functional.                                                                                                                                                                                                  |

---

## cli.py

---

### 🟠 #28 — `setup_logging` ignores the config file's `log_level`

|            |                                                                                                                                                                                                                                                                                                                 |
| ---------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **File**   | `cli.py`                                                                                                                                                                                                                                                                                                        |
| **Lines**  | 66–69                                                                                                                                                                                                                                                                                                           |
| **Issue**  | The config file can set `log_level`, and there is logic to fall back to the CLI `log_level` if the config's is unset. However, `setup_logging(log_level)` on line 69 **always uses the CLI argument** (`log_level`), never `config_data.log_level`. The config file's log level setting is effectively ignored. |
| **Fix**    | Pass the resolved level to `setup_logging`:                                                                                                                                                                                                                                                                     |
| **Impact** | Config file log level setting has no effect.                                                                                                                                                                                                                                                                    |

```python
effective_log_level = config_data.log_level or log_level
setup_logging(effective_log_level)
```

---

### 🟠 #29 — `rename_files` parameter accepted but never used

|            |                                                                                                                                                                  |
| ---------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **File**   | `cli.py`                                                                                                                                                         |
| **Lines**  | 79, 100                                                                                                                                                          |
| **Issue**  | Both the `scan` and `sort` commands declare a `rename_files: bool` parameter, but it is never passed to `scan_dir()` or `sort_comics()`. It is silently dropped. |
| **Fix**    | Either pass it to the underlying function, or remove the parameter from the CLI signature if it is not intended for these commands.                              |
| **Impact** | Dead parameter — users who set `--rename-files` see no effect.                                                                                                   |

---

### ~~🟠 #30 — `log_level` parameter in `scan` and `sort` commands is redundant~~

|            |                                                                                                                                                                                                                                                                                   |
| ---------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **File**   | `cli.py`                                                                                                                                                                                                                                                                          |
| **Lines**  | 85, 102                                                                                                                                                                                                                                                                           |
| **Issue**  | Logging is already configured in the `@app.callback()` `get_config` function, which runs before any subcommand. The `log_level` parameters in `scan` and `sort` are never passed to `setup_logging` and have no effect. Typer will show them in `--help` output, confusing users. |
| **Fix**    | Remove `log_level` from the `scan` and `sort` command signatures. Users should set it via the global `--log-level` option.                                                                                                                                                        |
| **Impact** | Confusing/misleading CLI interface.                                                                                                                                                                                                                                               |

---

### 🔵 #31 — `file_okay`/`dir_okay` options on a `str`-typed argument

|            |                                                                                                                                                                                                                                                    |
| ---------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **File**   | `cli.py`                                                                                                                                                                                                                                           |
| **Line**   | 59                                                                                                                                                                                                                                                 |
| **Issue**  | `file_okay=True, dir_okay=False, readable=True, writable=False` are `typer.Option` parameters that only take effect when the type is `Path`. Since `config_file` is typed as `str`, these constraints are silently ignored — no validation occurs. |
| **Fix**    | Change `config_file: str` to `config_file: Path` (or `Optional[Path]`) so Typer can enforce the path constraints.                                                                                                                                  |
| **Impact** | No path validation at CLI entry point.                                                                                                                                                                                                             |

---

### 🔵 #32 — `if config_file else` could use `or`

|            |                                                                                                                                            |
| ---------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| **File**   | `cli.py`                                                                                                                                   |
| **Line**   | 63                                                                                                                                         |
| **Issue**  | `config_file = config_file if config_file else "~/.config/..."` is more clearly written as `config_file = config_file or "~/.config/..."`. |
| **Fix**    | Use `or`.                                                                                                                                  |
| **Impact** | Style only.                                                                                                                                |

---

## xml_dataclass.py

---

### 🟠 #33 — `"NA"` string used as `None` sentinel throughout

|            |                                                                                                                                                                                                                                                                                               |
| ---------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **File**   | `xml_dataclass.py`                                                                                                                                                                                                                                                                            |
| **Lines**  | 7–30                                                                                                                                                                                                                                                                                          |
| **Issue**  | Missing/unknown values are represented as the string `"NA"` rather than Python's `None`. This propagates into the database (storing the string `"NA"` in text columns instead of `NULL`) and requires all downstream code to check `value == "NA"` rather than using truthiness or `is None`. |
| **Fix**    | Use `None` as defaults and `Optional[str]` type annotations. Update `__post_init__` to normalise `"N"`, `"UNKNOWN"`, `""` → `None`. Update all downstream comparisons accordingly.                                                                                                            |
| **Impact** | Data quality — `"NA"` strings in SQLite columns instead of `NULL` break standard SQL `IS NULL` queries; also a design smell that spreads defensive checks throughout the codebase.                                                                                                            |

---

### 🟠 #34 — List fields have no type parameter

|            |                                                                                                                              |
| ---------- | ---------------------------------------------------------------------------------------------------------------------------- |
| **File**   | `xml_dataclass.py`                                                                                                           |
| **Lines**  | 33–45                                                                                                                        |
| **Issue**  | `list = field(default_factory=list)` lacks a type parameter. Should be `list[str]` to be explicit and support type checkers. |
| **Fix**    | Annotate as `list[str] = field(default_factory=list)`.                                                                       |
| **Impact** | Type safety; mypy/pyright will not catch type errors involving these fields.                                                 |

---

### 🔵 #35 — Hardcoded field name lists in `__post_init__`

|            |                                                                                                                                                                                                                             |
| ---------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **File**   | `xml_dataclass.py`                                                                                                                                                                                                          |
| **Lines**  | 49–68                                                                                                                                                                                                                       |
| **Issue**  | The `__post_init__` method normalises fields by iterating over hardcoded lists of field names as strings. If a field is added or renamed, the lists must be manually updated or the normalisation will silently be skipped. |
| **Fix**    | Use `dataclasses.fields(self)` and type annotations to determine which fields are `str` vs `list`, then apply normalisation accordingly.                                                                                    |
| **Impact** | Maintainability — easy to forget to update the lists when adding new XML fields.                                                                                                                                            |

---

## sql_statements.py

---

### 🟠 #36 — `issues.updated_at` has no update trigger

|            |                                                                                                                                                                                                                                                  |
| ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **File**   | `sql_statements.py`                                                                                                                                                                                                                              |
| **Lines**  | 55–56                                                                                                                                                                                                                                            |
| **Issue**  | `updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP` is defined on the `issues` table, but there is no `UPDATE` trigger to refresh it when a row is modified. It will always hold the insert time, making it functionally identical to `created_at`. |
| **Fix**    | Add a SQLite trigger, or remove `updated_at` if it is not needed:                                                                                                                                                                                |
| **Impact** | Silent incorrect data — `updated_at` will never reflect actual updates.                                                                                                                                                                          |

```sql
CREATE TRIGGER IF NOT EXISTS update_issues_updated_at
AFTER UPDATE ON issues
BEGIN
    UPDATE issues SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;
```

---

### 🟡 #37 — Missing indexes on high-frequency query columns

|            |                                                                                                                                                                                                                                     |
| ---------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **File**   | `sql_statements.py`                                                                                                                                                                                                                 |
| **Lines**  | 287–305                                                                                                                                                                                                                             |
| **Issue**  | Only `series_id`, `publisher_id`, and a few junction columns are indexed. Queries filtering or sorting by `issue_number`, `series.title`, `publishers.name`, or `publish_year` will perform full table scans as the database grows. |
| **Fix**    | Add indexes for common query patterns:                                                                                                                                                                                              |
| **Impact** | Moderate — full table scans on `series` and `issues` become slow at thousands of rows.                                                                                                                                              |

```sql
CREATE INDEX IF NOT EXISTS idx_series_title ON series(title);
CREATE INDEX IF NOT EXISTS idx_publishers_name ON publishers(name);
CREATE INDEX IF NOT EXISTS idx_issues_issue_number ON issues(issue_number);
CREATE INDEX IF NOT EXISTS idx_issues_publish_year ON issues(publish_year);
```

---

## pyproject.toml

---

### ~~🔴 #38 — `requires-python = ">=3.14"` — Python 3.14 is unreleased~~

> ❌ **Recommendation withdrawn** — Python 3.14 was released; this requirement is valid.

|            |                                                                                                                                                                                                      |
| ---------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **File**   | `pyproject.toml`                                                                                                                                                                                     |
| **Line**   | 9                                                                                                                                                                                                    |
| **Issue**  | Python 3.14 is in alpha/beta as of mid-2026 and is not a stable release. Requiring it blocks installation on all production Python versions and is almost certainly a typo for `>=3.12` or `>=3.13`. |
| **Fix**    | Change to `requires-python = ">=3.12"` (or `>=3.13` if f-string and type alias features are being used).                                                                                             |
| **Impact** | Installation failure for all users on stable Python.                                                                                                                                                 |

---

### 🟠 #39 — Profiling tools in production dependencies

|            |                                                                                                                                                                                                 |
| ---------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **File**   | `pyproject.toml`                                                                                                                                                                                |
| **Lines**  | 13, 16                                                                                                                                                                                          |
| **Issue**  | `py-spy` and `snakeviz` are profiling/visualisation tools. They have no business being in `[project] dependencies` (installed for all users). They should be optional development/debug extras. |
| **Fix**    | Move to an optional dependency group:                                                                                                                                                           |
| **Impact** | Unnecessary package installs for all end users; increases install size.                                                                                                                         |

```toml
[project.optional-dependencies]
dev = ["py-spy>=0.4.2", "snakeviz>=2.2.2"]
```

---

## Converters

---

### 🟠 #40 — `cbr_to_cbz.py` and `pdf_to_cbz.py` are empty

|            |                                                                                                                                                                                  |
| ---------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Files**  | `converters/cbr_to_cbz.py`, `converters/pdf_to_cbz.py`                                                                                                                           |
| **Lines**  | —                                                                                                                                                                                |
| **Issue**  | Both converter files are completely empty. The `converters/` package exists but provides no functionality. If conversion is triggered anywhere, it will silently import nothing. |
| **Fix**    | Implement the converters or add a `raise NotImplementedError` stub so failures are explicit, not silent.                                                                         |
| **Impact** | Silent failure; misleads readers of the project structure.                                                                                                                       |

---

## Cross-cutting / Architectural

---

### 🟠 #41 — No test suite

|            |                                                                                                                                                                                                                                                                                                                                                             |
| ---------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Files**  | All                                                                                                                                                                                                                                                                                                                                                         |
| **Issue**  | There are no tests anywhere in the project (no `tests/` directory, no `test_*.py` files). Core logic like XML parsing, hash comparison, publisher mapping, and database insertion has no automated coverage. The bug in `sort_cb.py` (#26) and the `self.collection` exhaustion bug (#6) are the kind of issues a basic test suite would catch immediately. |
| **Fix**    | Add `pytest` as a dev dependency. Write unit tests for: `get_data_from_xml`, `XML_data.__post_init__`, `publisher_mapping`, `_tag_scanner_page`, `_insert_m2m_data`.                                                                                                                                                                                        |
| **Impact** | Regressions will be found in production rather than during development.                                                                                                                                                                                                                                                                                     |

---

### ~~🔵 #42 — `ComicBook._ids` class counter is never reset between runs~~

|            |                                                                                                                                                                                                                                                                                                                                   |
| ---------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **File**   | `comic_class.py`                                                                                                                                                                                                                                                                                                                  |
| **Line**   | 24                                                                                                                                                                                                                                                                                                                                |
| **Issue**  | `_ids = count(0)` is a class-level counter that increments across all `ComicBook` instances in a process. This ID is used in `get_new_name` as the issue number placeholder (`"issue": str(self.id)`), which means rename format output depends on the order files were processed in a given run, not on the actual issue number. |
| **Fix**    | Use `self.xml_data.issue` (the actual issue number from the XML) in `get_new_name` rather than the process-local counter. Reserve `self.id` for internal ordering only.                                                                                                                                                           |
| **Impact** | Incorrect file names when using rename format with `{issue}`.                                                                                                                                                                                                                                                                     |

---

## Summary Table

| #                 | File                                       | Line(s)          | Severity | Category                                             |
| ----------------- | ------------------------------------------ | ---------------- | -------- | ---------------------------------------------------- |
| ~~1~~             | ~~`scan_dir.py`~~                          | ~~2~~            | ~~🔴~~   | ~~Bad import~~ ✅                                    |
| ~~2~~             | ~~`scan_dir.py`~~                          | ~~39~~           | ~~🟠~~   | ~~Anti-pattern~~ ✅                                  |
| ~~3~~             | ~~`scan_dir.py`~~                          | ~~39~~           | ~~🟠~~   | ~~Type safety~~ ✅                                   |
| 4                 | `scan_dir.py`                              | 37–39            | 🟡       | Parallelism                                          |
| [~~5~~](#rec-5)   | ~~`comic_class.py`~~                       | ~~162~~          | ~~🔴~~   | ~~Error handling~~ ✅                                |
| ~~6~~             | ~~`comic_class.py`~~                       | ~~61, 64–65~~    | ~~🔴~~   | ~~Generator exhaustion bug~~ ✅                      |
| [~~7~~](#rec-7)   | ~~`comic_class.py`~~                       | ~~101, 296~~     | ~~🔴~~   | ~~Double I/O~~ ✅                                    |
| ~~8~~             | ~~`comic_class.py`~~                       | ~~270~~          | ~~🔴~~   | ~~Resource leak + redundant I/O~~ ✅                 |
| ~~9~~             | ~~`comic_class.py`~~                       | ~~57~~           | ~~🟠~~   | ~~Invalid sentinel value~~ ✅                        |
| ~~10~~            | ~~`comic_class.py`~~                       | ~~70–74~~        | ~~🟠~~   | ~~List comprehension side-effect anti-pattern~~ ✅   |
| ~~11~~            | ~~`comic_class.py`~~                       | ~~73~~           | ~~🟠~~   | ~~O(n) membership test~~ ✅                          |
| ~~12~~            | ~~`comic_class.py`~~                       | ~~9~~            | ~~🟠~~   | ~~Unused import~~ ✅                                 |
| 13                | `comic_class.py`                           | 432–433          | 🟠       | Inconsistent M2M handling                            |
| 14                | `comic_class.py`                           | 174              | 🟡       | O(n²) mode calculation                               |
| 15                | `comic_class.py`                           | 404–419, 450–462 | 🟡       | Per-row inserts (use `executemany`)                  |
| ~~16~~            | ~~`comic_class.py`~~                       | ~~296–301~~      | ~~🟡~~   | ~~Sequential image hashing~~ ✅                      |
| 17                | `comic_class.py`                           | 435              | 🟡       | Per-comic commits                                    |
| 18                | `comic_class.py`                           | 321–443          | 🔵       | Method too long                                      |
| 19                | `comic_class.py`                           | 31               | 🔵       | Style                                                |
| ~~20~~            | ~~`utils.py`~~                             | ~~92~~           | ~~🔴~~   | ~~Resource leak~~ ✅                                 |
| ~~21~~            | ~~`utils.py`~~                             | ~~91–92~~        | ~~🔴~~   | ~~JSON re-read every call~~ ✅                       |
| ~~22~~            | ~~`utils.py`~~                             | ~~92~~           | ~~🟠~~   | ~~Hardcoded relative path~~ ✅                       |
| 23                | `utils.py`                                 | 39–41            | 🟠       | `fetchall` vs `fetchone`                             |
| 24                | `utils.py`                                 | 32               | 🟠       | Foreign keys not enabled                             |
| 25                | `utils.py`                                 | 65–74            | 🟠       | Partial schema check                                 |
| 26                | `sort_cb.py`                               | 21               | 🔴       | Tuple not unpacked (bug)                             |
| 27                | `sort_cb.py`                               | 1–21             | 🟠       | Incomplete stub                                      |
| 28                | `cli.py`                                   | 66–69            | 🟠       | Config log level ignored                             |
| 29                | `cli.py`                                   | 79, 100          | 🟠       | Dead parameter                                       |
| ~~30~~            | ~~`cli.py`~~                               | ~~85, 102~~      | ~~🟠~~   | ~~Redundant parameter~~ ✅                           |
| 31                | `cli.py`                                   | 59               | 🔵       | Path validation not active                           |
| 32                | `cli.py`                                   | 63               | 🔵       | Style                                                |
| 33                | `xml_dataclass.py`                         | 7–30             | 🟠       | `"NA"` sentinel instead of `None`                    |
| 34                | `xml_dataclass.py`                         | 33–45            | 🟠       | Untyped list fields                                  |
| 35                | `xml_dataclass.py`                         | 49–68            | 🔵       | Hardcoded field name lists                           |
| 36                | `sql_statements.py`                        | 55–56            | 🟠       | `updated_at` never updated                           |
| 37                | `sql_statements.py`                        | 287–305          | 🟡       | Missing indexes                                      |
| [~~38~~](#rec-38) | ~~`pyproject.toml`~~                       | ~~9~~            | ~~🔴~~   | ~~Unreleased Python version~~ ❌ withdrawn           |
| 39                | `pyproject.toml`                           | 13, 16           | 🟠       | Profiling tools in prod deps                         |
| 40                | `converters/*.py`                          | —                | 🟠       | Empty files                                          |
| 41                | All                                        | —                | 🟠       | No test suite                                        |
| ~~42~~            | ~~`comic_class.py`~~                       | ~~24~~           | ~~🔵~~   | ~~Counter used as issue number~~ ✅                  |
| [~~43~~](#rec-43) | ~~`scan_dir.py`~~                          | ~~50~~           | ~~🟠~~   | ~~`print()` bypasses logging system~~ ❌ withdrawn   |
| [~~44~~](#rec-44) | ~~`utils.py`~~                             | ~~95~~           | ~~🟠~~   | ~~`mapping_file` has no default value~~ ❌ withdrawn |
| [~~45~~](#rec-45) | ~~`comic_class.py` / `cli.py`~~            | ~~40 / 26~~      | ~~🟠~~   | ~~`hash_threads` caps disagree~~ ✅                  |
| [~~46~~](#rec-46) | ~~`sql_statements.py` / `comic_class.py`~~ | ~~59 / 443~~     | ~~🟠~~   | ~~No duplicate detection~~ ✅                        |

---

### <a id="rec-43"></a>~~🟠 #43 — `print()` used instead of `logger.info()` in `scan_dir.py`~~

> ❌ **Recommendation withdrawn** — `print()` output here is intentional.

|            |                                                                                                                                                                                                                                                        |
| ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **File**   | `scan_dir.py`                                                                                                                                                                                                                                          |
| **Line**   | 50                                                                                                                                                                                                                                                     |
| **Issue**  | `print(comicbook.report())` writes directly to stdout, bypassing the logging system entirely. It cannot be silenced by changing the log level, will not appear in the log file, and is inconsistent with every other output statement in the codebase. |
| **Fix**    | Replace with `logger.info(comicbook.report())`.                                                                                                                                                                                                        |
| **Impact** | Logging inconsistency — report output disappears from the log file and cannot be filtered.                                                                                                                                                             |

---

### <a id="rec-44"></a>~~🟠 #44 — `publisher_mapping()` `mapping_file` parameter has no default~~

> ❌ **Recommendation withdrawn** — `mapping_file` as a required argument is intentional.

|            |                                                                                                                                                                                                                                                                                                         |
| ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **File**   | `utils.py`                                                                                                                                                                                                                                                                                              |
| **Line**   | 95                                                                                                                                                                                                                                                                                                      |
| **Issue**  | `def publisher_mapping(query_publisher: str, mapping_file: Path \| None) -> str:` — `mapping_file` has no default value, making it a required positional argument. Any call site that omits it will raise a `TypeError`. The intent is clearly that `None` (use package default) should be the default. |
| **Fix**    | Add `= None`: `mapping_file: Path \| None = None`.                                                                                                                                                                                                                                                      |
| **Impact** | Any call to `publisher_mapping(text)` without the second argument raises `TypeError` at runtime.                                                                                                                                                                                                        |

```python
def publisher_mapping(query_publisher: str, mapping_file: Path | None = None) -> str:
```

---

### <a id="rec-45"></a>~~🟠 #45 — `hash_threads` caps disagree between `ConfigData` and `ComicBook`~~

|            |                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| ---------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Files**  | `cli.py` line 26, `comic_class.py` line 40                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| **Issue**  | `ConfigData.__post_init__` clamps `hash_threads` to `1–8`, but `ComicBook.__init__` clamps it to `2–12`. A value of `9` set in the config file would be silently clamped to `8` by `ConfigData`, then passed straight through to `ComicBook` without hitting the `12` cap — so the two caps never conflict in practice, but they imply different contracts and will confuse anyone reading the code. The minimum of `2` in `ComicBook` also overrides a user setting of `1`. |
| **Fix**    | Decide on one authoritative range (e.g. `1–8`) and enforce it only in `ConfigData`. Remove the clamp from `ComicBook.__init__` entirely and trust the resolved value passed in.                                                                                                                                                                                                                                                                                              |
| **Impact** | Silent override of user config; confusing inconsistency.                                                                                                                                                                                                                                                                                                                                                                                                                     |

---

### <a id="rec-46"></a>~~🟠 #46 — No duplicate comic detection in `send_to_sqlite`~~

|            |                                                                                                                                                                                                                                                                                                                                       |
| ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Files**  | `sql_statements.py` line 59, `comic_class.py` lines 443–503                                                                                                                                                                                                                                                                           |
| **Issue**  | The `issues` table had a `UNIQUE(series_id, issue_number, volume, format)` constraint that silently dropped duplicates on `INSERT OR IGNORE`, with no way for the caller to know a duplicate existed. Duplicate files (e.g. the same issue in two different rips) were silently lost.                                                 |
| **Fix**    | Removed the `UNIQUE` constraint; added `is_duplicate BOOLEAN DEFAULT 0` column. `send_to_sqlite` now checks for an existing row matching `series_id + publisher_id + issue_number + volume + format` after resolving IDs, and inserts with `is_duplicate = 1` if a match is found. A `WARNING` is logged for each duplicate detected. |
| **Impact** | Data integrity — duplicate comics are now preserved and flagged rather than silently discarded.                                                                                                                                                                                                                                       |

---

_End of report._
