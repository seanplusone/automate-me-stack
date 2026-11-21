def accept(report):
    """Accept a report only when every case passed."""
    if report.get("passed") is True:
        return True
    cases = report.get("cases") or []
    if not cases:
        return False
    return all(item.get("ok") is True for item in cases)
