#!/usr/bin/env python3
import os
import argparse
import json
import logging
import pathlib
import re
import shutil
import subprocess
import sys
import yaml
from datetime import datetime
from rich.logging import RichHandler


# Asset injected into the HTML output so that ticked checkboxes are
# preserved when the page is printed or saved as a PDF
CHECKBOX_PRINT_ASSET = "checkbox_print.html"


logging.basicConfig(
    format="%(message)s",
    # format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[RichHandler()],
)


def create_parser():
    """Create and return the argument parser."""
    parser = argparse.ArgumentParser(
        description="Generate the bioinformatic production checklists (QC, Delivery, Close) from Quarto templates."
    )
    parser.add_argument(
        "--templates-path",
        type=pathlib.Path,
        help="Path to the template file.",
        default=pathlib.Path("templates"),
    )
    parser.add_argument(
        "--format",
        type=str,
        help="Output format for the checklist.",
        default=None,
        choices=["markdown", "html"],
    )
    parser.add_argument(
        "--name",
        type=str,
        help="Project name.",
        default=None,
    )
    parser.add_argument(
        "--project",
        type=str,
        help="Project identifier.",
        default=None,
    )
    parser.add_argument(
        "--flowcell",
        type=str,
        help="Flowcell identifier.",
        default=None,
    )
    parser.add_argument(
        "--slide",
        type=str,
        help="Slide identifier.",
        default=None,
    )
    parser.add_argument(
        "--genome-path",
        type=pathlib.Path,
        help="Genome path.",
        default=None,
    )
    parser.add_argument(
        "--transcriptome-path",
        type=pathlib.Path,
        help="Transcriptome path.",
        default=None,
    )
    parser.add_argument(
        "--author",
        type=str,
        help="Author name.",
        default=None,
    )
    parser.add_argument(
        "--signature",
        type=str,
        help="Author signature.",
        default=None,
    )
    parser.add_argument(
        "--email",
        type=str,
        help="Author email.",
        default=None,
    )
    parser.add_argument(
        "--instrument",
        type=str,
        help="Instrument type.",
        default="illumina",
        choices=["illumina", "aviti"],
    )
    parser.add_argument(
        "--delivery-type",
        type=str,
        help="Delivery type for the checklist.",
        default=None,
        choices=["standard", "runfolder"],
    )
    parser.add_argument(
        "--runfolder-path",
        type=pathlib.Path,
        help="Path to the runfolder on the ngi_data server (used with --delivery-type runfolder).",
        default=None,
    )
    parser.add_argument(
        "--best-practice",
        type=str,
        help="Best practice workflow to include in the checklists.",
        default=None,
        choices=["visium"],
    )
    parser.add_argument(
        "--ngi-path",
        type=pathlib.Path,
        help="Path to the NGI folder.",
        default=None,
    )
    parser.add_argument(
        "--incoming-path",
        type=pathlib.Path,
        help="Path to the incoming data folder.",
        default=None,
    )
    parser.add_argument(
        "--visium-base-path",
        type=pathlib.Path,
        help="Path to the Visium Base path directory.",
        default=None,
    )
    parser.add_argument(
        "--config-path",
        type=pathlib.Path,
        help="Path to the config files directory.",
        default=None,
    )
    parser.add_argument(
        "--genstat-url",
        type=str,
        help="Base URL for Genomics Status.",
        default=None,
    )
    parser.add_argument(
        "--charon-url",
        type=str,
        help="Base URL for Charon.",
        default=None,
    )
    parser.add_argument(
        "--quarto-path",
        type=pathlib.Path,
        help="Path to the Quarto executable.",
        default=None,
    )
    parser.add_argument(
        "--output-path",
        type=pathlib.Path,
        help="Path to the output directory.",
        default=None,
    )
    parser.add_argument(
        "--local-reports-path",
        type=pathlib.Path,
        help="Path to where MultiQC and reports folder should be saved locally.",
        default=None,
    )
    parser.add_argument(
        "--timestamp",
        action="store_true",
        default=False,
        help="Add a timestamp to the output filename.",
    )
    parser.add_argument(
        "--output-structure",
        type=str,
        help="Output structure for the checklist.",
        default=None,
        choices=["flat", "nested"],
    )
    parser.add_argument(
        "--script-assets-path",
        type=pathlib.Path,
        help="Path to the assets required by this script.",
        default=None,
    )
    parser.add_argument(
        "--force",
        action="store_true",
        default=False,
        help="Force overwrite of existing files.",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        help="Set the logging level. Default is INFO.",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
    )
    return parser


