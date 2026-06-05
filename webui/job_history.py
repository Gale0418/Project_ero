INTERRUPTED_STATUSES = {"Pending", "Running", "Canceling"}
RESTART_ERROR = "Server restarted before completion"


def normalize_loaded_job(job_data):
    normalized = dict(job_data)
    if normalized.get("status") not in INTERRUPTED_STATUSES:
        return normalized, False

    normalized["status"] = "Failed"
    normalized["error"] = RESTART_ERROR
    normalized["phase_text"] = ""
    return normalized, True
