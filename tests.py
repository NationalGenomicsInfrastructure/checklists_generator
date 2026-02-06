import unittest
from generate_checklists import validate_project_id, validate_flowcell_id


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
