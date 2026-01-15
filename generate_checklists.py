#!/usr/bin/env python3
import argparse
import json
import logging
import pathlib
import re
import subprocess
from datetime import datetime

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S",
)


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Generate a list of files in a directory."
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
        "--project",
        type=str,
        help="Project name.",
        default=None,
    )
    parser.add_argument(
        "--flowcell",
        type=str,
        help="Flowcell identifier.",
        default=None,
    )
    parser.add_argument(
        "--author",
        type=str,
        help="Author name.",
        default=None,
    )
    parser.add_argument(
        "--email",
        type=str,
        help="Author email.",
        default=None,
    )
    parser.add_argument(
        "--ngi-path",
        type=pathlib.Path,
        help="Path to the NGI folder.",
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
    return parser.parse_args()


def set_run_parameters(args):
    """Set the run parameters based on the command-line arguments."""
    config = {}
    # Load the config file if it exists
    if pathlib.Path("config.json").is_file():
        with open("config.json", "r") as f:
            config = json.load(f)
        # Check for alien keys in the config file
        not_found = {key for key in config.keys() if key not in vars(args).keys()}
        if not_found:
            logging.warning(
                f"One or more keys in the config file are not among the expected keys: {not_found}"
            )
        for key, value in config.items():
            if "path" in key or "dir" in key:
                # Convert string paths to pathlib.Path objects
                config[key] = pathlib.Path(value)

    # Re-set the config parameters based on command-line arguments
    for key, value in vars(args).items():
        if key not in config or value is not None:
            # Update the config with command-line arguments
            config[key] = value

    # Set the output directory and file basename
    prefix = f"{datetime.now().strftime('%Y%m%d')}_" if args.timestamp else ""
    prefix += f"{config['project']}_" if config["project"] else ""
    config["basename"] = prefix[:-1] if prefix.endswith("_") else prefix
    if config["basename"] != "" and config["output_structure"] == "nested":
        config["output_path"] = config["output_path"].joinpath(config["basename"])
        if not config["output_path"].is_dir():
            config["output_path"].mkdir(parents=True, exist_ok=True)

    return config


def validate_project_id(project_id: str):
    """Validate the project ID format."""
    if not re.match(r"^P[0-9]{5}$", project_id):
        raise ValueError(
            "Project ID must start with 'P' followed by 4 or 5 digits (e.g., P1234 or P12345)."
        )


def validate_flowcell_id(flowcell_id: str):
    """Validate the flowcell ID format."""
    if not re.match(
        r"^[0-9]{6,8}_[A-Z]{1,2}[0-9]{5}_[0-9]{3,4}_[A-Z0-9]{9,10}(-[A-Z0-9]{5})?$",
        flowcell_id,
    ):
        raise ValueError(
            "Flowcell ID is not in the expected format. Please check the ID."
        )


def validate_quarto_path(quarto_path: pathlib.Path):
    """Validate the Quarto path."""
    # Check if the Quarto executable exists and is accessible
    status, quarto_version = subprocess.getstatusoutput(f"{quarto_path} --version")
    if status != 0:
        logging.error(
            "Quarto not found in the specified path. Attempting to find it in the system path."
        )
        # Attempt to find Quarto in the system path
        status, quarto_path = subprocess.getstatusoutput("which quarto")
        if status != 0:
            logging.error("Quarto not found in the system path.")
            exit(1)
        else:
            status, quarto_version = subprocess.getstatusoutput(
                f"{quarto_path} --version"
            )
    return pathlib.Path(quarto_path), quarto_version


def validate_templates(template_path: pathlib.Path):
    """Validate the template path."""
    if not template_path.is_dir():
        logging.error("The specified template path does not exist.")
        exit(1)
    required_templates = [
        "QC_template.qmd",
        "Delivery_template.qmd",
        "Close_template.qmd",
    ]
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


def prepare_markdown_header(config: dict, template: str):
    """Prepare the markdown header with project and author information."""
    # Set the title and subtitle based on the template
    if template == "qc":
        title = "QC and Delivery"
        subtitle = "Bioinformatic Sample QC and Preparation for Data Delivery"
    elif template == "delivery":
        title = "Delivery"
        subtitle = "Bioinformatic Sample Delivery"
    elif template == "close":
        title = "Close"
        subtitle = "Bioinformatic Sample Close"
    else:
        logging.error(f"Unknown template '{template}'. Cannot prepare markdown header.")
        exit(1)
    # Prepare the markdown header
    md_header = "---\n"
    md_header += (
        f"title: {config['project']} {title}\n"
        if config["project"]
        else "title: Bioinformatic {title}\n"
    )
    md_header += (
        f"author: {config['author']} <{config['email']}>\n"
        if config["author"] and config["email"]
        else f"author: {config['author']}\n"
        if config["author"]
        else ""
    )
    md_header += "\n".join(
        [
            f"subtitle: '{subtitle}'",
            "description: 'Automatically generated checklist'",
            "date: today",
            "lang: en-GB",
            "format:",
            "  html:",
            "    page-layout: full",
            "    anchor-sections: true",
            "    tbl-cap-location: bottom",
            "    theme:",
            "      light: flatly",
            "      dark: darkly",
            "  commonmark:",
            "    wrap: none",
            "version: 1.0",
            "---",
            "",
        ]
    )
    return md_header


def parse_markdown_templates(config: dict) -> dict:
    """Parse the markdown templates and replace placeholders with actual values."""

    def parse_line(config, line):
        """Parse a line of the template and replace placeholders with actual values."""
        if config["project"]:
            line = re.sub(r"<project_id>", f"{config['project']}", line)
        if config["flowcell"]:
            line = re.sub(r"<flowcell_id>", f"{config['flowcell']}", line)
        if config["author"]:
            line = re.sub(r"<author_name>", f"{config['author']}", line)
        if config["ngi_path"]:
            line = re.sub(r"<ngi_path>", f"{config['ngi_path']}", line)
        if config["genstat_url"]:
            line = re.sub(r"<genstat_url>", f"{config['genstat_url']}", line)
        if config["charon_url"]:
            line = re.sub(r"<charon_url>", f"{config['charon_url']}", line)
        if config["config_path"]:
            line = re.sub(r"<config_path>", f"{config['config_path']}", line)
        return line

    def write_template(label: str):
        """Write the template content to the output file."""
        outname = (
            f"{config['basename']}_{label}.qmd"
            if config["basename"] != ""
            else f"{label}.qmd"
        )
        with open(outname, "w") as output_file:
            output_file.write(header)
            # Write the template content
            with open(
                config["templates_path"].joinpath(f"{label}_template.qmd"), "r"
            ) as template_file:
                for line in template_file:
                    output_file.write(parse_line(config, line))

    # Prepare QC template
    header = prepare_markdown_header(config, "qc")
    write_template("QC")

    # Prepare Delivery template
    header = prepare_markdown_header(config, "delivery")
    write_template("Delivery")

    # Prepare Close template
    header = prepare_markdown_header(config, "close")
    write_template("Close")

    return {
        "QC": f"{config['basename']}_QC.qmd" if config["basename"] != "" else "QC.qmd",
        "Delivery": f"{config['basename']}_Delivery.qmd"
        if config["basename"] != ""
        else "Delivery.qmd",
        "Close": f"{config['basename']}_Close.qmd"
        if config["basename"] != ""
        else "Close.qmd",
    }


def generate_markdown_output(config: dict, cmd: str, label: str):
    """Generate the markdown output using Quarto."""
    logging.debug("Generating markdown via Quarto...")
    try:
        _ = subprocess.run(cmd, shell=True, check=True, capture_output=True)
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
        logging.error(f"Error generating markdown: {e}")
        exit(1)


def generate_html_output(config: dict, cmd: str):
    """Generate the HTML output using Quarto."""
    logging.debug("Generating HTML via Quarto...")
    try:
        _ = subprocess.run(cmd, shell=True, check=True, capture_output=True)
        logging.debug("HTML file generated successfully.")
    except subprocess.CalledProcessError as e:
        logging.warning(f"Error generating HTML: {e}")
        exit(1)


def cleanup_temporary_data(config: dict):
    """Remove temporary files and directories created during the process."""
    files_list = list(
        pathlib.Path(__file__).resolve().parent.glob(f"{config['basename']}*.qmd")
    )
    # Move qmd files to the quarto directory
    for qmd in files_list:
        if qmd.is_file():
            qmd.rename(config["qmds_path"].joinpath(qmd.name))

    # Remove the md files
    files_list = list(pathlib.Path().glob(f"**/{config['basename']}*.md"))
    files_list = [x for x in files_list if not re.match("README.md", x.name)]
    for tmp_md in files_list:
        if tmp_md.is_file():
            logging.debug(f"Removing temporary file: {tmp_md}")
            tmp_md.unlink()

    # Remove the html files
    paths_list = list(pathlib.Path().glob(f"**/{config['basename']}_*_files"))
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

    # Set the logging level based on the command-line argument
    logging.getLogger().setLevel(args.log_level)

    # Set the run parameters according to the command-line arguments and config file
    config = set_run_parameters(args)

    # Validate the project ID
    if config["project"]:
        validate_project_id(config["project"])

    # Validate the flowcell ID
    if config["flowcell"]:
        validate_flowcell_id(config["flowcell"])

    # Check if the Quarto executable exists and is accessible
    config["quarto_path"], quarto_version = validate_quarto_path(config["quarto_path"])

    # Check if the template file exists
    validate_templates(config["templates_path"])

    # Create the output directory if it doesn't exist
    config["output_path"].mkdir(parents=True, exist_ok=True)

    # Set the path for the Quarto markdown files, and create the directory if it doesn't exist
    config["qmds_path"] = pathlib.Path(__file__).resolve().parent.joinpath("qmds")
    config["qmds_path"].mkdir(parents=True, exist_ok=True)

    # Check if the output directory exists
    if not args.force:
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
                    "Delivery.html",
                    "Delivery.md",
                    "Close.html",
                    "Close.md",
                ]
                if config["output_path"].joinpath(x).is_file()
            ]
        if files_list:
            logging.error(
                "The following files already exist and will not be overwritten:"
            )
            for file in files_list:
                logging.error(f"    '{file}'")
            logging.error(
                "Use --force to overwrite existing files or specify a different output directory."
            )
            exit(1)

    # Summarise the run parameters
    logging.debug("-" * 40)
    logging.debug("Run Parameters:")
    logging.debug(f"    Quarto Path: {config['quarto_path']}")
    logging.debug(f"    Quarto Version: {quarto_version}")
    logging.debug(f"    Templates Path: {config['templates_path']}")
    logging.debug(f"    Project ID: {config['project']}")
    logging.debug(f"    Flowcell ID: {config['flowcell']}")
    logging.debug(f"    NGI Path: {config['ngi_path']}")
    logging.debug(f"    Author: {config['author']}")
    logging.debug(f"    Author Email: {config['email']}")
    logging.debug(f"    Output Directory: {config['output_path']}")
    logging.debug(f"    Output Format: {config['format']}")
    logging.debug(f"    Output Structure: {config['output_structure']}")
    logging.debug(f"    Timestamp: {args.timestamp}")
    if config["format"] == "markdown":
        logging.debug(f"    Markdown Output Path: {config['output_path']}")
        logging.debug(f"    Markdown Filename: {config['basename']}.md")
    else:
        logging.debug(f"    HTML Output Path: {config['output_path']}")
        logging.debug(f"    HTML Filename: {config['basename']}.html")
    logging.debug("-" * 40)

    # Write the markdown template, including the dynamic content
    templates_dict = parse_markdown_templates(config)

    for key, template in templates_dict.items():
        logging.debug(f"Generating {key} output using template: {template}")
        # Prepare the base command to run Quarto
        cmd = f"{config['quarto_path']} render {template} --no-clean"
        cmd += f" --output-dir {config['output_path']} --execute-dir {config['output_path']}"
        if config["format"] == "markdown":
            cmd += " --to commonmark"
            cmd += (
                f" --output {config['basename']}_{key}.md"
                if config["basename"] != ""
                else f" --output {key}.md"
            )
            # Generate the Markdown file and place it in the specified directory
            generate_markdown_output(config, cmd, key)

        elif config["format"] == "html":
            cmd += " --to html --embed-resources --standalone --debug "
            cmd += (
                f"--output {config['basename']}_{key}.html"
                if config["basename"] != ""
                else f" --output {key}.html"
            )
            # Generate the HTML file and place it in the specified directory
            generate_html_output(config, cmd)
        else:
            logging.error("Invalid format specified. Use 'markdown' or 'html'.")
            exit(1)

    logging.info("All output files generated successfully.")
    logging.debug("-" * 40)

    logging.debug("Cleaning up temporary files and folders...")
    cleanup_temporary_data(config)

    logging.debug("-" * 40)
