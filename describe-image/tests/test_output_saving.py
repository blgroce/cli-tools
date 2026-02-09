"""Tests for output saving functionality."""
import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from describe_image.main import app


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def test_image():
    """Create a minimal PNG for testing."""
    # 1x1 red pixel PNG
    png_bytes = (
        b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
        b'\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xcf\xc0'
        b'\x00\x00\x00\x03\x00\x01\x00\x05\xfe\xd4\xd3\x00\x00\x00\x00IEND\xaeB`\x82'
    )
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
        f.write(png_bytes)
        return Path(f.name)


@pytest.fixture
def mock_openrouter_response():
    """Mock successful OpenRouter API response."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": "This is a test description of the image."
                }
            }
        ]
    }
    return mock_resp


class TestOutputSaving:
    """Test --out/-o option functionality."""

    def test_out_option_saves_to_file(
        self, runner, test_image, mock_openrouter_response
    ):
        """Test that --out saves description to specified file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / "output.txt"

            with patch("describe_image.main.requests.post", return_value=mock_openrouter_response):
                with patch("describe_image.main.resolve_api_key", return_value="test-key"):
                    result = runner.invoke(
                        app,
                        ["describe", str(test_image), "--out", str(output_file)],
                    )

            assert result.exit_code == 0
            assert output_file.exists()
            assert output_file.read_text() == "This is a test description of the image."

            # Check JSON output includes saved_to
            data = json.loads(result.stdout)
            assert data["success"] is True
            assert "saved_to" in data["data"]
            assert data["data"]["saved_to"] == str(output_file.resolve())

    def test_out_option_creates_parent_dirs(
        self, runner, test_image, mock_openrouter_response
    ):
        """Test that --out creates parent directories if they don't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / "nested" / "dir" / "output.txt"

            with patch("describe_image.main.requests.post", return_value=mock_openrouter_response):
                with patch("describe_image.main.resolve_api_key", return_value="test-key"):
                    result = runner.invoke(
                        app,
                        ["describe", str(test_image), "--out", str(output_file)],
                    )

            assert result.exit_code == 0
            assert output_file.exists()
            assert output_file.read_text() == "This is a test description of the image."

    def test_out_option_with_directory_generates_filename(
        self, runner, test_image, mock_openrouter_response
    ):
        """Test that --out with directory auto-generates timestamped filename."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("describe_image.main.requests.post", return_value=mock_openrouter_response):
                with patch("describe_image.main.resolve_api_key", return_value="test-key"):
                    result = runner.invoke(
                        app,
                        ["describe", str(test_image), "--out", tmpdir],
                    )

            assert result.exit_code == 0

            # Find the generated file
            files = list(Path(tmpdir).glob("description-*.txt"))
            assert len(files) == 1
            assert files[0].read_text() == "This is a test description of the image."

            # Check JSON output includes saved_to
            data = json.loads(result.stdout)
            assert data["success"] is True
            assert "saved_to" in data["data"]
            assert "description-" in data["data"]["saved_to"]

    def test_without_out_option_no_saved_to(
        self, runner, test_image, mock_openrouter_response
    ):
        """Test that without --out, no saved_to in response."""
        with patch("describe_image.main.requests.post", return_value=mock_openrouter_response):
            with patch("describe_image.main.resolve_api_key", return_value="test-key"):
                result = runner.invoke(
                    app,
                    ["describe", str(test_image)],
                )

        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["success"] is True
        assert "saved_to" not in data["data"]
        assert "description" in data["data"]
