"""Deterministic classifier; this is not a live language-model adapter."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Classification:
    category: str
    priority: str
    reason: str
    mode: str = 'rules'


def classify(subject: str, message: str) -> Classification:
    text = f'{subject} {message}'.casefold()
    terms = {
        'billing': ('invoice', 'refund', 'payment', 'فاتورة', 'سداد', 'دفع'),
        'support': ('broken', 'error', 'issue', 'bug', 'help', 'خطأ', 'مشكلة'),
        'sales': ('quote', 'pricing', 'buy', 'purchase', 'price', 'سعر', 'شراء'),
    }
    category = next((name for name, words in terms.items()
                     if any(word in text for word in words)), 'other')
    priority = 'high' if any(word in text for word in ('urgent', 'asap', 'critical', 'عاجل')) else 'normal'
    return Classification(category, priority,
                          'Matched deterministic rule' if category != 'other' else 'No rule matched')
