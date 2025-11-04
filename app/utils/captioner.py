"""
VLM-based image captioning for traffic scene understanding
"""
from typing import Optional, Dict, Any, List
from app.config import settings


class ImageCaptioner:
    """
    Vision-Language Model based image captioner
    Extracts traffic-related features from images
    """

    def __init__(self, model_name: str = None):
        self.model_name = model_name or settings.VLM_MODEL
        self.enabled = settings.ENABLE_VLM

    def caption_image(self, image_base64: str) -> Optional[str]:
        """
        Generate caption for traffic scene image

        Args:
            image_base64: Base64 encoded image

        Returns:
            Caption text describing traffic scene
        """
        pass

    def extract_traffic_features(self, image_base64: str) -> Dict[str, Any]:
        """
        Extract structured traffic features from image

        Args:
            image_base64: Base64 encoded image

        Returns:
            Dictionary containing:
                - road_signs: List of detected signs
                - lane_markings: Detected lane markings
                - intersection_type: Type of intersection
                - violations: Potential violations detected
        """
        pass

    def detect_road_signs(self, image_base64: str) -> List[str]:
        """
        Detect road signs in image

        Args:
            image_base64: Base64 encoded image

        Returns:
            List of detected road signs
        """
        pass

    def detect_violations(self, image_base64: str) -> List[Dict[str, Any]]:
        """
        Detect potential traffic violations in image

        Args:
            image_base64: Base64 encoded image

        Returns:
            List of potential violations with confidence scores
        """
        pass

    def is_available(self) -> bool:
        """
        Check if VLM captioning is available

        Returns:
            True if VLM is enabled and configured
        """
        pass
