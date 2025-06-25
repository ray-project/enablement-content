import os
import glob
import json
from pathlib import Path
import yaml

def split_notebook_by_h2(notebook_path, output_dir):
    """
    Splits a notebook into parts at each '##' (second-level markdown header).
    Returns a list of output notebook paths (relative to repo root).
    """
    with open(notebook_path, 'r', encoding='utf-8') as f:
        nb = json.load(f)

    cells = nb.get('cells', [])
    parts = []
    current_part = []
    for i, cell in enumerate(cells):
        if cell.get('cell_type') == 'markdown':
            # Check if this is a second-level header
            src = cell.get('source', [])
            if isinstance(src, list):
                src_str = ''.join(src)
            else:
                src_str = src
            if src_str.lstrip().startswith('## '):
                # Start a new part at each '##', but keep the first part from the top
                if current_part:
                    parts.append(current_part)
                    current_part = []
        current_part.append(cell)
    if current_part:
        parts.append(current_part)

    # Write each part as a new notebook
    output_paths = []
    base = os.path.splitext(os.path.basename(notebook_path))[0]
    for idx, part_cells in enumerate(parts):
        part_nb = dict(nb)  # shallow copy
        part_nb['cells'] = part_cells
        part_nb['metadata'] = nb.get('metadata', {})
        part_nb['nbformat'] = nb.get('nbformat', 4)
        part_nb['nbformat_minor'] = nb.get('nbformat_minor', 2)
        out_name = f"{base}_{idx+1:02d}.ipynb"
        out_path = os.path.join(output_dir, out_name)
        os.makedirs(output_dir, exist_ok=True)
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(part_nb, f, indent=1)
        # Store path relative to repo root
        rel_path = os.path.relpath(out_path, Path.cwd())
        output_paths.append(rel_path)
    return output_paths

def find_all_notebooks(root="courses"):
    """Recursively find all .ipynb files under root, ignoring output/ dirs."""
    notebooks = []
    for dirpath, dirnames, filenames in os.walk(root):
        # Skip output directories
        dirnames[:] = [d for d in dirnames if d != 'output']
        for fname in filenames:
            if fname.endswith('.ipynb'):
                notebooks.append(os.path.join(dirpath, fname))
    return sorted(notebooks)

def write_index_md_from_toc(toc_path="_toc.yml", index_path="index.md"):
    """Generate an index.md file with links to all notebook parts from _toc.yml."""
    with open(toc_path, "r", encoding="utf-8") as f:
        toc = yaml.safe_load(f)
    links = []
    # Add the root file first
    if "root" in toc:
        root_file = toc["root"]
        links.append(f"- [Index (this page)]({root_file})")
    # Add all chapters
    for entry in toc.get("chapters", []):
        file_path = entry["file"]
        # Use the filename (without extension) as the link text
        name = os.path.splitext(os.path.basename(file_path))[0].replace("_", " ")
        links.append(f"- [{name}]({file_path})")
    index_md = "# Index of All Notebooks\n\n" + "\n".join(links) + "\n"
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(index_md)

def main():
    all_notebooks = find_all_notebooks()
    toc_entries = []
    root_file = None
    for nb_path in all_notebooks:
        nb_dir = os.path.dirname(nb_path)
        output_dir = os.path.join(nb_dir, 'output')
        split_paths = split_notebook_by_h2(nb_path, output_dir)
        if not split_paths:
            continue
        if root_file is None:
            root_file = split_paths[0]
        # Add all parts to TOC
        for i, part in enumerate(split_paths):
            if part == root_file:
                continue  # root will be set separately
            toc_entries.append({'file': part})

    # Write new _toc.yml
    toc_lines = ["format: jb-book"]
    if root_file:
        toc_lines.append(f"root: index.md")
    if toc_entries or root_file:
        toc_lines.append("chapters:")
        if root_file:
            toc_lines.append(f"  - file: {root_file}")
        for entry in toc_entries:
            toc_lines.append(f"  - file: {entry['file']}")
    with open("_toc.yml", "w", encoding="utf-8") as f:
        f.write("\n".join(toc_lines) + "\n")

    # Generate index.md with links to all notebook parts
    write_index_md_from_toc("_toc.yml", "index.md")

if __name__ == "__main__":
    main() 