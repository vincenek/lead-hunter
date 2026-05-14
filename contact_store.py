import json
from datetime import datetime, timezone
from pathlib import Path


STORE_PATH = Path(__file__).with_name('contacted_leads.json')


def _read_store():
    if not STORE_PATH.exists():
        return {}

    try:
        data = json.loads(STORE_PATH.read_text(encoding='utf-8'))
    except (json.JSONDecodeError, OSError):
        return {}

    return data if isinstance(data, dict) else {}


def list_contacted():
    return _read_store()


def save_contacted(data):
    STORE_PATH.write_text(json.dumps(data, indent=2, sort_keys=True), encoding='utf-8')


def mark_contacted(lead):
    data = _read_store()
    lead_id = lead['lead_id']
    data[lead_id] = {
        'lead_id': lead_id,
        'name': lead.get('name'),
        'city': lead.get('city'),
        'country': lead.get('country'),
        'phone': lead.get('phone'),
        'email': lead.get('email'),
        'address': lead.get('address'),
        'website': lead.get('website'),
        'profile_link': lead.get('profile_link'),
        'contacted_at': datetime.now(timezone.utc).isoformat(),
    }
    save_contacted(data)
    return data[lead_id]


def unmark_contacted(lead_id):
    data = _read_store()
    removed = data.pop(lead_id, None)
    save_contacted(data)
    return removed
