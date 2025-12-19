import json
import unittest
from unittest.mock import MagicMock, patch

from futurehealth.utils import parse_json_from_model, validate_nif
from futurehealth.utils.pdf import detect_file_type, extract_text_from_pdf, read_pdf, xconvert_from_path


class TestValidateNIF(unittest.TestCase):
    """Test cases for Portuguese NIF validation using mod11 algorithm."""

    def test_valid_nifs(self):
        """Test that valid NIFs pass validation."""
        valid_nifs = [
            '123456789',  # Valid personal NIF
            '505956985',  # Valid business NIF (starts with 5)
            ' 123 456 789 ',  # Valid with spaces (should be cleaned)
        ]

        for nif in valid_nifs:
            self.assertTrue(validate_nif(nif), f'NIF {nif} should be valid')

    def test_invalid_nifs(self):
        """Test that invalid NIFs fail validation."""
        invalid_nifs = [
            '123456780',  # Wrong check digit
            '999999999',  # Invalid check digit
            '12345678',  # Too short (8 digits)
            '1234567890',  # Too long (10 digits)
            '12345678a',  # Contains letter
            'abcdefgh',  # All letters
            '',  # Empty string
            '123.456.78',  # With dots, becomes 12345678 (too short)
        ]

        for nif in invalid_nifs:
            self.assertFalse(validate_nif(nif), f'NIF {nif} should be invalid')

    def test_edge_cases(self):
        """Test edge cases and boundary conditions."""
        # Test with various formatting
        self.assertTrue(validate_nif('123-456-789'))  # With dashes
        self.assertTrue(validate_nif('123 456 789'))  # With spaces
        self.assertTrue(validate_nif('123456789'))  # Clean

        # Test single digit variations
        self.assertFalse(validate_nif('123456788'))  # Wrong last digit
        self.assertFalse(validate_nif('023456789'))  # Leading zero (but valid)

    def test_algorithm_correctness(self):
        """Test specific cases to verify mod11 algorithm implementation."""
        # Test case: NIF 123456789
        # Digits: [1,2,3,4,5,6,7,8,9]
        # Weights: [9,8,7,6,5,4,3,2]
        # Sum: 1*9 + 2*8 + 3*7 + 4*6 + 5*5 + 6*4 + 7*3 + 8*2 = 156
        # 156 % 11 = 2, check_digit = 11 - 2 = 9
        # Last digit is 9, so valid
        self.assertTrue(validate_nif('123456789'))

        # Test case: NIF 505956985 (business NIF)
        # This should pass validation as it's a real example
        self.assertTrue(validate_nif('505956985'))

    def test_parametrized_nifs(self):
        """Parametrized test for various NIF validation cases."""
        test_cases = [
            ('123456789', True),
            ('505956985', True),
            ('123456780', False),
            ('999999999', False),
            ('12345678', False),
            ('1234567890', False),
            ('12345678a', False),
            (' 123 456 789 ', True),
        ]

        for nif, expected in test_cases:
            self.assertEqual(validate_nif(nif), expected)


class TestParseJsonFromModel(unittest.TestCase):
    """Test cases for parse_json_from_model function."""

    def test_valid_json(self):
        """Test parsing valid JSON."""
        json_str = '{"business_nif": "123456789", "total_amount": 100.50}'
        result = parse_json_from_model(json_str)
        self.assertEqual(result, {'business_nif': '123456789', 'total_amount': 100.50})

    def test_json_with_markdown_code_block(self):
        """Test parsing JSON wrapped in markdown code block."""
        json_str = '```json\n{"business_nif": "123456789", "total_amount": 100.50}\n```'
        result = parse_json_from_model(json_str)
        self.assertEqual(result, {'business_nif': '123456789', 'total_amount': 100.50})

    def test_invalid_json_raises_error(self):
        """Test that invalid JSON raises an error."""
        with self.assertRaises(json.JSONDecodeError):
            parse_json_from_model('{"invalid": json}')


