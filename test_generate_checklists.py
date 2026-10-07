import pathlib
import unittest

import yaml
from generate_checklists import (
    CHECKBOX_PRINT_ASSET,
    prepare_markdown_header,
    validate_flowcell_id,
    validate_project_id,
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


class TestPrepareMarkdownHeader(unittest.TestCase):
    """Test prepare_markdown_header function."""

    def setUp(self):
        """Set up a minimal run configuration."""
        self.assets_path = pathlib.Path(__file__).resolve().parent.joinpath("assets")
        self.config = {
            "project": "P1234",
            "name": "A.Project_26_01",
            "author": "Jane Doe",
            "email": "jane.doe@scilifelab.se",
            "script_assets_path": self.assets_path,
        }

    def load_header(self, template: str) -> dict:
        """Load the generated header (a delimited YAML document) as a dict."""
        return next(yaml.safe_load_all(prepare_markdown_header(self.config, template)))

    def test_html_header_includes_checkbox_print_asset(self):
        """Test that the HTML header includes the checkbox print asset."""
        header = self.load_header("qc")
        expected = str(self.assets_path.joinpath(CHECKBOX_PRINT_ASSET).resolve())
        self.assertEqual(header["format"]["html"]["include-in-header"], expected)
        self.assertTrue(pathlib.Path(expected).is_file())

    def test_commonmark_header_has_no_html_includes(self):
        """Test that the markdown header is not affected by the HTML include."""
        header = self.load_header("qc")
        self.assertNotIn("include-in-header", header["format"]["commonmark"])

    def test_missing_asset_skips_include(self):
        """Test that a missing asset results in no include in the HTML header."""
        self.config["script_assets_path"] = pathlib.Path("/nonexistent/assets")
        header = self.load_header("delivery")
        self.assertNotIn("include-in-header", header["format"]["html"])

    def test_no_assets_path_skips_include(self):
        """Test that a config without an assets path skips the include."""
        del self.config["script_assets_path"]
        header = self.load_header("close")
        self.assertNotIn("include-in-header", header["format"]["html"])
