import os
import glob
import json
from pathlib import Path
import yaml
import re
import subprocess
import argparse

def fix_image_paths_in_cell(cell, notebook_path):
    """
    Fix relative image paths in markdown cells to use GitHub raw content URLs.
    """
    if cell.get('cell_type') != 'markdown':
        return cell
    
    # Extract course folder from notebook path
    # e.g., "courses/anyscale_101/101_anyscale_intro_jobs.ipynb" -> "anyscale_101"
    path_parts = notebook_path.split(os.sep)
    if len(path_parts) >= 2 and path_parts[0] == 'courses':
        course_folder = path_parts[1]
    else:
        return cell  # Can't determine course folder, return unchanged
    
    # Process source content
    source = cell.get('source', [])
    if isinstance(source, list):
        source_str = ''.join(source)
    else:
        source_str = source
    
    # GitHub raw content base URL
    github_base = "https://raw.githubusercontent.com/ray-project/enablement-content/refs/heads/main"
    
    # Pattern to match relative image paths in markdown
    # Matches: ![alt](./images/file.png), ![alt](images/file.png), <img src="./images/file.png", etc.
    patterns = [
        (r'!\[([^\]]*)\]\(\./images/([^)]+)\)', rf'![\1]({github_base}/courses/{course_folder}/images/\2)'),
        (r'!\[([^\]]*)\]\(images/([^)]+)\)', rf'![\1]({github_base}/courses/{course_folder}/images/\2)'),
        (r'<img\s+src="\.\/images\/([^"]+)"', rf'<img src="{github_base}/courses/{course_folder}/images/\1"'),
        (r'<img\s+src="images\/([^"]+)"', rf'<img src="{github_base}/courses/{course_folder}/images/\1"'),
    ]
    
    # Apply all patterns
    modified_source = source_str
    for pattern, replacement in patterns:
        modified_source = re.sub(pattern, replacement, modified_source)
    
    # Update the cell if changes were made
    if modified_source != source_str:
        if isinstance(source, list):
            # Split back into list format if original was a list
            cell['source'] = [modified_source]
        else:
            cell['source'] = modified_source
    
    return cell

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
        # Fix image paths in the cell
        cell = fix_image_paths_in_cell(cell, notebook_path)
        
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

def find_notebooks_by_course(root="courses"):
    """Find all .ipynb files organized by course folder, ignoring output/ dirs."""
    courses = {}
    for item in os.listdir(root):
        course_path = os.path.join(root, item)
        if os.path.isdir(course_path):
            notebooks = []
            for dirpath, dirnames, filenames in os.walk(course_path):
                # Skip output directories
                dirnames[:] = [d for d in dirnames if d != 'output']
                for fname in filenames:
                    if fname.endswith('.ipynb'):
                        notebooks.append(os.path.join(dirpath, fname))
            if notebooks:
                courses[item] = sorted(notebooks)
    return courses

def load_course_display_names(config_path="_config.yml"):
    """Load course display name mappings from config file."""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        return config.get('course_display_names', {})
    except (FileNotFoundError, yaml.YAMLError):
        # Fallback to empty dict if config file is missing or invalid
        return {}

def get_course_display_name(course_folder, display_names):
    """Get display name for course folder from config, with fallback logic."""
    if course_folder in display_names:
        return display_names[course_folder]
    else:
        # Fallback: Convert underscores to spaces and title case
        return course_folder.replace("_", " ").replace("-", " ").title()

