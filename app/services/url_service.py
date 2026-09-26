"""URL Validation and Sanitization Service for authoritative government sources.

Maintains verified official government endpoints, validates source URLs,
and sanitizes chatbot-generated text to ensure no unverified or fabricated URLs reach the user.
"""

import re
import urllib.parse
from typing import Dict, List, Optional, Set


class URLService:
    """Lightweight, standalone URL verification and sanitization service.

    Has zero external dependencies so scripts and CLI tools can run independently.
    """

    # Official verified statutory URLs
    OFFICIAL_URL_PATENT = "https://ipindia.gov.in/resource/patents-resources-act"
    OFFICIAL_URL_TRADEMARK = "https://ipindia.gov.in/trade-marks-resources-act"
    OFFICIAL_URL_BIODIVERSITY = "https://nbaindia.nic.in/acts-and-rules/acts"
    OFFICIAL_URL_AYURVEDA_AAHAR = (
        "https://fssai.gov.in/upload/notifications/2022/05/627a4198112d8Gazette_Notification_Ayurveda_Aahar_06_05_2022.pdf"
    )
    OFFICIAL_URL_DRUGS_ASU = "https://cdsco.gov.in/opencms/opencms/en/Acts-Rules"

    VERIFIED_OFFICIAL_URLS: Dict[str, str] = {
        "Patent": OFFICIAL_URL_PATENT,
        "Trademark": OFFICIAL_URL_TRADEMARK,
        "Biological_Resources": OFFICIAL_URL_BIODIVERSITY,
        "Ayurveda_Aahar": OFFICIAL_URL_AYURVEDA_AAHAR,
        "Classical_Medicine": OFFICIAL_URL_DRUGS_ASU,
        "Drug_Ayush": OFFICIAL_URL_DRUGS_ASU,
    }

    # Set of canonical verified URLs for fast exact lookup
    ALL_VERIFIED_URLS_SET: Set[str] = {
        OFFICIAL_URL_PATENT,
        OFFICIAL_URL_TRADEMARK,
        OFFICIAL_URL_BIODIVERSITY,
        OFFICIAL_URL_AYURVEDA_AAHAR,
        OFFICIAL_URL_DRUGS_ASU,
        "https://cdsco.gov.in/opencms/opencms/en/Acts-and-rules/",
        "https://ayush.gov.in/",
    }

    # Legitimate official government domains
    OFFICIAL_GOVERNMENT_DOMAINS: Set[str] = {
        "ipindia.gov.in",
        "nbaindia.nic.in",
        "fssai.gov.in",
        "cdsco.gov.in",
        "ayush.gov.in",
    }

    # Known broken / obsolete domains that must be rejected
    REJECTED_OBSOLETE_DOMAINS: Set[str] = {
        "nbaindia.org",
    }

    @classmethod
    def normalize_url(cls, url: str) -> str:
        """Normalizes URL for consistent comparison (stripping trailing slashes and whitespace)."""
        if not url:
            return ""
        u = url.strip()
        if u.endswith("/") and len(u) > 10 and not u.endswith("://"):
            u = u[:-1]
        return u

    @classmethod
    def get_domain(cls, url: str) -> str:
        """Extracts the lowercased domain hostname from a URL."""
        try:
            parsed = urllib.parse.urlparse(url.strip())
            return parsed.netloc.lower()
        except Exception:
            return ""

    @classmethod
    def is_official_domain(cls, url: str) -> bool:
        """Checks if a URL belongs to a legitimate official government domain."""
        domain = cls.get_domain(url)
        if any(bad in domain for bad in cls.REJECTED_OBSOLETE_DOMAINS):
            return False
        return any(domain == d or domain.endswith("." + d) for d in cls.OFFICIAL_GOVERNMENT_DOMAINS)

    @classmethod
    def is_url_verified(cls, url: str) -> bool:
        """Checks if the URL is an explicitly verified, approved authoritative source URL.

        Does NOT blindly accept any URL on a government domain; it must be in the
        verified registry or match an explicitly approved statutory endpoint.
        """
        if not url:
            return False

        norm = cls.normalize_url(url)
        domain = cls.get_domain(url)

        # Reject obsolete domains immediately
        if any(bad in domain for bad in cls.REJECTED_OBSOLETE_DOMAINS):
            return False

        # Check against canonical verified set
        for verified in cls.ALL_VERIFIED_URLS_SET:
            if cls.normalize_url(verified).lower() == norm.lower():
                return True

        return False

    @classmethod
    def validate_and_sanitize_answer_urls(
        cls, answer_text: str, allowed_urls: Optional[List[str]] = None
    ) -> str:
        """Scans answer text for URLs, verifies each against allowed and approved sets,

        and removes unverified, guessed, or obsolete URLs to prevent hallucination.
        Per Rule 3: Does NOT blindly replace arbitrary URLs with a default from the same domain.
        """
        if not answer_text:
            return ""

        allowed_normalized: Set[str] = set()
        if allowed_urls:
            for u in allowed_urls:
                if u and cls.is_url_verified(u):
                    allowed_normalized.add(cls.normalize_url(u).lower())

        # Also permit canonical verified URLs
        for v in cls.ALL_VERIFIED_URLS_SET:
            allowed_normalized.add(cls.normalize_url(v).lower())

        url_regex = re.compile(r"https?://[^\s)\]\"'>]+", re.IGNORECASE)

        def replace_match(match: re.Match) -> str:
            raw_url = match.group(0).rstrip(".,;:!?'\"")
            norm = cls.normalize_url(raw_url).lower()

            # If explicitly approved and verified, retain it
            if norm in allowed_normalized or cls.is_url_verified(raw_url):
                return raw_url

            # Otherwise, reject/remove unverified URL (do not guess or auto-substitute)
            return "[official government record]"

        sanitized = url_regex.sub(replace_match, answer_text)
        return sanitized

    @classmethod
    def check_url_live(cls, url: str, timeout: float = 6.0) -> Dict[str, object]:
        """Performs a live network verification of a URL, returning HTTP status, redirect, and domain info."""
        import ssl
        import urllib.request

        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        domain = cls.get_domain(url)
        is_verified = cls.is_url_verified(url)
        is_official = cls.is_official_domain(url)

        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) IP-SAKTI-Sahayak/1.0"},
            )
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as response:
                status_code = getattr(response, "status", 200)
                final_url = response.geturl()
                return {
                    "url": url,
                    "status_code": status_code,
                    "final_url": final_url,
                    "domain": domain,
                    "is_official_domain": is_official,
                    "is_verified": is_verified,
                    "error": None,
                }
        except Exception as exc:
            return {
                "url": url,
                "status_code": 0,
                "final_url": url,
                "domain": domain,
                "is_official_domain": is_official,
                "is_verified": is_verified,
                "error": str(exc),
            }
