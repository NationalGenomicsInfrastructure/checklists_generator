import unittest
import os
import pathlib
import tempfile
from generate_checklists import (
    validate_project_id,
    validate_flowcell_id,
    validate_templates,
    parse_markdown_templates,
)


class TestValidateProjectId(unittest.TestCase):
    """Test validate_project_id function."""

    def test_happy_path(self):
        """Test that the function executes correctly with valid project ID format."""
        self.assertIsNone(validate_project_id("P1234"))
        self.assertIsNone(validate_project_id("P12345"))

    def test_exceptions(self):
        """Test that the function raises a ValueError when given an invalid project ID format."""
        self.assertRaises(ValueError, validate_project_id, "P123")
        self.assertRaises(ValueError, validate_project_id, "P123A")
        self.assertRaises(ValueError, validate_project_id, "P123456")


class TestValidateFlowcellId(unittest.TestCase):
    """Test validate_flowcell_id function."""

    def test_happy_path(self):
        """Test that the function executes correctly with valid flowcell ID format."""
        self.assertIsNone(validate_flowcell_id("123456_A01234_0001_ABCDEFGHIJ-ACBSH"))
        self.assertIsNone(validate_flowcell_id("12345678_BC12345_001_ABCDEFG123-ABC12"))

    def test_exceptions(self):
        """Test that the function raises a ValueError when given an invalid flowcell ID format."""
        self.assertRaises(
            ValueError, validate_flowcell_id, "123456789_A01_00001_ABCDEFGHIJKL"
        )
        self.assertRaises(
            ValueError, validate_flowcell_id, "123456_A01_00001_ABCDEFGHIJKL-ABCD"
        )


def _make_templates(base: pathlib.Path, delivery_type: str = "standard") -> None:
    """Create the minimal template tree required by validate_templates and parse_markdown_templates."""
    partials = base / "partials"
    partials.mkdir(parents=True, exist_ok=True)
    (base / "QC_template.qmd").write_text("<qc_type_section>\n")
    (partials / "qc_standard.qmd").write_text("standard qc section\n")
    (partials / "qc_runfolder.qmd").write_text("runfolder qc section\n")
    (base / "Delivery_standard_template.qmd").write_text("standard delivery content\n")
    (base / "Delivery_runfolder_template.qmd").write_text("runfolder delivery content\n")
    (base / "Close_template.qmd").write_text("close content\n")


def _make_config(templates_path: pathlib.Path, delivery_type: str = "standard") -> dict:
    """Return a minimal config dict for parse_markdown_templates."""
    return {
        "basename": "",
        "templates_path": templates_path,
        "delivery_type": delivery_type,
        "best_practice": None,
        "project": None,
        "name": None,
        "flowcell": None,
        "slide": None,
        "genome_path": None,
        "transcriptome_path": None,
        "author": None,
        "signature": None,
        "email": None,
        "ngi_path": None,
        "visium_base_path": None,
        "local_reports_path": None,
        "instrument": "illumina",
        "genstat_url": None,
        "charon_url": None,
        "script_assets_path": None,
        "config_path": None,
        "runfolder_path": None,
    }


class TestValidateTemplates(unittest.TestCase):
    """Test validate_templates function."""

    def test_standard_passes(self):
        """All required files present for standard delivery should not raise."""
        with tempfile.TemporaryDirectory() as tmp:
            tpl = pathlib.Path(tmp)
            _make_templates(tpl, "standard")
            validate_templates(tpl, delivery_type="standard")  # should not exit

    def test_runfolder_passes(self):
        """All required files present for runfolder delivery should not raise."""
        with tempfile.TemporaryDirectory() as tmp:
            tpl = pathlib.Path(tmp)
            _make_templates(tpl, "runfolder")
            validate_templates(tpl, delivery_type="runfolder")  # should not exit

    def test_missing_delivery_template_exits(self):
        """Missing Delivery_<type>_template.qmd should cause SystemExit."""
        with tempfile.TemporaryDirectory() as tmp:
            tpl = pathlib.Path(tmp)
            _make_templates(tpl, "standard")
            (tpl / "Delivery_standard_template.qmd").unlink()
            with self.assertRaises(SystemExit):
                validate_templates(tpl, delivery_type="standard")

    def test_missing_qc_partial_exits(self):
        """Missing partials/qc_<type>.qmd should cause SystemExit."""
        with tempfile.TemporaryDirectory() as tmp:
            tpl = pathlib.Path(tmp)
            _make_templates(tpl, "standard")
            (tpl / "partials" / "qc_standard.qmd").unlink()
            with self.assertRaises(SystemExit):
                validate_templates(tpl, delivery_type="standard")

    def test_missing_templates_dir_exits(self):
        """Non-existent templates directory should cause SystemExit."""
        with self.assertRaises(SystemExit):
            validate_templates(pathlib.Path("/nonexistent/path"))