def parse_args():
    """Parse command-line arguments."""
    parser = create_parser()
    return parser.parse_args()


def set_run_parameters(args):
    """Set the run parameters based on the command-line arguments."""
    config = {}
    script_dir = pathlib.Path(__file__).resolve().parent
    # Valid config keys (must match argparse argument destination names)
    _parser = create_parser()
    VALID_CONFIG_KEYS = {k.dest for k in _parser._actions}
    # Argument defaults, used to tell explicit CLI values apart from unset ones
    arg_defaults = {k.dest: k.default for k in _parser._actions if k.dest}
    # Load the config file if it exists
    config_file = script_dir.joinpath("config.json")
    if config_file.is_file():
        with open(config_file, "r") as f:
            raw_config = json.load(f)
        if not isinstance(raw_config, dict):
            logging.error(
                "config.json must contain a JSON object (key-value pairs), "
                f"got {type(raw_config).__name__}."
            )
            sys.exit(1)
        # Check for unknown keys
        unknown = {k for k in raw_config if k not in VALID_CONFIG_KEYS}
        if unknown:
            logging.warning(
                f"One or more keys in the config file are not recognized: {unknown}"
            )
        # Validate required keys exist and have correct types
        required_keys = {
            "format": str,
            "output_path": str,
            "quarto_path": str,
            "log_level": str,
        }
        for key, expected_type in required_keys.items():
            if key not in raw_config:
                logging.error(
                    f"Required config key '{key}' is missing from config.json."
                )
                sys.exit(1)
            if not isinstance(raw_config[key], expected_type):
                logging.error(
                    f"Config key '{key}' must be a {expected_type.__name__}, "
                    f"got {type(raw_config[key]).__name__}."
                )
                sys.exit(1)
        # Check for null/None values on required string keys
        for key, expected_type in required_keys.items():
            if raw_config[key] is None:
                logging.error(
                    f"Config key '{key}' cannot be null. Please set a value in config.json."
                )
                sys.exit(1)
        # Validate best_practice choices
        if "best_practice" in raw_config and raw_config["best_practice"] not in (
            "visium",
            "",
        ):
            logging.error(
                f"Config key 'best_practice' must be 'visium' or empty, got '{raw_config['best_practice']}'."
            )
            sys.exit(1)
        config = raw_config
        for key, value in config.items():
            if "path" in key or "dir" in key:
                # Convert string paths to pathlib.Path objects
                p = pathlib.Path(value)
                if key == "templates_path" and not p.is_absolute():
                    p = script_dir.joinpath(p)
                resolved = p.resolve()
                if ".." in p.parts:
                    logging.error(f"Path traversal detected in '{key}': {value}")
                    sys.exit(1)
                if key == "templates_path" and not resolved.is_relative_to(script_dir):
                    logging.error(
                        f"Templates path must resolve to within the project directory. "
                        f"Got '{resolved}' but project root is '{script_dir}'."
                    )
                    sys.exit(1)
                config[key] = p

    # Re-set the config parameters based on command-line arguments.
    # A CLI value only overrides the config file when it was explicitly set
    # (i.e. differs from the argparse default).
    for key, value in vars(args).items():
        if key not in config or value != arg_defaults.get(key):
            # Update the config with command-line arguments
            if key in ("templates_path",):
                p = (
                    pathlib.Path(value)
                    if not isinstance(value, pathlib.Path)
                    else value
                )
                if not p.is_absolute():
                    p = script_dir.joinpath(p)
                resolved = p.resolve()
                if not resolved.is_relative_to(script_dir):
                    logging.error(
                        f"Templates path must resolve to within the project directory. "
                        f"Got '{resolved}' but project root is '{script_dir}'."
                    )
                    sys.exit(1)
                config[key] = p
            else:
                config[key] = value

    # Set the output directory and file basename
    prefix = f"{datetime.now().strftime('%Y%m%d')}_" if config.get("timestamp") else ""
    prefix += f"{config['project']}_" if config["project"] else ""
    config["basename"] = prefix[:-1] if prefix.endswith("_") else prefix
    config["basename"] = re.sub(r"[^A-Za-z0-9_\-\.]", "", config["basename"])
    if config["basename"] != "" and config["output_structure"] == "nested":
        config["output_path"] = config["output_path"].joinpath(config["basename"])
        if not config["output_path"].is_dir():
            config["output_path"].mkdir(parents=True, exist_ok=True)

    # Set default for delivery_type
    if not config.get("delivery_type"):
        config["delivery_type"] = "standard"

    return config


