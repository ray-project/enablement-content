import os
import json
from pathlib import Path
import yaml
import re
import subprocess
import argparse


def fix_image_paths_in_cell(cell, notebook_path):
    """
    Fix relative image paths in markdown cells to use GitHub raw content URLs.
    Supports both flat and nested course structures.
    """
    if cell.get("cell_type") != "markdown":
        return cell

    # Extract course folder path from notebook path (relative to courses/)
    # e.g., "courses/anyscale_101/file.ipynb" -> "anyscale_101"
    # e.g., "courses/workloads/anyscale_101/file.ipynb" -> "courses/anyscale_101"
    # e.g., "courses/level1/level2/course/file.ipynb" -> "level1/level2/course"
    path_parts = notebook_path.split(os.sep)

    # Find the index of 'courses' in the path
    courses_index = None
    for i, part in enumerate(path_parts):
        if part == "courses":
            courses_index = i
            break

    if courses_index is None or courses_index + 1 >= len(path_parts):
        return cell  # Can't determine course folder, return unchanged

    # Get the directory containing the notebook (everything after 'courses' up to the filename)
    notebook_dir_parts = path_parts[courses_index + 1 : -1]
    if notebook_dir_parts:
        # Join all parts to get the full course path (supports nested structures)
        # Use forward slashes for GitHub URLs (works on all platforms)
        course_folder = "/".join(notebook_dir_parts)
    else:
        return cell  # Notebook is directly in courses/, can't determine course folder

    # Process source content
    source = cell.get("source", [])
    if isinstance(source, list):
        source_str = "".join(source)
    else:
        source_str = source

    # GitHub raw content base URL
    github_base = "https://raw.githubusercontent.com/ray-project/enablement-content/refs/heads/main"

    # Pattern to match relative image paths in markdown
    # Matches: ![alt](./images/file.png), ![alt](images/file.png), <img src="./images/file.png", etc.
    patterns = [
        (
            r"!\[([^\]]*)\]\(\./images/([^)]+)\)",
            rf"![\1]({github_base}/courses/{course_folder}/images/\2)",
        ),
        (
            r"!\[([^\]]*)\]\(images/([^)]+)\)",
            rf"![\1]({github_base}/courses/{course_folder}/images/\2)",
        ),
        (
            r'<img\s+src="\.\/images\/([^"]+)"',
            rf'<img src="{github_base}/courses/{course_folder}/images/\1"',
        ),
        (
            r'<img\s+src="images\/([^"]+)"',
            rf'<img src="{github_base}/courses/{course_folder}/images/\1"',
        ),
    ]

    # Apply all patterns
    modified_source = source_str
    for pattern, replacement in patterns:
        modified_source = re.sub(pattern, replacement, modified_source)

    # Update the cell if changes were made
    if modified_source != source_str:
        if isinstance(source, list):
            # Split back into list format if original was a list
            cell["source"] = [modified_source]
        else:
            cell["source"] = modified_source

    return cell


def split_notebook_by_h2(notebook_path, output_dir, force=False):
    """
    Splits a notebook into parts at each '##' (second-level markdown header).
    Returns a list of output notebook paths (relative to repo root).
    """
    with open(notebook_path, "r", encoding="utf-8") as f:
        nb = json.load(f)

    cells = nb.get("cells", [])
    parts = []
    current_part = []
    for i, cell in enumerate(cells):
        # Fix image paths in the cell
        cell = fix_image_paths_in_cell(cell, notebook_path)

        if cell.get("cell_type") == "markdown":
            # Check if this is a second-level header
            src = cell.get("source", [])
            if isinstance(src, list):
                src_str = "".join(src)
            else:
                src_str = src
            if src_str.lstrip().startswith("## "):
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
        part_nb["cells"] = part_cells
        part_nb["metadata"] = nb.get("metadata", {})
        part_nb["nbformat"] = nb.get("nbformat", 4)
        part_nb["nbformat_minor"] = nb.get("nbformat_minor", 2)
        out_name = f"{base}_{idx + 1:02d}.ipynb"
        out_path = os.path.join(output_dir, out_name)
        os.makedirs(output_dir, exist_ok=True)
        if force or not os.path.exists(out_path):
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(part_nb, f, indent=1)
        else:
            print(
                f"Skipping existing split notebook: {out_path} (use --force to regenerate)"
            )
        # Store path relative to repo root
        rel_path = os.path.relpath(out_path, Path.cwd())
        output_paths.append(rel_path)
    return output_paths


