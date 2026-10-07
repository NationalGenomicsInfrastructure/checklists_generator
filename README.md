# Checklists generator

Python script to dynamically generate the bioinfo production checklists for QC, Delivery and Close of NGI sequencing projects. The script uses Quarto to generate the checklists in HTML or markdown format. The checklists are based on templates that can be customized to fit the needs of different projects.

The templates are based on the following internal documents and versions:

- Bioinfo QC: _1617:**6**_
- Delivery: _1286:**23**_
- Close: _1262:**18**_

## Requirements

- Python 3.10 or higher
- Python dependencies: `pip install -r requirements.txt`
- [Quarto](https://quarto.org/docs/get-started/) installed

## Usage

Clone the repository and run the following minimal command in the root directory:

```bash
python generate_checklists.py --output-path . --format html
```

This will generate three checklists (i.e. QC, Delivery and Close) in HTML format in the current directory. It will also generate the corresponding `.qmd` files with the same base name, and place them in the `qmds` folder. A `.qmd` file is a Quarto document that can be edited and rendered to generate a new HTML file with the updated checklist.

A more complete example for a standard delivery:

```bash
python generate_checklists.py --output-path . --format html \
  --project P1234 --flowcell 240101_A01234_0001_ABCDEFGHIJ-ACBSH \
  --author "John Doe" --signature jdoe --email john.doe@scilifelab.se \
  --timestamp --output-structure nested
```

To generate checklists for an Illumina runfolder delivery, pass `--delivery-type runfolder`:

```bash
python generate_checklists.py --output-path . --format html --delivery-type runfolder \
  --project P1234 --flowcell 240101_A01234_0001_ABCDEFGHIJ-ACBSH \
  --runfolder-path /path/to/ngi_data/runfolder
```

For an AVITI instrument, pass `--instrument aviti` (this switches the TACA config from `fastq` to `elements`):

```bash
python generate_checklists.py --output-path . --format html --instrument aviti \
  --project P1234 --flowcell 20240101_BC12345_001_ABCDEFG123-ABC12 \
  --author "John Doe" --signature jdoe --email john.doe@scilifelab.se \
  --timestamp --output-structure nested
```

For a Visium project, pass `--best-practice visium` to generate a fourth checklist for the spatial analysis steps:

```bash
python generate_checklists.py --output-path . --format html --best-practice visium \
  --project P1234 --flowcell 240101_A01234_0001_ABCDEFGHIJ-ACBSH --slide V12A34-567 \
  --visium-base-path /path/to/visium/base --transcriptome-path /path/to/transcriptome \
  --author "John Doe" --signature jdoe --email john.doe@scilifelab.se \
  --timestamp --output-structure nested
```
To save an HTML checklist as a PDF while preserving the ticked checkboxes, open the HTML file in a web browser, tick the completed checklist items, and click the "Download PDF" button in the bottom-right corner (or use the browser's print dialog, e.g. `Ctrl+P` / `Cmd+P`), then choose "Save as PDF" as the destination.

To re-generate any of the checklists after having modified its `.qmd` file, run the following command:

```bash
quarto render qmds/<qmd_file> --to html --embed-resources --standalone
```

Instead, if you want to generate the checklists in markdown format, run:

```bash
quarto render qmds/<qmd_file> --to markdown --embed-resources --standalone
```

## Testing

The test suite uses Python's built-in `unittest` framework and requires no additional test dependencies beyond `rich` (already needed to run the script itself).

Run all tests from the repository root:

```bash
python -m unittest tests -v
```

Run a single test class:

```bash
python -m unittest tests.TestValidateTemplates -v
```

Run a single test method:

```bash
python -m unittest tests.TestParseMarkdownTemplates.test_runfolder_qc_partial_injected -v
```

A passing run looks like this:

```
test_runfolder_delivery_template_used (tests.TestParseMarkdownTemplates) ... ok
test_runfolder_path_not_substituted_when_absent (tests.TestParseMarkdownTemplates) ... ok
test_runfolder_path_substituted (tests.TestParseMarkdownTemplates) ... ok
test_runfolder_qc_partial_injected (tests.TestParseMarkdownTemplates) ... ok
test_standard_delivery_template_used (tests.TestParseMarkdownTemplates) ... ok
test_standard_qc_partial_injected (tests.TestParseMarkdownTemplates) ... ok
test_exceptions (tests.TestValidateFlowcellId) ... ok
test_happy_path (tests.TestValidateFlowcellId) ... ok
test_exceptions (tests.TestValidateProjectId) ... ok
test_happy_path (tests.TestValidateProjectId) ... ok
test_missing_delivery_template_exits (tests.TestValidateTemplates) ... ok
test_missing_qc_partial_exits (tests.TestValidateTemplates) ... ok
test_missing_templates_dir_exits (tests.TestValidateTemplates) ... ok
test_runfolder_passes (tests.TestValidateTemplates) ... ok
test_standard_passes (tests.TestValidateTemplates) ... ok

Ran 15 tests in 0.026s

OK
```

The `ERROR` log lines printed by the `test_missing_*` tests are expected — they are the error messages logged by the script before `exit(1)` is called, which is the behaviour being verified.

Note: the tests do not require Quarto to be installed as they only exercise template parsing and validation, not the final HTML/markdown rendering step.

## Options

- `--help`: Show the help message and exit.
- `--templates-path`: The path to the template files. The default is `templates`. The script expects `QC_template.qmd`, `Close_template.qmd`, and a delivery template named after the delivery type (`Delivery_standard_template.qmd` or `Delivery_runfolder_template.qmd`). The QC template uses a partial from `templates/partials/qc_<delivery-type>.qmd` to inject the type-specific QC steps.
- `--format`: The output format for the checklist: `markdown` or `html`. This is required, either via this option or the `format` key in the configuration file.
- `--name`: The project name (format: `<username>_<year>_<index>`). If not provided, the script will leave a generic placeholder (`<project_name>`) in the output file.
- `--project`: The project ID for which the QC checklist will be generated. If not provided, the script will leave a generic placeholder (`<project_id>`) in the output file.
- `--flowcell`: The flowcell ID for the project. If not provided, the script will leave a generic placeholder (`<flowcell_id>`) in the output file.
- `--slide`: The slide ID (used by the Visium best practice checklist). If not provided, the script will leave a generic placeholder (`<slide_id>`) in the output file.
- `--genome-path`: The path to the genome files. If not provided, the script will leave a generic placeholder (`<genome_path>`) in the output file.
- `--transcriptome-path`: The path to the transcriptome files. If not provided, the script will leave a generic placeholder (`<transcriptome_path>`) in the output file.
- `--author`: The full name of the author. If not provided, the script will not include the author in the output file.
- `--signature`: The author signature (initials) used in the running notes. If not provided, the signature placeholders are removed from the output file.
- `--email`: The email address of the author. If not provided, the script will not include the email in the output file.
- `--delivery-type`: The delivery type, which determines which QC and delivery checklist content is generated. The default is `standard`. Use `runfolder` to generate checklists for Illumina runfolder deliveries, where the raw runfolder is transferred to Miarka and delivered without bcl conversion or demultiplexing.
- `--runfolder-path`: The path to the runfolder on the ngi_data server. Used together with `--delivery-type runfolder` to pre-fill the `<runfolder_path>` placeholder in the TACA transfer command. If not provided, the placeholder is left in the output file.
- `--instrument`: The instrument type: `illumina` (default) or `aviti`.
- `--best-practice`: Set to `visium` to also generate the Visium data analysis checklist.
- `--ngi-path`: The path to the NGI folder on Miarka. This is used to generate the path to the project folders. If not provided, the script will leave a generic placeholder (`<ngi_path>`) in the output file.
- `--incoming-path`: The path to the incoming data folder. If not provided, the script will leave a generic placeholder (`<incoming_path>`) in the output file.
- `--visium-base-path`: The path to the Visium base folder (probe sets, feature references). If not provided, the script will leave a generic placeholder (`<visium_base_path>`) in the output file.
- `--config-path`: The path to the TACA configuration folder. This is used to generate the path to the project folders. If not provided, the script will leave a generic placeholder (`<config_path>`) in the output file.
- `--genstat-url`: The URL for the Genomics Status page. If not provided, the script will leave a generic placeholder (`<genstat_url>`) in the output file.
- `--charon-url`: The URL for the Charon page. If not provided, the script will leave a generic placeholder (`<charon_url>`) in the output file.
- `--quarto-path`: The path to the Quarto executable. If not provided, or if the executable is not found at the given path, the script will attempt to search for `quarto` in the system path.
- `--output-path`: The directory where the output files will be saved. The default is the current directory.
- `--local-reports-path`: The local path where the MultiQC and reports folders are saved. If not provided, the script will leave a generic placeholder (`<local_reports_path>`) in the output file.
- `--timestamp`: Whether to include a timestamp in the output file name. The default is `False`. If `True`, the output files will be named `<YYYYMMDD>_<project_id>_<Label>.{html,md,qmd}` (e.g. `20260127_P37871_QC.html`).
- `--output-structure`: The structure of the output. The default is `flat`. The other option is `nested`. If `nested` is selected, the output files will be saved in a subdirectory named after the timestamp and project ID.
- `--script-assets-path`: The path to the assets folder used by the templates. The default is the `assets` folder in this repository.
- `--force`: Force overwrite of existing files. If not provided and the output file already exists, the script will not overwrite it and will exit with an error message.
- `--log-level`: The logging level. The default is `INFO`. Other options are `DEBUG`, `WARNING`, `ERROR`, and `CRITICAL`. This can be set to `DEBUG` for more detailed logging information.

## Configuration file

If a `config.json` file is present in the same directory as the script, it will be used to set the default values for all or some of the options. The configuration file should be in JSON format and can include the following keys:

- `delivery_type [string]`
- `runfolder_path [string]`
- `templates_path [string]`
- `format [string]`
- `project [string]`
- `flowcell [string]`
- `author [string]`
- `email [string]`
- `ngi_path [string]`
- `incoming_path [string]`
- `config_path [string]`
- `genstat_url [string]`
- `charon_url [string]`
- `quarto_path [string]`
- `output_path [string]`
- `timestamp [bool]`
- `output_structure [string]`
- `force [bool]`
- `log_level [string]`
- `slide [string]`
- `genome_path [string]`
- `transcriptome_path [string]`
- `instrument [string]`
- `visium_base_path [string]`
- `local_reports_path [string]`
- `script_assets_path [string]`

> Note: `config.json` is gitignored and will not be tracked. To get started, copy `config.json.example` to `config.json` and fill in the values that apply to your environment. Any keys omitted from `config.json` will fall back to their command-line argument counterparts.

### Example of `config.json` file:

```json
{
  "author": "Your Name",
  "email": "your.name@scilifelab.se",
  "format": "markdown",
  "output_path": "/path/to/output/directory",
  "output_structure": "nested",
  "quarto_path": "/usr/local/bin/quarto",
  "ngi_path": "/path/to/NGI/folder",
  "incoming_path": "/path/to/incoming/folder",
  "genstat_url": "https://genomics-status.example.com",
  "charon_url": "https://charon.example.com",
  "config_path": "/path/to/conf/TACA",
  "log_level": "INFO"
}
```