def validate_project_id(project_id: str) -> None:
    """Validate the project ID format."""
    if not re.match(r"^P[0-9]{4,5}$", project_id):
        raise ValueError(
            "Project ID must start with 'P' followed by 4 to 5 digits (e.g., P1234 or P12345)."
        )


def validate_project_name(project_name: str) -> None:
    """Validate the project name format."""
    if not re.match(r"^[A-Z]\.[A-Za-z]+_[0-9]{2}_[0-9]{2}$", project_name):
        raise ValueError(
            "Project Name is not in the expected format. Please check the input or drop the option."
        )


def validate_flowcell_id(flowcell_id: str) -> None:
    """Validate the flowcell ID format."""
    if (
        not re.match(
            r"^[0-9]{6,8}_[A-Z]{1,2}[0-9]{5}_[0-9]{3,4}_[A-Z0-9]{9,10}(-[A-Z0-9]{5})?$",  # NovaSeq flowcell format
            flowcell_id,
        )
        and not re.match(
            r"^[0-9]{8}_[A-Z]{2}[0-9]{6}_[A-Z][0-9]{10}$",  # AVITI flowcell format
            flowcell_id,
        )
        and not re.match(
            r"^[0-9]{6,8}_[A-Z]{1,2}[0-9]{5}(R)?_[0-9]{1,3}_[A-Z0-9]{9,10}(-[A-Z0-9]{5})?$",  # NextSeq flowcell format
            flowcell_id,
        )
    ):
        raise ValueError(
            "Flowcell ID is not in the expected format. Please check the ID."
        )


# Template label to lowercase header type mapping for prepare_markdown_header
TEMPLATE_HEADER_MAP = {
    "QC": "qc",
    "Delivery": "delivery",
    "Close": "close",
    "Visium": "visium",
}


# generate template labels and their corresponding filenames (label: template_file)
def get_required_templates(delivery_type: str) -> list[dict]:
    return [
        {"label": "QC", "file": "QC_template.qmd"},
        {
            "label": f"Delivery_{delivery_type}",
            "file": f"Delivery_{delivery_type}_template.qmd",
        },
        {"label": "Close", "file": "Close_template.qmd"},
    ]


def validate_quarto_path(quarto_path):
    """Validate the Quarto path."""
    if quarto_path is not None:
        quarto_path = pathlib.Path(quarto_path)
        try:
            proc = subprocess.run(
                [str(quarto_path), "--version"], capture_output=True, text=True
            )
        except OSError:
            proc = None
        if proc is not None and proc.returncode == 0:
            return quarto_path, proc.stdout.strip()
        logging.warning(
            f"Quarto not found at configured path '{quarto_path}'. "
            "Attempting to find it in the system path."
        )
    else:
        logging.warning(
            "No Quarto path configured. Attempting to find it in the system path."
        )
    found = shutil.which("quarto")
    if found is None:
        logging.error("Quarto not found in the system path.")
        sys.exit(1)
    quarto_path = pathlib.Path(found)
    logging.warning(f"Falling back to quarto from system path: {quarto_path}")
    proc = subprocess.run(
        [str(quarto_path), "--version"], capture_output=True, text=True
    )
    quarto_version = proc.stdout.strip() if proc.returncode == 0 else ""
    return quarto_path, quarto_version


