"""Allowlisted Codex telemetry, consumed only inside the existing bounded log reader.
No account credentials, messages, reasoning, billing inference or external calls.
"""
import math


def number(value):
    return value if type(value) in (int, float) and math.isfinite(value) and value >= 0 else None


def snapshot(payload, stamp):
    info = payload.get('info') if isinstance(payload.get('info'), dict) else {}
    last = info.get('last_token_usage') if isinstance(info.get('last_token_usage'), dict) else {}
    total = info.get('total_token_usage') if isinstance(info.get('total_token_usage'), dict) else {}
    limits = payload.get('rate_limits') if isinstance(payload.get('rate_limits'), dict) else {}
    windows = []
    for key in ('primary', 'secondary'):
        window = limits.get(key)
        if not isinstance(window, dict):
            continue
        used = number(window.get('used_percent'))
        windows.append({'kind': key, 'usedPercent': used if used is not None and used <= 100 else None,
                        'minutes': number(window.get('window_minutes')), 'resetsAt': number(window.get('resets_at'))})
    return {'provider': 'codex', 'observedAt': stamp, 'contextWindow': number(info.get('model_context_window')),
            'lastTokens': number(last.get('total_tokens')), 'totalTokens': number(total.get('total_tokens')),
            'cachedInputTokens': number(last.get('cached_input_tokens')), 'windows': windows,
            'cost': None, 'source': 'Local Codex token_count event; account identity unverified'}