class TestParseMarkdownTemplates(unittest.TestCase):
    """Test parse_markdown_templates function."""

    def setUp(self):
        self._original_cwd = os.getcwd()
        self._tmp = tempfile.TemporaryDirectory()
        os.chdir(self._tmp.name)

    def tearDown(self):
        os.chdir(self._original_cwd)
        self._tmp.cleanup()

    def _read_qmd(self, name: str) -> str:
        return pathlib.Path(name).read_text()

    def test_standard_qc_partial_injected(self):
        """QC output should contain standard partial content, not the placeholder."""
        with tempfile.TemporaryDirectory() as tmp:
            tpl = pathlib.Path(tmp)
            _make_templates(tpl)
            config = _make_config(tpl, delivery_type="standard")
            parse_markdown_templates(config)
            qc_content = self._read_qmd("QC.qmd")
            self.assertIn("standard qc section", qc_content)
            self.assertNotIn("<qc_type_section>", qc_content)

    def test_runfolder_qc_partial_injected(self):
        """QC output should contain runfolder partial content for runfolder delivery."""
        with tempfile.TemporaryDirectory() as tmp:
            tpl = pathlib.Path(tmp)
            _make_templates(tpl)
            config = _make_config(tpl, delivery_type="runfolder")
            parse_markdown_templates(config)
            qc_content = self._read_qmd("QC.qmd")
            self.assertIn("runfolder qc section", qc_content)
            self.assertNotIn("standard qc section", qc_content)

    def test_standard_delivery_template_used(self):
        """Delivery output should use Delivery_standard_template.qmd for standard."""
        with tempfile.TemporaryDirectory() as tmp:
            tpl = pathlib.Path(tmp)
            _make_templates(tpl)
            config = _make_config(tpl, delivery_type="standard")
            parse_markdown_templates(config)
            delivery_content = self._read_qmd("Delivery.qmd")
            self.assertIn("standard delivery content", delivery_content)
            self.assertNotIn("runfolder delivery content", delivery_content)

    def test_runfolder_delivery_template_used(self):
        """Delivery output should use Delivery_runfolder_template.qmd for runfolder."""
        with tempfile.TemporaryDirectory() as tmp:
            tpl = pathlib.Path(tmp)
            _make_templates(tpl)
            config = _make_config(tpl, delivery_type="runfolder")
            parse_markdown_templates(config)
            delivery_content = self._read_qmd("Delivery.qmd")
            self.assertIn("runfolder delivery content", delivery_content)
            self.assertNotIn("standard delivery content", delivery_content)

    def test_runfolder_path_substituted(self):
        """<runfolder_path> placeholder should be replaced when runfolder_path is set."""
        with tempfile.TemporaryDirectory() as tmp:
            tpl = pathlib.Path(tmp)
            (tpl / "partials").mkdir()
            (tpl / "QC_template.qmd").write_text("<qc_type_section>\n")
            (tpl / "partials" / "qc_runfolder.qmd").write_text(
                "taca transfer <runfolder_path> done\n"
            )
            (tpl / "partials" / "qc_standard.qmd").write_text("")
            (tpl / "Delivery_runfolder_template.qmd").write_text("")
            (tpl / "Delivery_standard_template.qmd").write_text("")
            (tpl / "Close_template.qmd").write_text("")
            config = _make_config(tpl, delivery_type="runfolder")
            config["runfolder_path"] = pathlib.Path("/data/ngi/runfolders/240101_A01234")
            parse_markdown_templates(config)
            qc_content = self._read_qmd("QC.qmd")
            self.assertIn("/data/ngi/runfolders/240101_A01234", qc_content)
            self.assertNotIn("<runfolder_path>", qc_content)

    def test_runfolder_path_not_substituted_when_absent(self):
        """<runfolder_path> placeholder should remain when runfolder_path is not set."""
        with tempfile.TemporaryDirectory() as tmp:
            tpl = pathlib.Path(tmp)
            (tpl / "partials").mkdir()
            (tpl / "QC_template.qmd").write_text("<qc_type_section>\n")
            (tpl / "partials" / "qc_runfolder.qmd").write_text(
                "taca transfer <runfolder_path> done\n"
            )
            (tpl / "partials" / "qc_standard.qmd").write_text("")
            (tpl / "Delivery_runfolder_template.qmd").write_text("")
            (tpl / "Delivery_standard_template.qmd").write_text("")
            (tpl / "Close_template.qmd").write_text("")
            config = _make_config(tpl, delivery_type="runfolder")
            parse_markdown_templates(config)
            qc_content = self._read_qmd("QC.qmd")
            self.assertIn("<runfolder_path>", qc_content)