def find_notebooks_by_course(root="courses", target_course=None):
    """
    Find all .ipynb files organized by course folder, ignoring output/ dirs.
    Supports both flat and nested course structures.
    Optionally limit the search to a single course folder.

    Course folders are identified as directories containing .ipynb files.
    The course identifier is the path relative to the root (e.g., "course1" or "courses/course2").
    """
    courses = {}

    if not os.path.exists(root):
        return courses

    # Normalize root path
    root = os.path.normpath(root)

    # If target_course is specified, construct the full path
    if target_course:
        target_path = os.path.join(root, target_course)
        if not os.path.isdir(target_path):
            return courses
        search_paths = [target_path]
    else:
        search_paths = [root]

    # Walk through all directories to find course folders
    # Strategy:
    # 1. Find all directories that contain notebooks directly
    # 2. For directories with notebooks, check if their parent also has notebooks directly
    #    - If parent has notebooks directly, parent is the course folder (category grouping)
    #    - If parent doesn't have notebooks directly, check if parent has multiple subdirs with notebooks
    #      - If yes, parent is the course folder (e.g., 02_Anyscale_Admin)
    #      - If no, this directory is the course folder
    # 3. Also identify directories that have subdirectories with notebooks but no notebooks directly

    directories_with_direct_notebooks = (
        set()
    )  # Directories with notebooks directly in them

    for search_path in search_paths:
        for dirpath, dirnames, filenames in os.walk(search_path):
            # Skip output directories
            dirnames[:] = [d for d in dirnames if d != "output"]

            # Check if this directory contains notebooks (directly)
            has_notebooks = any(fname.endswith(".ipynb") for fname in filenames)

            if has_notebooks:
                # Get path relative to root
                rel_path = os.path.relpath(dirpath, root)
                # Normalize to use forward slashes for consistency (even on Windows)
                course_id = rel_path.replace(os.sep, "/")
                directories_with_direct_notebooks.add(course_id)

    # Identify course folders by analyzing the structure
    # Group directories by their immediate parent
    parent_to_children = {}
    for dir_with_nb in directories_with_direct_notebooks:
        dir_parts = dir_with_nb.split("/")
        if len(dir_parts) > 1:
            parent_id = "/".join(dir_parts[:-1])
            if parent_id not in parent_to_children:
                parent_to_children[parent_id] = []
            parent_to_children[parent_id].append(dir_with_nb)
        else:
            # Top-level directory (directly under courses/)
            parent_to_children[None] = parent_to_children.get(None, []) + [dir_with_nb]

    course_folders = set()

    # Process each parent and its children
    for parent_id, children in parent_to_children.items():
        if parent_id is None:
            # Top-level directories - they are course folders
            course_folders.update(children)
            continue

        # Check if parent has notebooks directly
        if parent_id in directories_with_direct_notebooks:
            # Parent has notebooks directly - parent is the course folder
            # (This handles cases where both parent and child have notebooks)
            course_folders.add(parent_id)
        else:
            # Parent doesn't have notebooks directly
            # Get immediate subdirectories (one level down from parent)
            immediate_subdirs = set()
            for child in children:
                child_parts = child[len(parent_id) + 1 :].split("/")
                if child_parts:
                    immediate_subdirs.add(child_parts[0])

            if len(immediate_subdirs) > 1:
                # Parent has multiple immediate subdirectories with notebooks
                # Parent is the course folder (e.g., 02_Anyscale_Admin)
                course_folders.add(parent_id)
            else:
                # Parent has only one immediate subdirectory with notebooks
                # Use the children as course folders (handles category structures)
                course_folders.update(children)

    # Also add any directories that weren't processed (shouldn't happen, but safety check)
    for dir_with_nb in directories_with_direct_notebooks:
        if not any(
            dir_with_nb.startswith(cf + "/") or dir_with_nb == cf
            for cf in course_folders
            if cf
        ):
            # This directory is not under any identified course folder, so it's a course folder itself
            course_folders.add(dir_with_nb)

    # For each course folder, collect all notebooks in its tree (excluding output dirs)
    # Preserve filesystem order (from os.listdir) to match original index.md order
    # Note: _toc.yml will sort this later to match original behavior (sorted(courses_data.keys()))
    course_folders_ordered = []
    if not target_course:
        # Discover courses in filesystem order (like original os.listdir - unsorted)
        try:
            for item in os.listdir(root):  # Use filesystem order, not sorted
                item_path = os.path.join(root, item)
                if os.path.isdir(item_path):
                    # Check if this exact item is a course folder
                    if item in course_folders:
                        course_folders_ordered.append(item)
                    # Check for nested course folders under this directory
                    for course_id in course_folders:  # Preserve order, don't sort
                        if (
                            course_id.startswith(item + "/")
                            and course_id not in course_folders_ordered
                        ):
                            course_folders_ordered.append(course_id)
        except (FileNotFoundError, OSError):
            pass

    # Add any remaining course folders (preserve their discovery order)
    for course_id in course_folders:
        if course_id not in course_folders_ordered:
            course_folders_ordered.append(course_id)

    # Fallback to sorted if we couldn't determine order (e.g., target_course specified)
    if not course_folders_ordered or target_course:
        course_folders_ordered = sorted(course_folders)

    for course_id in course_folders_ordered:
        course_path = os.path.join(root, course_id)
        all_notebooks = []

        for dirpath, dirnames, filenames in os.walk(course_path):
            # Skip output directories
            dirnames[:] = [d for d in dirnames if d != "output"]
            for fname in filenames:
                if fname.endswith(".ipynb"):
                    all_notebooks.append(os.path.join(dirpath, fname))

        if all_notebooks:
            courses[course_id] = sorted(all_notebooks)

    return courses