def validate_templates(
    template_path: pathlib.Path,
    extra_templates: list = None,
    delivery_type: str = "standard",
):
    """Validate the template path."""
    if extra_templates is None:
        extra_templates = []
    if not template_path.is_dir():
        logging.error("The specified template path does not exist.")
        sys.exit(1)
    required_templates = [
        t["file"] for t in get_required_templates(config["delivery_type"])
    ] + extra_templates
    missing_templates = [
        template
        for template in required_templates
        if not template_path.joinpath(template).is_file()
    ]
    if missing_templates:
        logging.error(
            f"The following required templates are missing: {', '.join(missing_templates)}"
        )
        exit(1)
    partial_path = template_path / "partials" / f"qc_{delivery_type}.qmd"
    if not partial_path.is_file():
        logging.error(f"Required QC partial template not found: {partial_path}")
        exit(1)


def prepare_markdown_header(config: dict, template: str):
    """Prepare the markdown header with project and author information."""
    # Set the title and subtitle based on the template
    if template == "qc":
        title = "QC and Delivery"
        subtitle = "Bioinformatic Sample QC and Preparation for Data Delivery"
    elif re.match("delivery.*", template):
        title = "Delivery"
        subtitle = "Bioinformatic Sample Delivery"
    elif template == "close":
        title = "Close"
        subtitle = "Bioinformatic Sample Close"
    elif template == "visium":
        title = "Visium Data Analysis"
        subtitle = "Non-Accredited Bioinformatic Analysis"
    else:
        logging.error(f"Unknown template '{template}'. Cannot prepare markdown header.")
        sys.exit(1)
    html_format = {
        "page-layout": "full",
        "anchor-sections": True,
        "collapse": True,
        "tbl-cap-location": "bottom",
        "theme": {
            "light": "flatly",
            "dark": "darkly",
        },
    }
    assets_path = config.get("script_assets_path")
    if assets_path:
        print_asset = pathlib.Path(assets_path).joinpath(CHECKBOX_PRINT_ASSET).resolve()
        if print_asset.is_file():
            # Inject the checkbox print styles and the "Download PDF"
            # helper button into the HTML output header
            html_format["include-in-header"] = str(print_asset)
        else:
            logging.warning(
                f"The checkbox print asset was not found at '{print_asset}'. "
                "Ticked checkboxes will not be preserved when the HTML "
                "output is saved as a PDF."
            )

    # Prepare the markdown header using yaml.dump for safe escaping
    header = {
        "title": f"{config['project']} {title}"
        if config.get("project")
        else f"Bioinformatic {title}",
        "subtitle": subtitle,
        "description": "Automatically generated checklist",
        "date": "today",
        "lang": "en-GB",
        "format": {
            "html": html_format,
            "commonmark": {
                "wrap": "none",
            },
        },
        "version": "1.0",
    }
    if config.get("author"):
        if config.get("email"):
            header["author"] = f"{config['author']} <{config['email']}>"
        else:
            header["author"] = config["author"]
    yaml_body = yaml.dump(
        header,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
        indent=2,
        width=120,
    )
    return f"---\n{yaml_body}\n---\n"


