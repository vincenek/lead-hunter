from flask import Flask, render_template, request, jsonify, Response
import csv
import io
import os
from scraper import search_region, REGIONS, BUSINESS_TYPES
from contact_store import list_contacted, mark_contacted, unmark_contacted

app = Flask(__name__)


def _coerce_max_cities(value, default=6):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(2, min(parsed, 8))


def _coerce_bool(value, default=False):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {'1', 'true', 'yes', 'on'}


@app.route('/')
def index():
    return render_template('index.html', business_types=BUSINESS_TYPES)


@app.route('/regions', methods=['GET'])
def regions():
    return jsonify(list(REGIONS.keys()))


@app.route('/categories', methods=['GET'])
def categories():
    return jsonify(list(BUSINESS_TYPES))


@app.route('/search', methods=['POST'])
def search():
    data = request.get_json(silent=True) or {}
    category = (data.get('category') or '').strip()
    region = (data.get('region') or 'Worldwide').strip()
    max_cities = _coerce_max_cities(data.get('max_cities', 3), default=3)
    actionable_only = _coerce_bool(data.get('actionable_only'), default=True)
    email_only = _coerce_bool(data.get('email_only'), default=False)
    hide_contacted = _coerce_bool(data.get('hide_contacted'), default=True)

    if not category:
        return jsonify({'error': 'Business type is required.'}), 400
    if region not in REGIONS:
        region = 'Worldwide'

    try:
        leads = search_region(category, region, max_cities)
    except Exception:
        return jsonify({'error': 'Lead search failed. Please try again in a moment.'}), 502

    if actionable_only:
        leads = [lead for lead in leads if lead.get('priority') == 'HOT']
    if email_only:
        leads = [lead for lead in leads if lead.get('email')]

    contacted_map = list_contacted()
    for lead in leads:
        lead['contacted'] = lead.get('lead_id') in contacted_map

    contacted_count = sum(1 for l in leads if l.get('contacted'))
    if hide_contacted:
        leads = [lead for lead in leads if not lead.get('contacted')]

    hot = sum(1 for l in leads if l['priority'] == 'HOT')
    warm = sum(1 for l in leads if l['priority'] == 'WARM')
    low = sum(1 for l in leads if l['priority'] == 'LOW')
    with_contact = sum(1 for l in leads if l.get('has_contact'))
    with_email = sum(1 for l in leads if l.get('email'))
    return jsonify({
        'leads': leads,
        'total': len(leads),
        'hot': hot,
        'warm': warm,
        'low': low,
        'with_contact': with_contact,
        'with_email': with_email,
        'contacted_count': contacted_count,
        'actionable_only': actionable_only,
        'email_only': email_only,
        'hide_contacted': hide_contacted,
    })


@app.route('/contacted', methods=['GET'])
def contacted():
    return jsonify({'leads': list(list_contacted().values())})


@app.route('/contacted', methods=['POST'])
def add_contacted():
    data = request.get_json(silent=True) or {}
    lead = data.get('lead') or {}
    lead_id = lead.get('lead_id')
    if not lead_id:
        return jsonify({'error': 'Lead ID is required.'}), 400

    stored = mark_contacted(lead)
    return jsonify({'ok': True, 'lead': stored})


@app.route('/contacted/<lead_id>', methods=['DELETE'])
def remove_contacted(lead_id):
    removed = unmark_contacted(lead_id)
    return jsonify({'ok': True, 'removed': bool(removed)})



@app.route('/export', methods=['POST'])
def export():
    data = request.get_json(silent=True) or {}
    leads = data.get('leads', [])

    output = io.StringIO()
    fieldnames = ['lead_id', 'name', 'phone', 'email', 'address', 'city', 'country', 'website', 'website_source', 'has_website', 'has_contact', 'needs_website', 'priority', 'contacted', 'source', 'profile_link']
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction='ignore')
    writer.writeheader()
    for lead in leads:
        writer.writerow(lead)

    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=leads.csv'}
    )


if __name__ == '__main__':
    port = int(os.environ.get('PORT', '5000'))
    debug = os.environ.get('FLASK_DEBUG', '').strip().lower() in {'1', 'true', 'yes', 'on'}
    app.run(host='0.0.0.0', port=port, debug=debug)