def load_course_display_names(config_path="_config.yml"):
    """Load course display name mappings from config file."""
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        return config.get("course_display_names", {})
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


def extract_category(course_folder):
    """
    Extract category from course folder path.
    Returns (category, course_name) tuple.
    For flat structures, category is None.
    Examples:
      "workloads/course_1" -> ("workloads", "course_1")
      "foundations/course_x" -> ("foundations", "course_x")
      "course_1" -> (None, "course_1")
    """
    parts = course_folder.split("/")
    if len(parts) > 1:
        return (parts[0], "/".join(parts[1:]))
    else:
        return (None, course_folder)


def group_courses_by_category(courses_data):
    """
    Group courses by category.
    Returns a dict mapping category (or None for uncategorized) to list of (course_folder, course_parts) tuples.
    Preserves original order when there are no categories (backward compatibility).
    """
    categorized = {}
    # Track insertion order to preserve it when no categories
    insertion_order = []
    # Track order of courses within each category to preserve original order
    course_order_by_category = {}

    for course_folder, course_parts in courses_data.items():
        category, course_name = extract_category(course_folder)
        if category not in categorized:
            categorized[category] = []
            insertion_order.append(category)
            course_order_by_category[category] = []
        categorized[category].append((course_folder, course_parts))
        course_order_by_category[category].append(course_folder)

    # Only sort if there are actual categories (not just uncategorized)
    has_categories = any(cat is not None for cat in categorized.keys())

    if has_categories:
        # Sort categories: None (uncategorized) first, then alphabetically
        sorted_categories = sorted(
            categorized.keys(), key=lambda x: (x is not None, x or "")
        )
        # Sort courses within each category alphabetically
        for category in sorted_categories:
            categorized[category].sort(key=lambda x: x[0])
        return categorized, sorted_categories
    else:
        # No categories - preserve original order from courses_data
        # The courses are already in the right order in categorized[None]
        # because we iterated over courses_data.items() which preserves dict order
        return categorized, insertion_order