def parse_markdown_templates(config: dict) -> dict:
    """Parse the markdown templates and replace placeholders with actual values."""

    def parse_line(config, line):
        """Parse a line of the template and replace placeholders with actual values."""
        line = (
            line.replace("<project_id>", str(config["project"]))
            if config["project"]
            else line
        )
        line = (
            line.replace("<project_name>", str(config["name"]))
            if config["name"]
            else line
        )
        line = (
            line.replace("<flowcell_id>", str(config["flowcell"]))
            if config["flowcell"]
            else line
        )
        line = (
            line.replace("<slide_id>", str(config["slide"]))
            if config["slide"]
            else line
        )
        line = (
            line.replace("<genome_path>", str(config["genome_path"]))
            if config["genome_path"]
            else line
        )
        line = (
            line.replace("<transcriptome_path>", str(config["transcriptome_path"]))
            if config["transcriptome_path"]
            else line
        )
        line = (
            line.replace("<author_name>", str(config["author"]))
            if config.get("author")
            else line
        )
        if config.get("signature", ""):
            line = line.replace("<author_signature>", "/" + config["signature"])
            line = line.replace("<user_signature>", config["signature"])
        else:
            line = line.replace("<author_signature>", "")
            line = line.replace("<user_signature>", "")
        line = (
            line.replace("<ngi_path>", str(config["ngi_path"]))
            if config["ngi_path"]
            else line
        )
        line = (
            line.replace("<incoming_path>", str(config["incoming_path"]))
            if config.get("incoming_path")
            else line
        )
        line = (
            line.replace("<visium_base_path>", str(config["visium_base_path"]))
            if config["visium_base_path"]
            else line
        )
        line = (
            line.replace("<local_reports_path>", str(config["local_reports_path"]))
            if config["local_reports_path"]
            else line
        )
        if config.get("instrument"):
            substitution = "element" if config["instrument"] == "aviti" else "fastq"
            line = line.replace("<instrument_config>", substitution)
            substitution = "aviti" if config["instrument"] == "aviti" else ""
            line = line.replace("<instrument_path>", substitution)
        line = (
            line.replace("<genstat_url>", str(config["genstat_url"]))
            if config.get("genstat_url")
            else line
        )
        line = (
            line.replace("<charon_url>", str(config["charon_url"]))
            if config.get("charon_url")
            else line
        )
        line = (
            line.replace("<assets_path>", str(config["script_assets_path"]))
            if config["script_assets_path"]
            else line
        )
        line = (
            line.replace("<config_path>", str(config["config_path"]))
            if config.get("config_path")
            else line
        )
        return line

    def write_template(label: str, template_name: str = None):
        """Write the template content to the output file."""
        outname = (
            f"{config['basename']}_{label}.qmd"
            if config["basename"] != ""
            else f"{label}.qmd"
        )
        template_file_name = f"{template_name or label}_template.qmd"
        with open(outname, "w") as output_file:
            output_file.write(header)
            # Write the template content
            with open(
                config["templates_path"].joinpath(template_file_name), "r"
            ) as template_file:
                for line in template_file:
                    if line.strip() == "<qc_type_section>":
                        partial_path = (
                            config["templates_path"]
                            / "partials"
                            / f"qc_{config['delivery_type']}.qmd"
                        )
                        with open(partial_path, "r") as partial_file:
                            for partial_line in partial_file:
                                output_file.write(parse_line(config, partial_line))
                    else:
                        output_file.write(parse_line(config, line))

    results_dict = {}
    for tmpl in get_required_templates(config["delivery_type"]):
        label = tmpl["label"]
        outname = (
            f"{config['basename']}_{label}.qmd"
            if config["basename"] != ""
            else f"{label}.qmd"
        )
        results_dict[label] = outname
        header = prepare_markdown_header(
            config, TEMPLATE_HEADER_MAP.get(label, label.lower())
        )
        write_template(label)

    if config["best_practice"] == "visium":
        label = "Visium"
        outname = (
            f"{config['basename']}_{label}.qmd"
            if config["basename"] != ""
            else f"{label}.qmd"
        )
        results_dict[label] = outname
        header = prepare_markdown_header(config, "visium")
        write_template(label)

    return results_dict


def generate_markdown_output(config: dict, cmd: list, label: str):
    """Generate the markdown output using Quarto."""
    logging.debug("Generating markdown via Quarto...")
    try:
        _ = subprocess.run(cmd, shell=False, check=True, capture_output=True)
        output_stream = []
        outname = (
            f"{config['basename']}_{label}.md"
            if config["basename"] != ""
            else f"{label}.md"
        )
        with open(config["output_path"].joinpath(outname), "r") as input_file:
            for line in input_file:
                if line.startswith("<"):
                    # Remove some HTML tags for aesthetic purposes
                    line = re.sub(r"<div>", "", line).strip()
                    line = re.sub(r"</div>", "", line).strip()
                if line.startswith(">"):
                    line = re.sub(r"> -", "-", line)
                line = re.sub(r"☐", "[ ]", line)
                output_stream.append(line)
        with open(config["output_path"].joinpath(outname), "w") as output_file:
            for line in output_stream:
                output_file.write(line)
        logging.debug("Markdown file generated successfully.")
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode("utf-8", errors="replace")
        logging.error(f"Error generating markdown (exit code {e.returncode}): {stderr}")
        sys.exit(1)


