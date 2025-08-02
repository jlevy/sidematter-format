# Sidematter Format

**Sidematter format** is a simple, universal convention for keeping metadata and assets
alongside a primary document.
It is a useful complement to
[frontmatter-format](https://github.com/jlevy/frontmatter-format).

## Motivation

Many tools and formats need structured data *associated with* a document but not
*inside* it:

* **Metadata** that can’t easily be stored in a document itself, due to size or because
  it is updated more often (e.g. document annotations, full version history, etc.)

* **Additional files** that must travel with a document, such as images or resources
  associated with an HTML or Markdown file.

Sidematter format defines a **minimal set of conventions** for naming and resolving such
“sidecar files” in a consistent way.

Sidecar patterns are often used in data pipelines, in exports from web browsers, and
other applications. Unfortunately, there’s no consistent convention for naming and
organizing such external files, leading to varied, ad-hoc approaches that don’t
interoperate well.

This repository is a **description of the format** and a **reference implementation**.
The implementation is in Python but the format is simple and can be adopted by any tool
or language.

Sidematter format does not specify a way to bundle the outputs, but a file plus its
sidematter files can easily be bundled together in a zip or tarball.

> [!TIP]
> 
> Sidematter format complements
> [**frontmatter format**](https://github.com/jlevy/frontmatter-format), which allows
> placing metadata within any text file.
> A good practice is to use frontmatter format for small metadata attached at the front
> of text files, and sidematter format for larger metadata, on binary files, or for
> additional file assets.

## Examples

Some simple examples:

Given a primary document `report.md`, the sidematter files would be:

```
report.md
report.meta.yml        # YAML metadata
report.assets/         # Asset directory
    figure1.png
    diagram.svg
    styles.css
```

The document can reference assets with relative paths:

```markdown
# My Report

![Key findings](report.assets/figure1.png)

See the [full diagram](report.assets/diagram.svg) for details.
```

More examples across different file types:

```
blog-post.md           → blog-post.meta.yml, blog-post.assets/
index.html             → index.meta.json, index.assets/
presentation.slides    → presentation.meta.yml, presentation.assets/
notebook.ipynb         → notebook.meta.yml, notebook.assets/
```

Example metadata content:

```yaml
# report.meta.yml
title: Q3 Financial Analysis
author: Jane Doe
created_at: 2024-01-15
tags:
  - finance
  - quarterly
  - analysis
processing_history:
  - step: data_extraction
    timestamp: 2024-01-15T10:30:00Z
    tool: custom_extractor_v2.1
  - step: analysis
    timestamp: 2024-01-15T11:45:00Z
    tool: pandas_analyzer
source_files:
  - raw_data.csv
  - market_trends.json
```

## Goals of this Approach

* **Clean separation:** Keep metadata and assets separate from primary content, not
  requiring that it be bundled (like a zip file).

* **Predictable asset filenames and metadata syntax:** Sidematter files should be
  auto-detectable via consistent naming convention so it is easy for tools to discover
  metadata and asset files.

* **Schema- and format-neutral:** This is a simple convention for attaching metadata and
  assets. It aims to be flexible and unopinionated.
  so does not specify any specifics on asset file formats or metadata schema (other than
  the use of YAML or JSON). The convention works with any file format since sidecars
  don’t modify the original document.

## Format Definition

The sidematter format defines naming conventions for files and directories related to a
*base document*, which can be any file, with any name.

### Path Transformation Rule

Given a base document with filename `basename.extension`, the sidematter files are:

- **Metadata files:** `basename.meta.json` or `basename.meta.yml`

- **Asset directory:** `basename.assets/` (directory containing related files)

The sidematter names are formed by dropping the final extension from the base document
name, then appending the sidematter suffix:

* Files without extensions get sidematter suffixes directly: `README` →
  `README.meta.yml`, `README.assets/`.

* For files with multiple extensions (e.g., `data.tar.gz`), only the final extension is
  dropped: `data.tar.gz` → `data.tar.meta.yml`.

### Metadata Schema

* The schema of metadata files is **free-form and tool-dependent**. Common metadata
  conventions include standard fields like `title`, `description`, `author`,
  `created_at`, and `tags`, but applications are free to define their own schemas.

* Both JSON and YAML are allowed.
  JSON is often preferred for machine-generated metadata due to ubiquitous parsing
  support. YAML is often better for human-authored or human-readable metadata due to
  readability and comment support.

* If there is a schema associated with the metadata, follow the standard convention of
  linking to it with the `$schema` key, so that tools like IDEs can validate the schema.

### Metadata Precedence

In most cases, metadata should only reside in one place, typically `basename.meta.yml`.
Implementations should observe precedence and pick metadata from the first location
found in this order:

1. Metadata JSON: `basename.meta.json`

2. Metadata YAML: `basename.meta.yml`

3. Optionally, implementations can look for
   [frontmatter](https://github.com/jlevy/frontmatter-format) on the file itself (if it
   is a text file)

### Asset Filenames

- **Any asset files are allowed:** The `.assets/` directory structure is free-form and
  tool-dependent. Files can be organized in subdirectories as needed.

- **Relative path resolution:** References from the base document (such as Markdown or
  HTML) to assets should use relative paths starting with the asset directory name.

## Python API Usage

The Python implementation provides a simple reference implementation for reading and
writing sidematter.

### Reading Sidematter

```python
from sidematter_format import smf_read

# Read all sidematter for a document (immutable snapshot)
sidematter = smf_read("report.md")
print(sidematter.meta)  # {'title': 'Q3 Report', 'author': 'Jane Doe', ...}
print(sidematter.meta_path)  # Path('report.meta.yml') or None
print(sidematter.assets_path)  # Path('report.assets') or None
```

### Writing Metadata

```python
from sidematter_format import SidematterPath

# Create a SidematterPath for read/write operations
sp = SidematterPath(Path("report.md"))

# Write metadata as YAML (default)
metadata = {
    "title": "Q3 Financial Analysis",
    "author": "Jane Doe",
    "tags": ["finance", "quarterly"]
}
sp.write_meta(metadata)

# Write metadata as JSON
sp.write_meta(metadata, fmt="json")

# Write pre-formatted YAML/JSON string
sp.write_meta("title: My Report\nauthor: Jane Doe\n")

# Remove all metadata files
sp.write_meta(None)
```

### Managing Assets

```python
from sidematter_format import SidematterPath
from pathlib import Path

sp = SidematterPath(Path("report.md"))

# Get the path for an asset (creates .assets/ directory)
chart_path = sp.asset_path("chart.png")
# Returns: Path('report.assets/chart.png')

# Copy a file into the assets directory
sp.copy_asset("~/Downloads/chart.png")
# or with a custom name:
sp.copy_asset("~/Downloads/fig1.png", dest_name="chart.png")

# Check if assets directory exists
if sp.resolve_assets():
    print(f"Assets found at: {sp.assets_dir}")
```

### Complete Example

```python
from pathlib import Path
from sidematter_format import SidematterPath

# Create a new document with sidematter
doc_path = Path("analysis.md")
doc_path.write_text("# Sales Analysis\n\nSee the trends chart below.")

sp = SidematterPath(doc_path)

# Add metadata
sp.write_meta({
    "title": "2024 Sales Analysis",
    "author": "Data Team",
    "created_at": "2024-01-15",
    "version": "1.0"
})

# Add assets
sp.copy_asset("charts/trends.png")
sp.copy_asset("data/raw_sales.csv")

# Later, read everything back
from sidematter_format import smf_read

data = smf_read(doc_path)
print(f"Title: {data.meta.get('title')}")
print(f"Assets: {list(data.assets_path.iterdir()) if data.assets_path else []}")
```

## FAQ

* **Hasn’t this been done before?** Similar patterns exist in various tools (Jekyll’s
  `_files/` directories, Hugo’s page bundles, etc.), but there’s no universal convention
  that works across different tools and file types.
  This format provides a simple, consistent approach.

* **When should I use sidematter vs frontmatter?** Use **frontmatter format** for small,
  essential metadata, especially on text files of any kind.
  Use **sidematter format** for larger metadata, when the original file cannot be
  modified or metadata that should be updated separately from the original file, or if
  additional asset files are needed.

* **Does this work with version control?** Yes, of course.
  Typically you would check in both metadata and assets, but if it’s easy to put
  `*.assets/` or `*.meta.json` or `*.meta.yml` in `.gitignore` to avoid including them
  in version control.

* **Can I use both YAML and JSON metadata?** Yes, tools should support either or even
  both formats simultaneously.
  The convention is that if present, JSON will be used first, since that is often
  auto-generated or faster to parse.

* * *

## Project Docs

For how to install uv and Python, see [installation.md](installation.md).

For development workflows, see [development.md](development.md).

For instructions on publishing to PyPI, see [publishing.md](publishing.md).

* * *

*This project was built from
[simple-modern-uv](https://github.com/jlevy/simple-modern-uv).*
```
```