def write_index_md_from_courses(courses_data, display_names, index_path="index.md"):
    """Generate an index.md file with links organized by category and course."""
    lines = [
        "# Ray Enablement Content",
        "",
        "This collection contains multiple courses on Ray and Anyscale:",
        "",
    ]

    # Group courses by category
    categorized, sorted_categories = group_courses_by_category(courses_data)

    # Check if there are any actual categories (not just uncategorized)
    has_categories = any(cat is not None for cat in sorted_categories)

    # When there are no categories, use the same order as _toc.yml (backward compatibility)
    if not has_categories:
        # No categories - iterate in original order from courses_data (same as _toc.yml)
        for course_folder, notebook_parts in courses_data.items():
            course_name = get_course_display_name(course_folder, display_names)
            lines.append(f"## {course_name}")
            lines.append("")
            for part in notebook_parts:
                # Use the filename (without extension) as the link text
                name = os.path.splitext(os.path.basename(part))[0].replace("_", " ")
                lines.append(f"- [{name}]({part})")
            lines.append("")
    else:
        # Has categories - use categorized order
        for category in sorted_categories:
            courses_in_category = categorized[category]

            # Add category header if there are categories
            if category is not None:
                category_display = category.replace("_", " ").replace("-", " ").title()
                lines.append(f"## {category_display}")
                lines.append("")

            # Add courses in this category
            for course_folder, notebook_parts in courses_in_category:
                course_name = get_course_display_name(course_folder, display_names)
                # If course is nested, use just the course name part for display
                _, course_base = extract_category(course_folder)
                if category is not None:
                    # Use the base course name, not the full path
                    course_display = get_course_display_name(course_base, display_names)
                else:
                    course_display = course_name

                # Use H3 for courses when there are categories
                lines.append(f"### {course_display}")
                lines.append("")
                for part in notebook_parts:
                    # Use the filename (without extension) as the link text
                    name = os.path.splitext(os.path.basename(part))[0].replace("_", " ")
                    lines.append(f"- [{name}]({part})")
                lines.append("")

    with open(index_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def convert_notebook_to_html(notebook_path, force=False):
    """
    Convert a notebook to HTML using jupyter nbconvert.
    Returns True if successful, False otherwise.
    """
    html_path = os.path.splitext(notebook_path)[0] + ".html"
    if not force and os.path.exists(html_path):
        print(f"Skipping existing HTML: {html_path} (use --force to regenerate)")
        return True

    try:
        subprocess.run(
            ["jupyter", "nbconvert", "--to", "html", notebook_path],
            capture_output=True,
            text=True,
            check=True,
        )
        print(f"✓ Converted {notebook_path} to HTML")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to convert {notebook_path} to HTML: {e.stderr}")
        return False
    except FileNotFoundError:
        print(
            "✗ jupyter command not found. Please ensure jupyter is installed and in PATH."
        )
        return False


def find_all_split_notebooks(root="courses"):
    """
    Find all split notebooks in output directories across all courses.
    Recursively searches for output directories at any level.
    Returns a list of absolute paths to split notebooks.
    """
    split_notebooks = []
    for root_dir, dirs, files in os.walk(root):
        # Check if this directory is named 'output'
        if os.path.basename(root_dir) == "output":
            for filename in files:
                if filename.endswith(".ipynb"):
                    split_notebooks.append(os.path.join(root_dir, filename))
    return split_notebooks


def convert_all_split_notebooks_to_html(root="courses", force=False):
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
        if convert_notebook_to_html(notebook_path, force=force):
            successful_conversions += 1

    print(
        f"Successfully converted {successful_conversions}/{len(split_notebooks)} notebooks to HTML"
    )
    return successful_conversions


def main():
    parser = argparse.ArgumentParser(
        description="Split notebooks by H2 headers and optionally convert to HTML"
    )
    parser.add_argument(
        "--no-html", action="store_true", help="Skip HTML conversion of split notebooks"
    )
    parser.add_argument(
        "--course", help="Name of course folder under courses/ to process"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Regenerate outputs even if they already exist",
    )
    args = parser.parse_args()

    # Load course display names from config
    display_names = load_course_display_names()

    courses_root = "courses"
    courses_notebooks = find_notebooks_by_course(
        root=courses_root, target_course=args.course
    )
    if args.course:
        # Check if the course was found (it might be nested, so check by key)
        course_found = False
        for course_id in courses_notebooks.keys():
            # Check if this course_id matches or ends with the target_course
            if (
                course_id == args.course
                or course_id.endswith(os.sep + args.course)
                or course_id.endswith("/" + args.course)
            ):
                course_found = True
                break

        if not course_found:
            target_course_path = os.path.join(courses_root, args.course)
            if not os.path.isdir(target_course_path):
                print(
                    f"Course '{args.course}' not found under '{courses_root}'. Nothing to do."
                )
                return
            if not courses_notebooks:
                print(f"No notebooks found for course '{args.course}'. Nothing to do.")
                return

    courses_data = {}
    first_notebook = None

    # Process each course
    for course_folder, notebooks in courses_notebooks.items():
        course_parts = []
        for nb_path in notebooks:
            nb_dir = os.path.dirname(nb_path)
            output_dir = os.path.join(nb_dir, "output")
            split_paths = split_notebook_by_h2(nb_path, output_dir, force=args.force)
            if split_paths:
                course_parts.extend(split_paths)
                if first_notebook is None:
                    first_notebook = split_paths[0]

        if course_parts:
            courses_data[course_folder] = course_parts

    # Write new _toc.yml organized by category and course using 'parts' format
    toc_data = {"format": "jb-book", "root": "index.md", "parts": []}

    # Group courses by category
    categorized, sorted_categories = group_courses_by_category(courses_data)

    # Check if there are any actual categories (not just uncategorized)
    has_categories = any(cat is not None for cat in sorted_categories)

    # Add courses organized by category
    # Each course remains a separate part for Jupyter Book compatibility
    # When there are no categories, use sorted order to match original _toc.yml behavior
    if not has_categories:
        # No categories - sort to match original behavior (original used sorted(courses_data.keys()))
        sorted_courses = sorted(courses_data.keys())
        for course_folder in sorted_courses:
            course_parts = courses_data[course_folder]
            course_name = get_course_display_name(course_folder, display_names)

            # Add course part with chapters
            course_part = {"caption": course_name, "chapters": []}

            for part in course_parts:
                course_part["chapters"].append({"file": part})

            toc_data["parts"].append(course_part)
    else:
        # Has categories - use categorized order
        for category in sorted_categories:
            courses_in_category = categorized[category]

            for course_folder, course_parts in courses_in_category:
                # Get display name - use base course name if categorized
                _, course_base = extract_category(course_folder)
                if category is not None:
                    course_name = get_course_display_name(course_base, display_names)
                else:
                    course_name = get_course_display_name(course_folder, display_names)

                # Add course part with chapters
                course_part = {"caption": course_name, "chapters": []}

                for part in course_parts:
                    course_part["chapters"].append({"file": part})

                toc_data["parts"].append(course_part)

    # Write _toc.yml
    with open("_toc.yml", "w", encoding="utf-8") as f:
        yaml.dump(toc_data, f, default_flow_style=False, sort_keys=False)

    # Generate index.md with links organized by course
    write_index_md_from_courses(courses_data, display_names, "index.md")

    # Convert all split notebooks to HTML (unless disabled)
    if not args.no_html:
        print("\n" + "=" * 50)
        print("Converting split notebooks to HTML...")
        print("=" * 50)
        html_root = (
            os.path.join(courses_root, args.course) if args.course else courses_root
        )
        convert_all_split_notebooks_to_html(root=html_root, force=args.force)
    else:
        print("\nSkipping HTML conversion (--no-html flag provided)")


if __name__ == "__main__":
    main()