def generate_html_output(config: dict, cmd: list):
    """Generate the HTML output using Quarto."""
    logging.debug("Generating HTML via Quarto...")
    try:
        _ = subprocess.run(cmd, shell=False, check=True, capture_output=True)
        logging.debug("HTML file generated successfully.")
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode("utf-8", errors="replace")
        logging.error(f"Error generating HTML (exit code {e.returncode}): {stderr}")
        sys.exit(1)


def cleanup_temporary_data(config: dict):
    """Remove temporary files and directories created during the process."""
    script_dir = pathlib.Path(__file__).resolve().parent
    workdirs = (script_dir, pathlib.Path.cwd())
    # Move the generated qmd files to the qmds directory
    for workdir in workdirs:
        files_list = list(workdir.glob(f"{config['basename']}*.qmd"))
        for qmd in files_list:
            if qmd.is_file():
                qmd.rename(config["qmds_path"].joinpath(qmd.name))

    # Remove the quarto resource folders. These are created next to the
    # source qmd files (i.e. in the working directory), not in the output
    # directory, so only look at the top level of the working directories.
    for workdir in workdirs:
        paths_list = list(workdir.glob(f"{config['basename']}_*_files"))
        for tmp_path in paths_list:
            for path, dirs, files in tmp_path.walk(top_down=False):
                for file in files:
                    file_path = pathlib.Path(path).joinpath(file)
                    if file_path.is_file():
                        logging.debug(f"Removing temporary file: {file_path}")
                        file_path.unlink()
                logging.debug(f"Removing temporary directory: {path}")
                path.rmdir()


