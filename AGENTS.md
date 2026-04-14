# Project Goal
Build a local Streamlit app called "通用表格智能校验与变更说明生成器".

# Scope
- Input: one or two Excel/CSV files
- Output:
  - validation summary
  - diff summary
  - AI-generated natural language change report
  - markdown/html export

# Constraints
- Finish MVP in one day
- Keep code simple and modular
- Do not introduce database or user system
- Use Python + Streamlit + pandas + openpyxl
- Support Chinese UI text
- Prefer readable code over over-engineering

# Coding Rules
- Separate modules under src/
- Add type hints when reasonable
- Add basic error handling
- Add lightweight tests
- Avoid unnecessary abstractions

# Deliverables
- runnable local app
- sample files
- usage doc
- technical doc
- short process note

# Goal
Make this project demo-ready for interview submission.

# Run commands
- Install deps: pip install -r requirements.txt
- Run app: streamlit run app.py
- Run tests: pytest -q

# Done criteria
- App launches without crashing
- Main page is understandable in Chinese
- User can upload old/new Excel or CSV
- User can select primary key
- User can click "开始分析"
- Validation summary is visible
- Diff summary is visible
- AI summary or fallback summary is visible
- Markdown report can be exported

# UI expectations
- Chinese labels only
- Important results should be visible without scrolling too much
- Show summary cards first, details later
- Error messages should be friendly

# Rules
- Do not redesign architecture unless necessary
- Prefer small patches
- After each change, explain:
  1. which files changed
  2. how to run
  3. what to verify manually

## Bugfix workflow
- Reproduce the bug before changing code
- Prefer minimal patch over refactor
- After every fix, run:
  - pytest -q
  - python -m py_compile app.py src/*.py
  - streamlit run app.py
- Report:
  1. root cause
  2. changed files
  3. verification steps
  4. remaining manual checks

## Current task
Add built-in example datasets with sidebar switching and auto-loading, without changing the core analysis flow.

## Validation commands
- pytest -q
- python -m py_compile app.py src/*.py
- streamlit run app.py

## Bugfix rules
- Reproduce the failure before changing code
- Prefer minimal patch over refactor
- After fixing, rerun all validation commands
- Report:
  1. root cause
  2. changed files
  3. verification results
  4. remaining manual checks

# Contents Category
table-checker/
├─ app.py
├─ requirements.txt
├─ README.md
├─ .env.example
├─ AGENTS.md
├─ src/
│  ├─ loader.py
│  ├─ validator.py
│  ├─ differ.py
│  ├─ reporter.py
│  ├─ llm_summary.py
│  └─ utils.py
├─ samples/
│  ├─ old_sample.xlsx
│  └─ new_sample.xlsx
├─ outputs/
├─ tests/
│  ├─ test_loader.py
│  ├─ test_validator.py
│  └─ test_differ.py
└─ docs/
   ├─ 使用说明书.md
   ├─ 技术实现说明书.md
   └─ 过程记录.md