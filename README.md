# table-checker

“通用表格智能校验与变更说明生成器” 的 Python + Streamlit MVP 脚手架。

当前版本提供：

- 中文 Streamlit 页面
- 旧版本 / 新版本文件上传
- 支持 `xlsx`、`xls`、`csv`
- 基础校验摘要
- 基础差异摘要
- Markdown 变更说明预览

## 目录结构

```text
table-checker/
├─ app.py
├─ requirements.txt
├─ README.md
├─ .env.example
├─ AGENTS.md
├─ src/
├─ tests/
├─ docs/
├─ samples/
└─ outputs/
```

## 启动方式

推荐在 WSL Ubuntu 中运行：

```bash
cd /mnt/c/Users/Administrator/Downloads/table-checker
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

如果默认 `pip install -r requirements.txt` 较慢或失败，可改用阿里云镜像：

```bash
cd /mnt/c/Users/Administrator/Downloads/table-checker
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/
streamlit run app.py
```

启动后在浏览器打开 Streamlit 提示的本地地址，一般为：

```text
http://localhost:8501
```

## 测试

```bash
pytest
```

## 后续可扩展方向

- 增加字段级校验规则
- 增加更完整的差异比较逻辑
- 接入真实 LLM 生成自然语言变更报告
- 增加 Markdown / HTML 文件导出

## 安装说明补充

- Ubuntu 24.04 的系统 Python 默认带有 PEP 668 保护，但项目使用 `.venv` 虚拟环境即可正常安装依赖。
- 本项目这次实际排查到的问题不是 PEP 668，而是 WSL 到 `pypi.org` 的 IPv6 连接异常，导致 `pip` 读取索引超时。
