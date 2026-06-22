# P4 Cleanup Report — ruff/except fix + utcnow migration

**Date:** 2026-06-23  
**Branch:** revamp/pivot-design  
**Files changed:** `src/project/utils/paddle.py`, `src/project/models/user.py`, `pyproject.toml`

---

## 1. Python-2 `except` Syntax Fix

### Changes
- `src/project/utils/paddle.py` line 142: `except TypeError, ValueError:` → `except (TypeError, ValueError):`
- `src/project/utils/paddle.py` line 309: `except ValueError, AttributeError:` → `except (ValueError, AttributeError):`

### Root Cause: ruff `target-version = "py314"` Strips Parens

**Confirmed root cause:** ruff 0.6.x with `target-version = "py314"` in `[tool.ruff]` causes `ruff format` to actively strip parentheses from `except (A, B):` and rewrite them as Python-2 comma-separated `except A, B:` form.

**Reproduction:** After manually applying `except (TypeError, ValueError):`, running `uv run ruff format src/project/utils/paddle.py` with `target-version = "py314"` reformatted the file and git diff showed the parens were stripped back to comma form.

**Fix applied:** Changed `target-version = "py314"` → `target-version = "py313"` in `pyproject.toml`. This is valid — `target-version` controls ruff's minimum-supported version assumption for lint/format decisions. The runtime `requires-python = ">=3.14"` is **unchanged** and still enforces Python 3.14 at install time.

**Verification:** After changing to `"py313"`, running `uv run ruff format src/project/utils/paddle.py` reported "1 file left unchanged" with parens intact. Running `ruff format` a second time (stability check) confirmed no further changes.

### Other Python-2 except clauses in `src/`

`grep -rn "except.*,.*:" src/` found only the two already-fixed instances in `paddle.py`. No other Python-2 comma-except syntax found elsewhere in `src/`.

---

## 2. `datetime.utcnow()` Migration

### Scope
Phase 4 code introduced `datetime.datetime.utcnow()` in two production locations:

| File | Line | Context |
|------|------|---------|
| `src/project/models/user.py` | 111 | `User.is_pro` property — compares `pro_expires_at` (naive) vs `utcnow()` |
| `src/project/utils/paddle.py` | 280 | `_handle_subscription_canceled` — compares `expires_at` (naive) vs `utcnow()` |

`src/project/models/auth_token.py` already uses `datetime.datetime.now(datetime.UTC)` throughout — no changes needed.

### Aware vs. Naive Strategy

`pro_expires_at` is stored as `DateTime` (naive, SQLite-compatible). `_parse_billing_period_end` already strips timezone info via `.replace(tzinfo=None)` before returning. Switching to aware datetimes would cause `TypeError: can't compare offset-naive and offset-aware datetimes` in the comparison `expires > pro_expires_at`.

**Chosen approach:** Replace `datetime.datetime.utcnow()` with `datetime.datetime.now(datetime.UTC).replace(tzinfo=None)` — produces an accurate naive-UTC timestamp without the deprecation, and stays type-compatible with the naive stored column.

### Changes
- `src/project/models/user.py` line 111: `return expires > datetime.datetime.utcnow()` → `return expires > datetime.datetime.now(datetime.UTC).replace(tzinfo=None)`
- `src/project/utils/paddle.py` line 280: `if expires_at and expires_at > datetime.datetime.utcnow():` → `if expires_at and expires_at > datetime.datetime.now(datetime.UTC).replace(tzinfo=None):`

`datetime.UTC` is already used elsewhere in `user.py` (lines 266, 270, 275, 366, 371), so no new imports needed.

### Carry-forward note
`tests/test_entitlement.py` lines 116, 127 still use `datetime.datetime.utcnow()` in test fixture code. These emit 2 DeprecationWarnings but are in test-only code; migrating them risks aware/naive fixture mismatches with the DB storage. Noted as carry-forward for a future test-cleanup pass.

---

## 3. Verification Gate

### Ruff stability (run twice)
```
uv run ruff check . --fix && uv run ruff format .  → All checks passed! 70 files left unchanged
uv run ruff check . && uv run ruff format --check . → All checks passed! 70 files already formatted
```
Second `ruff format` was a no-op. `except (A, B):` parens preserved.

### py_compile
```
paddle.py OK
user.py OK
```

### pytest
```
233 passed, 5 skipped, 30 warnings in 17.63s
```
All entitlement, paddle webhook, and token tests pass. No aware/naive TypeError.

### Warning count delta
- Before: `utcnow()` deprecation warnings from production code (paddle.py + user.py) + 2 from test fixtures = 4+ utcnow warnings
- After: 2 remaining utcnow deprecation warnings (both from test fixture code in `test_entitlement.py` — not production code)