def write_index_md_from_courses(courses_data, display_names, index_path="index.md"):
    """Generate an index.md file with links organized by course."""
    lines = ["# Ray Enablement Content", "", "This collection contains multiple courses on Ray and Anyscale:", ""]
    
    for course_folder, notebook_parts in courses_data.items():
        course_name = get_course_display_name(course_folder, display_names)
        lines.append(f"## {course_name}")
        lines.append("")
        for part in notebook_parts:
            # Use the filename (without extension) as the link text
            name = os.path.splitext(os.path.basename(part))[0].replace("_", " ")
            lines.append(f"- [{name}]({part})")
        lines.append("")
    
    with open(index_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

def convert_notebook_to_html(notebook_path):
    """
    Convert a notebook to HTML using jupyter nbconvert.
    Returns True if successful, False otherwise.
    """
    try:
        result = subprocess.run(
            ['jupyter', 'nbconvert', '--to', 'html', notebook_path],
            capture_output=True,
            text=True,
            check=True
        )
        print(f"✓ Converted {notebook_path} to HTML")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to convert {notebook_path} to HTML: {e.stderr}")
        return False
    except FileNotFoundError:
        print(f"✗ jupyter command not found. Please ensure jupyter is installed and in PATH.")
        return False

def find_all_split_notebooks(root="courses"):
    """
    Find all split notebooks in output directories across all courses.
    Returns a list of absolute paths to split notebooks.
    """
    split_notebooks = []
    for item in os.listdir(root):
        course_path = os.path.join(root, item)
        if os.path.isdir(course_path):
            output_dir = os.path.join(course_path, 'output')
            if os.path.exists(output_dir):
                for filename in os.listdir(output_dir):
                    if filename.endswith('.ipynb'):
                        split_notebooks.append(os.path.join(output_dir, filename))
    return split_notebooks

def convert_all_split_notebooks_to_html(root="courses"):
    """
    Convert all split notebooks in output directories to HTML.
    Returns the number of successfully converted notebooks.
    """
    split_notebooks = find_all_split_notebooks(root)
    if not split_notebooks:
        print("No split notebooks found in output directories.")
        return 0
    
    print(f"Found {len(split_notebooks)} split notebooks to convert to HTML...")
    successful_conversions = 0
    
    for notebook_path in split_notebooks:
        if convert_notebook_to_html(notebook_path):
            successful_conversions += 1
    
    print(f"Successfully converted {successful_conversions}/{len(split_notebooks)} notebooks to HTML")
    return successful_conversions

def main():
    parser = argparse.ArgumentParser(description='Split notebooks by H2 headers and optionally convert to HTML')
    parser.add_argument('--no-html', action='store_true', 
                       help='Skip HTML conversion of split notebooks')
    args = parser.parse_args()
    
    # Load course display names from config
    display_names = load_course_display_names()
    
    courses_notebooks = find_notebooks_by_course()
    courses_data = {}
    first_notebook = None
    
    # Process each course
    for course_folder, notebooks in courses_notebooks.items():
        course_parts = []
        for nb_path in notebooks:
            nb_dir = os.path.dirname(nb_path)
            output_dir = os.path.join(nb_dir, 'output')
            split_paths = split_notebook_by_h2(nb_path, output_dir)
            if split_paths:
                course_parts.extend(split_paths)
                if first_notebook is None:
                    first_notebook = split_paths[0]
        
        if course_parts:
            courses_data[course_folder] = course_parts

    # Write new _toc.yml organized by course using 'parts' format
    toc_data = {
        'format': 'jb-book',
        'root': 'index.md',
        'parts': []
    }
    
    # Sort courses for consistent ordering
    sorted_courses = sorted(courses_data.keys())
    
    for course_folder in sorted_courses:
        course_parts = courses_data[course_folder]
        course_name = get_course_display_name(course_folder, display_names)
        
        # Add course part with chapters
        course_part = {
            'caption': course_name,
            'chapters': []
        }
        
        for part in course_parts:
            course_part['chapters'].append({'file': part})
        
        toc_data['parts'].append(course_part)
    
    # Write _toc.yml
    with open("_toc.yml", "w", encoding="utf-8") as f:
        yaml.dump(toc_data, f, default_flow_style=False, sort_keys=False)

    # Generate index.md with links organized by course
    write_index_md_from_courses(courses_data, display_names, "index.md")
    
    # Convert all split notebooks to HTML (unless disabled)
    if not args.no_html:
        print("\n" + "="*50)
        print("Converting split notebooks to HTML...")
        print("="*50)
        convert_all_split_notebooks_to_html()
    else:
        print("\nSkipping HTML conversion (--no-html flag provided)")

if __name__ == "__main__":
    main() 