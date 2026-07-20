# Jupyter Notebook Learning

Scoped to **`/Users/shailja/clawd/jupyter-learning/`** only.

Does **not** change: other clawd projects, default Jupyter kernel (`python3` / system 3.13), system Python, LiteLLM, Hermes, etc.

## Defaults (this project)

| Setting | Value |
|---|---|
| Model | `qwen2.5:0.5b` (see `project.json`) |
| Ollama | `http://127.0.0.1:11434` |
| Kernel | **Python 3.11 (jupyter-learning)** (`lamini-py311` → `.venv`) |

Change the model for this project by editing `project.json` → `ollama.default_model`.

## One-time setup

```bash
# 1) Pull the project model (Ollama store is shared; only this project references it)
ollama pull qwen2.5:0.5b

# 2) Open Lab and use the project kernel
# Kernel → Change Kernel… → Python 3.11 (jupyter-learning)
```

Venv (already created, project-local):

```bash
cd /Users/shailja/clawd/jupyter-learning
# .venv is Python 3.11 + requests/ipykernel; leave system Python alone
```

## Notebooks

- `01-hello.ipynb` — load `project.json`, check Ollama, prompt `qwen2.5:0.5b`

Helpers: `jl_ollama.py` (project-local). Open Lab under `Users/shailja/clawd/jupyter-learning/`.

## Isolation checklist

- [x] Project venv only: `jupyter-learning/.venv`
- [x] Opt-in kernel only (not the default `python3` kernelspec)
- [x] Model name only in `project.json` / notebooks here
- [ ] Other projects: keep using their own kernels/models
