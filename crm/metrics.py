from prometheus_client import Counter, Histogram

chat_processing_seconds = Histogram(
    "crm_chat_processing_seconds",
    "Time spent generating CRM email drafts",
)

chat_failures_total = Counter(
    "crm_chat_failures_total",
    "Number of failed CRM chat/email jobs",
    ["reason"],
)
