"""
Unit tests for image captioner
"""
import pytest
from app.utils.captioner import ImageCaptioner


class TestImageCaptioner:
    """Test cases for ImageCaptioner"""

    @pytest.fixture
    def captioner(self):
        """Create ImageCaptioner instance"""
        return ImageCaptioner()

    def test_caption_image(self, captioner):
        """Test image captioning"""
        image_base64 = "fake_base64_image"
        caption = captioner.caption_image(image_base64)
        assert caption is None  # placeholder

    def test_extract_traffic_features(self, captioner):
        """Test traffic feature extraction"""
        image_base64 = "fake_base64_image"
        features = captioner.extract_traffic_features(image_base64)
        assert features is None  # placeholder

    def test_detect_road_signs(self, captioner):
        """Test road sign detection"""
        image_base64 = "fake_base64_image"
        signs = captioner.detect_road_signs(image_base64)
        assert signs is None  # placeholder

    def test_detect_violations(self, captioner):
        """Test violation detection"""
        image_base64 = "fake_base64_image"
        violations = captioner.detect_violations(image_base64)
        assert violations is None  # placeholder

    def test_is_available(self, captioner):
        """Test VLM availability check"""
        available = captioner.is_available()
        assert available is None  # placeholder

    def test_caption_with_none_input(self, captioner):
        """Test captioning with None input"""
        caption = captioner.caption_image(None)
        assert caption is None  # placeholder

    def test_extract_features_with_invalid_image(self, captioner):
        """Test feature extraction with invalid image"""
        features = captioner.extract_traffic_features("invalid_base64")
        assert features is None  # placeholder