if __name__ == "__main__":
    # Parse command-line arguments
    args = parse_args()

    if not args.script_assets_path:
        args.script_assets_path = (
            pathlib.Path(os.path.dirname(__file__)).joinpath("assets").resolve()
        )

    # Set the run parameters according to the command-line arguments and config file
    config = set_run_parameters(args)

    # Set the logging level based on the merged configuration
    logging.getLogger().setLevel(config["log_level"])

    # Validate the output format before any file is written
    if config["format"] not in ("markdown", "html"):
        logging.error(
            "A valid output format is required. Use 'markdown' or 'html' "
            "via --format or the config file."
        )
        sys.exit(1)

    # Validate the project ID
    if config["project"]:
        validate_project_id(config["project"])

    # Validate the project Name
    if config["name"]:
        validate_project_name(config["name"])

    # Validate the flowcell ID
    if config["flowcell"]:
        validate_flowcell_id(config["flowcell"])

    # Check if the Quarto executable exists and is accessible
    config["quarto_path"], quarto_version = validate_quarto_path(config["quarto_path"])

    # Check if the template file exists
    extra_templates = (
        ["Visium_template.qmd"] if config["best_practice"] == "visium" else []
    )
    validate_templates(
        config["templates_path"], extra_templates, config["delivery_type"]
    )

    # Create the output directory if it doesn't exist
    config["output_path"].mkdir(parents=True, exist_ok=True)

    # Set the path for the Quarto markdown files, and create the directory if it doesn't exist
    config["qmds_path"] = pathlib.Path(__file__).resolve().parent.joinpath("qmds")
    config["qmds_path"].mkdir(parents=True, exist_ok=True)

    # Check if the output directory exists
    if not config["force"]:
        if config["basename"] != "":
            files_list = [
                x
                for x in config["output_path"].glob(f"{config['basename']}*")
                if x.is_file()
            ]
        else:
            files_list = [
                x
                for x in [
                    "QC.html",
                    "QC.md",
                    "QC.qmd",
                    "Delivery.html",
                    "Delivery.md",
                    "Delivery.qmd",
                    "Close.html",
                    "Close.md",
                    "Close.qmd",
                ]
                if config["output_path"].joinpath(x).is_file()
            ]
            files_list += (
                ["Visium.html", "Visium.md", "Visium.qmd"]
                if config["best_practice"] == "visium"
                else []
            )
        if files_list:
            logging.error(
                "The following files already exist and will not be overwritten:"
            )
            for file in files_list:
                logging.error(f"    '{file}'")
            logging.error(
                "Use --force to overwrite existing files or specify a different output directory."
            )
            sys.exit(1)

    # Summarise the run parameters
    logging.debug("-" * 40)
    logging.debug("Run Parameters:")
    logging.debug(f"    Quarto Path: '{config['quarto_path']}'")
    logging.debug(f"    Quarto Version: {quarto_version}")
    logging.debug(f"    Templates Path: '{config['templates_path'].resolve()}'")
    logging.debug(f"    Project Name: '{config['name']}'")
    logging.debug(f"    Project ID: '{config['project']}'")
    logging.debug(f"    Flowcell ID: '{config['flowcell']}'")
    logging.debug(f"    Instrument: {config['instrument']}")
    logging.debug(f"    NGI Path: '{config['ngi_path']}'")
    if config["best_practice"]:
        logging.debug(f"    Genome Path: {config['genome_path']}")
        logging.debug(f"    Transcriptome Path: {config['transcriptome_path']}")
    logging.debug(f"    Author: '{config['author']}'")
    logging.debug(f"    Author Signature: '{config['signature']}'")
    logging.debug(f"    Author Email: '{config['email']}'")
    logging.debug(f"    Output Directory: '{config['output_path']}'")
    logging.debug(f"    Output Format: {config['format']}")
    logging.debug(f"    Output Structure: {config['output_structure']}")
    logging.debug(f"    Local Reports Directory: '{config['local_reports_path']}'")
    logging.debug(f"    Assets Directory: '{config['script_assets_path']}'")
    logging.debug(f"    Timestamp: {config['timestamp']}")
    if config["format"] == "markdown":
        logging.debug(f"    Markdown Output Path: '{config['output_path']}'")
        logging.debug(f"    Markdown Filename: '{config['basename']}.md'")
    else:
        logging.debug(f"    HTML Output Path: '{config['output_path']}'")
        logging.debug(f"    HTML Filename: '{config['basename']}.html'")
    logging.debug("-" * 40)

    # Write the markdown template, including the dynamic content
    templates_dict = parse_markdown_templates(config)

    for key, template in templates_dict.items():
        logging.debug(f"Generating {key} output using template: {template}")
        # Prepare the base command to run Quarto
        cmd = [
            str(config["quarto_path"]),
            "render",
            template,
            "--no-clean",
            "--output-dir",
            str(config["output_path"]),
            "--execute-dir",
            str(config["output_path"]),
        ]
        if config["format"] == "markdown":
            outname = (
                f"{config['basename']}_{key}.md"
                if config["basename"] != ""
                else f"{key}.md"
            )
            cmd.extend(["--to", "commonmark", "--output", outname])
            # Generate the Markdown file and place it in the specified directory
            generate_markdown_output(config, cmd, key)

        elif config["format"] == "html":
            outname = (
                f"{config['basename']}_{key}.html"
                if config["basename"] != ""
                else f"{key}.html"
            )
            html_flags = [
                "--to",
                "html",
                "--embed-resources",
                "--standalone",
                "--output",
                outname,
            ]
            if logging.getLogger().level <= logging.DEBUG:
                html_flags.extend(["--log-level", "debug"])
            cmd.extend(html_flags)
            # Generate the HTML file and place it in the specified directory
            generate_html_output(config, cmd)
        else:
            logging.error("Invalid format specified. Use 'markdown' or 'html'.")
            sys.exit(1)

    logging.info("All output files generated successfully.")
    logging.debug("-" * 40)

    logging.debug("Cleaning up temporary files and folders...")
    cleanup_temporary_data(config)

    logging.debug("-" * 40)
