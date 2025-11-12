# Ray Enablement Content: Jupyter Book Publishing

This project provides a robust workflow for publishing Jupyter notebooks as a clean, embeddable Jupyter Book website. It automatically splits large notebooks into smaller sections, generates a navigation index, and applies a minimalist, content-focused style suitable for embedding or sharing.

## Features

- **Automatic notebook splitting**: Each notebook is split into parts at every second-level markdown header (`##`).
- **Navigation index**: An `index.md` is generated with links to all notebook parts, serving as the landing page.
- **Minimalist UI**: All navigation, sidebars, footers, and theme switchers are hidden by default. Light mode is always enforced.
- **No code execution**: Notebooks are never executed during build, and all outputs are cleared in the published site.
- **Easy local preview**: Build and serve the book locally for testing.
- **GitHub Pages deployment**: The book is automatically published to GitHub Pages.

## Installation

1. **Clone the repository**

```bash
# Clone your fork or the main repo
git clone https://github.com/maxpumperla/enablement-content.git
cd enablement-content
```

2. **Set up a virtual environment (recommended)**

```bash
python3 -m venv venv
source venv/bin/activate
```

3. **Install dependencies**

```bash
pip install -r requirements.txt
# Or, if you want to build/serve locally:
pip install jupyter-book pyyaml
```

## Usage

### 1. Split Notebooks and Generate Navigation

Run the split script to:
- Split all notebooks in `courses/` into parts (by `##` header)
- Update `_toc.yml` and generate `index.md` with links to all parts

```bash
python split_notebooks.py
```

### 2. Build the Book

```bash
jupyter-book build .
```

### 3. Serve Locally for Testing

```bash
cd _build/html
python -m http.server 8000
```
Then open [http://localhost:8000/](http://localhost:8000/) in your browser.

## Customization

- **Styling**: Place custom CSS/JS in the `_static/` directory (e.g., `_static/custom_hide.css`, `_static/custom_light.js`). These files are automatically included in the built site.
- **Light mode**: Enforced via custom JS in `_static/custom_light.js`.
- **Navigation**: All navigation, sidebars, and footers are hidden via custom CSS.

## Disabling Notebook Execution and Outputs

Notebook execution is disabled and all outputs are cleared in the built site via `_config.yml`:

```yaml
jupyter_execute_notebooks: "off"
execute:
  execute_notebooks: "off"
  remove_code_outputs: true
```

## Adding New Notebooks or Courses

- Place new notebooks in a subdirectory of `courses/` (e.g., `courses/my-course/`).
- Run `python split_notebooks.py` to split and index them.
- Rebuild the book.

## How Navigation Works

- The `split_notebooks.py` script updates `_toc.yml` and generates `index.md`.
- `index.md` is the landing page and contains links to all notebook parts.
- All links are relative, so the site works both locally and on GitHub Pages.

## Publishing

- The book is automatically published to GitHub Pages at:
  - `https://ray-project.github.io/enablement-content/`
- Make sure GitHub Pages is enabled in your repo settings (source: `gh-pages` branch).

## Example Workflow

```bash
# 1. Split and index notebooks
python split_notebooks.py

# 2. Build the book
jupyter-book build .

# 3. Serve locally
cd _build/html
python -m http.server 8000
```