class TestPDFUtils(unittest.TestCase):
    """Test cases for PDF utility functions."""

    def test_detect_file_type_pdf(self):
        """Test detecting PDF file type."""
        with patch('mimetypes.guess_type', return_value=('application/pdf', None)):
            self.assertEqual(detect_file_type('test.pdf'), 'application/pdf')

    def test_detect_file_type_png(self):
        """Test detecting PNG file type."""
        with patch('mimetypes.guess_type', return_value=('image/png', None)):
            self.assertEqual(detect_file_type('test.png'), 'image/png')

    @patch('pymupdf.open')
    def test_extract_text_from_pdf(self, mock_pymupdf):
        """Test text extraction from PDF."""
        mock_doc = MagicMock()
        mock_page = MagicMock()
        mock_page.get_text.return_value = 'Sample text from PDF'
        mock_doc.__iter__.return_value = [mock_page]
        mock_pymupdf.return_value = mock_doc

        result = extract_text_from_pdf('test.pdf')
        self.assertEqual(result, 'Sample text from PDF')
        mock_pymupdf.assert_called_once_with('test.pdf')

    @patch('futurehealth.utils.pdf.xconvert_from_path')
    @patch('futurehealth.utils.pdf.extract_text_from_pdf')
    def test_read_pdf_text_mode(self, mock_extract, mock_convert):
        """Test read_pdf in text mode (sufficient text)."""
        mock_extract.return_value = 'A' * 60  # More than min_chars (50)
        result = read_pdf('test.pdf', min_chars=50)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['type'], 'text')
        mock_convert.assert_not_called()

    @patch('futurehealth.utils.pdf.xconvert_from_path')
    @patch('futurehealth.utils.pdf.extract_text_from_pdf')
    def test_read_pdf_vision_mode(self, mock_extract, mock_convert):
        """Test read_pdf in vision mode (insufficient text)."""
        mock_extract.return_value = 'Short text'
        mock_image = MagicMock()
        mock_convert.return_value = [mock_image]  # Mock PIL image

        with patch('io.BytesIO') as mock_buf:
            mock_buf.return_value.getvalue.return_value = b'fake_png_data'
            result = read_pdf('test.pdf', min_chars=50, force_vision=False)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['type'], 'image_url')
        mock_convert.assert_called_once()
        mock_image.save.assert_called_once()

    def test_read_pdf_image_file(self):
        """Test read_pdf with image file."""
        with patch('futurehealth.utils.pdf.detect_file_type', return_value='image/png'):
            with patch('futurehealth.utils.pdf.image_file_to_base64', return_value='data:image/png;base64,fake'):
                result = read_pdf('test.png')
                self.assertEqual(len(result), 1)
                self.assertEqual(result[0]['type'], 'image_url')

    def test_read_pdf_unsupported_type(self):
        """Test read_pdf with unsupported file type."""
        with patch('futurehealth.utils.pdf.detect_file_type', return_value='text/plain'):
            with self.assertRaisesRegex(ValueError, 'Unsupported file type'):
                read_pdf('test.txt')

    @patch('pymupdf.open')
    def test_xconvert_from_path_resizing(self, mock_pymupdf):
        """Test that xconvert_from_path resizes large images."""
        # Mock a large image (2000x2000)
        mock_pix = MagicMock()
        mock_pix.width = 2000
        mock_pix.height = 2000
        mock_pix.samples = b'fake_samples'

        mock_page = MagicMock()
        mock_page.get_pixmap.return_value = mock_pix

        mock_doc = MagicMock()
        mock_doc.__iter__.return_value = [mock_page]
        mock_pymupdf.return_value = mock_doc

        with patch('PIL.Image.frombytes') as mock_frombytes:
            mock_img = MagicMock()
            mock_img.width = 2000
            mock_img.height = 2000
            mock_frombytes.return_value = mock_img

            result = xconvert_from_path('test.pdf')

            self.assertEqual(len(result), 1)
            # Check that thumbnail was called because width/height > 1024
            mock_img.thumbnail.assert_called_once()

    @patch('pymupdf.open')
    def test_xconvert_from_path_no_resizing(self, mock_pymupdf):
        """Test that xconvert_from_path doesn't resize small images."""
        # Mock a small image (800x600)
        mock_pix = MagicMock()
        mock_pix.width = 800
        mock_pix.height = 600
        mock_pix.samples = b'fake_samples'

        mock_page = MagicMock()
        mock_page.get_pixmap.return_value = mock_pix

        mock_doc = MagicMock()
        mock_doc.__iter__.return_value = [mock_page]
        mock_pymupdf.return_value = mock_doc

        with patch('PIL.Image.frombytes') as mock_frombytes:
            with patch('PIL.Image.Image.thumbnail') as mock_thumbnail:
                mock_img = MagicMock()
                mock_img.width = 800
                mock_img.height = 600
                mock_frombytes.return_value = mock_img

                result = xconvert_from_path('test.pdf')

                self.assertEqual(len(result), 1)
                mock_thumbnail.assert_not_called()
