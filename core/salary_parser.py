"""Intelligent salary and package extraction and normalization engine.
Handles:
- Indian CTC packages in LPA (Lacs Per Annum): e.g. "₹14 - ₹22 LPA"
- Monthly stipends / salaries: e.g. "₹45,000 / mo"
- Global / US / EU annual salaries: e.g. "$120k - $160k / yr"
- Hourly rates: e.g. "$60 - $85 / hr"
"""
import re
from typing import Optional, Any, Dict


def extract_salary_from_text(text: str) -> Optional[str]:
    """Scans text (e.g. title, snippet, description) for salary and compensation patterns."""
    if not text:
        return None

    # 1. Look for LPA / Lacs / Lakhs patterns (e.g., 10-18 LPA, 8 to 15 Lacs, 12 LPA, 20-30 Lakhs PA)
    lpa_match = re.search(
        r'(?:₹|INR|Rs\.?|INR\s*)?\s*(\d+(?:\.\d+)?)\s*(?:-|to|–)\s*(\d+(?:\.\d+)?)\s*(?:lpa|lacs|lakhs?|lac)\b',
        text,
        re.IGNORECASE
    )
    if lpa_match:
        min_v, max_v = lpa_match.group(1), lpa_match.group(2)
        return f"₹{min_v} - ₹{max_v} LPA"

    single_lpa = re.search(
        r'(?:₹|INR|Rs\.?|INR\s*)?\s*(\d+(?:\.\d+)?)\s*(?:lpa|lacs?|lakhs?)\b',
        text,
        re.IGNORECASE
    )
    if single_lpa:
        val = single_lpa.group(1)
        if float(val) <= 150:  # Avoid matching large numbers incorrectly
            return f"₹{val} LPA"

    # 2. Look for monthly stipends/salaries (e.g. ₹25,000/month, 30k/month, Rs 40000 pm, ₹35,000 / mo)
    monthly_match = re.search(
        r'(?:₹|INR|Rs\.?)\s*(\d{1,2}(?:,\d{3})+|\d{4,6}|\d{2,3}k)(?:\s*(?:-|to)\s*(?:₹|INR|Rs\.?)?\s*(\d{1,2}(?:,\d{3})+|\d{4,6}|\d{2,3}k))?\s*(?:/|\s*per\s*)?\s*(?:month|mo|pm)\b',
        text,
        re.IGNORECASE
    )
    if monthly_match:
        val1 = monthly_match.group(1)
        val2 = monthly_match.group(2)
        if val2:
            return f"₹{val1} - ₹{val2} / month"
        return f"₹{val1} / month"

    # 3. Look for USD/EUR/GBP annual ranges (e.g. $120k - $160k, $120,000 - $150,000, £60k - £80k)
    annual_usd_range = re.search(
        r'([$€£])\s*(\d{2,3}(?:,\d{3})*|\d{2,3}k)\s*(?:-|to|–)\s*([$€£])?\s*(\d{2,3}(?:,\d{3})*|\d{2,3}k)(?:\s*(?:/|\s*per\s*|\s*)(?:year|yr|annum))?',
        text,
        re.IGNORECASE
    )
    if annual_usd_range:
        curr = annual_usd_range.group(1)
        min_v = annual_usd_range.group(2).replace(',', '')
        max_v = annual_usd_range.group(4).replace(',', '')
        if not min_v.endswith('k') and int(min_v) >= 1000:
            min_v = f"{int(min_v)//1000}k"
        if not max_v.endswith('k') and int(max_v) >= 1000:
            max_v = f"{int(max_v)//1000}k"
        return f"{curr}{min_v} - {curr}{max_v} / yr"

    # 4. Hourly rate (e.g. $50 - $80 / hr)
    hourly_match = re.search(
        r'([$€£])\s*(\d{2,3})\s*(?:-|to|–)\s*([$€£])?\s*(\d{2,3})\s*(?:/|\s*per\s*)(?:hr|hour)\b',
        text,
        re.IGNORECASE
    )
    if hourly_match:
        curr = hourly_match.group(1)
        return f"{curr}{hourly_match.group(2)} - {curr}{hourly_match.group(4)} / hr"

    return None


def normalize_salary(
    explicit_val: Optional[Any] = None,
    min_sal: Optional[Any] = None,
    max_sal: Optional[Any] = None,
    currency: Optional[str] = None,
    period: Optional[str] = None,
    fallback_text: Optional[str] = None,
    default_role_fallback: Optional[str] = None
) -> Optional[str]:
    """
    Normalizes diverse salary inputs into a clean, human-readable package string.
    Examples:
      - '₹16 - ₹24 LPA'
      - '$140k - $180k / yr'
      - '₹45,000 / month'
    """
    # 1. If explicit value passed
    if explicit_val and isinstance(explicit_val, str) and explicit_val.strip():
        s = explicit_val.strip()
        # If already formatted cleanly, return it
        if any(unit in s.lower() for unit in ['lpa', 'lacs', 'lakh', '/ yr', '/yr', '/ mo', '/mo', '/hr', '$', '₹', '€', '£']):
            return s
        parsed = extract_salary_from_text(s)
        if parsed:
            return parsed

    # 2. Check min_sal and max_sal numeric values
    if min_sal is not None or max_sal is not None:
        try:
            min_num = float(min_sal) if min_sal else None
            max_num = float(max_sal) if max_sal else None

            # Detect Indian LPA vs USD thousands
            curr_sym = "₹" if currency and "inr" in currency.lower() else "$"
            if currency and "eur" in currency.lower():
                curr_sym = "€"
            elif currency and "gbp" in currency.lower():
                curr_sym = "£"

            # Check if numbers are already in Lakhs (e.g. 10 to 20)
            if (min_num and min_num <= 100) or (max_num and max_num <= 100):
                if curr_sym == "₹":
                    if min_num and max_num:
                        return f"₹{int(min_num) if min_num.is_integer() else min_num} - ₹{int(max_num) if max_num.is_integer() else max_num} LPA"
                    elif min_num:
                        return f"₹{min_num} LPA"

            # Typical annual USD ($60,000 - $180,000)
            if (min_num and min_num >= 1000) or (max_num and max_num >= 1000):
                min_k = f"{int(min_num // 1000)}k" if min_num else None
                max_k = f"{int(max_num // 1000)}k" if max_num else None
                if min_k and max_k:
                    return f"{curr_sym}{min_k} - {curr_sym}{max_k} / yr"
                elif min_k:
                    return f"{curr_sym}{min_k}+ / yr"
                elif max_k:
                    return f"Up to {curr_sym}{max_k} / yr"
        except (ValueError, TypeError):
            pass

    # 3. Fallback: Scan text
    if fallback_text:
        parsed = extract_salary_from_text(fallback_text)
        if parsed:
            return parsed

    # 4. Optional role fallback if requested
    if default_role_fallback:
        role_lower = default_role_fallback.lower()
        if any(k in role_lower for k in ["intern", "trainee", "fellow"]):
            return "₹25,000 - ₹50,000 / mo"
        elif any(k in role_lower for k in ["senior", "lead", "staff", "principal", "architect"]):
            return "$140k - $210k / yr (₹30 - ₹50 LPA)"
        else:
            return "$90k - $140k / yr (₹15 - ₹25 LPA)"

    return None
