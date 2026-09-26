"""CLI tool to verify official government source URLs independently of Qdrant or RAG.

Usage:
    python scripts/check_source_urls.py
"""

import sys
from pathlib import Path

# Add project root to sys.path so app modules are resolvable
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from app.services.url_service import URLService


def main():
    print("=" * 75)
    print("IP-SAKTI Sahayak: Authoritative Source URL Audit")
    print("=" * 75)

    urls_to_check = [
        ("Patents (IPO / CGPDTM)", URLService.OFFICIAL_URL_PATENT),
        ("Trade Marks (CGPDTM)", URLService.OFFICIAL_URL_TRADEMARK),
        ("Biodiversity (NBA)", URLService.OFFICIAL_URL_BIODIVERSITY),
        ("Ayurveda Aahar (FSSAI)", URLService.OFFICIAL_URL_AYURVEDA_AAHAR),
        ("Drugs / ASU (CDSCO)", URLService.OFFICIAL_URL_DRUGS_ASU),
    ]

    all_passed = True
    print(f"\n{'Domain/Topic':<25} | {'Status':<6} | {'Verified':<8} | {'Official Domain':<15} | URL")
    print("-" * 75)

    for label, url in urls_to_check:
        res = URLService.check_url_live(url, timeout=7.0)
        status_str = str(res["status_code"]) if res["status_code"] > 0 else "ERR"
        verified_str = "YES" if res["is_verified"] else "NO"
        official_str = "YES" if res["is_official_domain"] else "NO"

        print(f"{label:<25} | {status_str:<6} | {verified_str:<8} | {official_str:<15} | {url}")

        if res["status_code"] != 200 or not res["is_verified"]:
            all_passed = False
            if res.get("error"):
                print(f"   -> Warning/Error: {res['error']}")

    print("\n" + "=" * 75)
    if all_passed:
        print("ALL 5 STATUTORY SOURCE URLS ARE VERIFIED, OFFICIAL, AND OPERATIONAL (HTTP 200).")
        print("=" * 75)
        sys.exit(0)
    else:
        print("SOME URLS ENCOUNTERED ERRORS OR FAILED VERIFICATION.")
        print("=" * 75)
        sys.exit(1)


if __name__ == "__main__":
    main()
