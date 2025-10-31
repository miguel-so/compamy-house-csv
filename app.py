from flask import Flask, request, render_template, send_file, jsonify
import csv
import io
import requests
import time
import os
from datetime import datetime
from typing import Dict, List, Optional
import json

# Load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv is optional

app = Flask(__name__)

# Companies House API configuration
API_BASE_URL = "https://api.company-information.service.gov.uk"
API_KEY = os.getenv('COMPANIES_HOUSE_API_KEY', '')

if not API_KEY:
    print("WARNING: COMPANIES_HOUSE_API_KEY environment variable not set!")
    print("Please set it before running the application.")

# Rate limiting: 600 requests per 5 minutes
RATE_LIMIT_REQUESTS = 600
RATE_LIMIT_WINDOW = 300  # 5 minutes in seconds
request_times = []


def check_rate_limit():
    """Check if we're within rate limits and wait if necessary"""
    global request_times
    now = time.time()
    
    # Remove requests older than the window
    request_times = [t for t in request_times if now - t < RATE_LIMIT_WINDOW]
    
    if len(request_times) >= RATE_LIMIT_REQUESTS:
        # Wait until the oldest request expires
        wait_time = RATE_LIMIT_WINDOW - (now - request_times[0]) + 1
        print(f"Rate limit reached. Waiting {wait_time:.1f} seconds...")
        time.sleep(wait_time)
        request_times = [t for t in request_times if time.time() - t < RATE_LIMIT_WINDOW]
    
    request_times.append(time.time())


def make_api_request(endpoint: str, params: Optional[Dict] = None, method: str = 'GET', json_data: Optional[Dict] = None) -> Optional[Dict]:
    """Make an authenticated request to the Companies House API"""
    if not API_KEY:
        return None
    
    check_rate_limit()
    
    url = f"{API_BASE_URL}{endpoint}"
    headers = {
        'Accept': 'application/json'
    }
    
    try:
        if method == 'POST' and json_data:
            response = requests.post(
                url,
                auth=(API_KEY, ''),
                json=json_data,
                params=params,
                headers=headers,
                timeout=30
            )
        else:
            response = requests.get(
                url,
                auth=(API_KEY, ''),
                params=params,
                headers=headers,
                timeout=30
            )
        
        if response.status_code == 429:
            # Rate limited - wait and retry
            retry_after = int(response.headers.get('Retry-After', 60))
            print(f"Rate limited. Waiting {retry_after} seconds...")
            time.sleep(retry_after)
            return make_api_request(endpoint, params, method, json_data)
        
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"API request failed: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response status: {e.response.status_code}")
            print(f"Response body: {e.response.text[:200]}")
        return None


def format_address(address: Dict) -> str:
    """Format address dictionary into a string"""
    if not address:
        return ''
    
    parts = []
    if address.get('address_line_1'):
        parts.append(address['address_line_1'])
    if address.get('address_line_2'):
        parts.append(address['address_line_2'])
    if address.get('locality'):
        parts.append(address['locality'])
    if address.get('region'):
        parts.append(address['region'])
    if address.get('postal_code'):
        parts.append(address['postal_code'])
    if address.get('country'):
        parts.append(address['country'])
    
    return ', '.join(parts)


def get_company_officers(company_number: str) -> List[Dict]:
    """Fetch officers (directors) for a company"""
    officers = []
    start_index = 0
    items_per_page = 100
    
    while True:
        endpoint = f"/company/{company_number}/officers"
        params = {
            'items_per_page': items_per_page,
            'start_index': start_index,
            'order_by': 'appointed_on',
            'register_view': 'false'
        }
        
        data = make_api_request(endpoint, params)
        if not data or 'items' not in data:
            break
        
        officers.extend(data['items'])
        
        # Check if there are more pages
        if start_index + items_per_page >= data.get('total_count', 0):
            break
        
        start_index += items_per_page
    
    return officers


def search_companies(filters: Dict) -> List[Dict]:
    """Search for companies using the advanced search API"""
    companies = []
    start_index = 0
    items_per_page = 100
    
    # Build query parameters - Companies House advanced search uses JSON body for POST
    # But we can use GET with query params for most filters
    params = {
        'items_per_page': items_per_page,
        'start_index': start_index
    }
    
    # Add filters - map to API parameter names
    if filters.get('company_name'):
        params['q'] = filters['company_name']
    
    if filters.get('company_status'):
        params['company_status'] = filters['company_status']
    
    if filters.get('sic_codes'):
        # SIC codes can be comma-separated or space-separated
        sic_str = filters['sic_codes'].replace(' ', '')
        params['sic_codes'] = sic_str
    
    if filters.get('location'):
        params['location'] = filters['location']
    
    if filters.get('incorporated_from'):
        params['incorporated_from'] = filters['incorporated_from']
    
    if filters.get('incorporated_to'):
        params['incorporated_to'] = filters['incorporated_to']
    
    # Companies House advanced search API uses POST with JSON body
    # But we'll try GET first for simpler queries, then fall back to POST
    endpoint = "/advanced-search/companies"
    
    # Build search body for POST request (advanced search prefers POST)
    search_body = {}
    if filters.get('company_name'):
        search_body['company_name_includes'] = filters['company_name']
    if filters.get('company_status'):
        search_body['company_status'] = [filters['company_status']]
    if filters.get('company_type'):
        search_body['company_type'] = [filters['company_type']]
    if filters.get('sic_codes'):
        sic_list = [code.strip() for code in filters['sic_codes'].split(',') if code.strip()]
        if sic_list:
            search_body['sic_codes'] = sic_list
    if filters.get('location'):
        search_body['location'] = filters['location']
    if filters.get('incorporated_from'):
        search_body['incorporated_from'] = filters['incorporated_from']
    if filters.get('incorporated_to'):
        search_body['incorporated_to'] = filters['incorporated_to']
    
    # Use POST if we have advanced filters, otherwise try GET
    use_post = bool(search_body and (filters.get('company_status') or filters.get('company_type') or filters.get('sic_codes') or filters.get('incorporated_from') or filters.get('incorporated_to')))
    
    while True:
        if use_post:
            # POST request for advanced search
            params['start_index'] = start_index
            data = make_api_request(endpoint, params, method='POST', json_data=search_body)
        else:
            # GET request for simple search
            params['start_index'] = start_index
            if filters.get('company_name'):
                params['q'] = filters['company_name']
            data = make_api_request(endpoint, params)
        
        # If advanced search POST fails, try regular search endpoint
        if not data and filters.get('company_name') and not endpoint.startswith('/search'):
            endpoint = "/search/companies"
            params = {'q': filters['company_name'], 'items_per_page': items_per_page, 'start_index': start_index}
            data = make_api_request(endpoint, params)
        
        if not data or 'items' not in data:
            break
        
        companies.extend(data['items'])
        
        # Check if there are more pages
        total_results = data.get('total_results', 0) or data.get('total_count', 0)
        if total_results == 0 or start_index + items_per_page >= total_results:
            break
        
        start_index += items_per_page
    
    return companies


@app.route('/')
def index():
    """Render the main search page"""
    return render_template('index.html')


@app.route('/search', methods=['POST'])
def search():
    """Handle company search and generate CSV"""
    try:
        # Get filters from form
        filters = {
            'company_name': request.form.get('company_name', '').strip(),
            'company_status': request.form.get('company_status', '').strip() or None,
            'company_type': request.form.get('company_type', '').strip() or None,
            'sic_codes': request.form.get('sic_codes', '').strip() or None,
            'location': request.form.get('location', '').strip() or None,
            'incorporated_from': request.form.get('incorporated_from', '').strip() or None,
            'incorporated_to': request.form.get('incorporated_to', '').strip() or None,
        }
        
        # Remove None values
        filters = {k: v for k, v in filters.items() if v}
        
        if not filters:
            return jsonify({'error': 'Please provide at least one search filter'}), 400
        
        # Search for companies
        companies = search_companies(filters)
        
        if not companies:
            return jsonify({'error': 'No companies found matching your criteria'}), 404
        
        # Create CSV in memory
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header - matching Companies House format with director info added
        writer.writerow([
            'company_name',
            'company_number',
            'company_status',
            'company_type',
            'company_subtype',
            'dissolution_date',
            'incorporation_date',
            'removed_date',
            'registered_date',
            'nature_of_business',
            'registered_office_address',
            'director_name',
            'director_address',
            'director_nationality',
            'director_occupation',
            'director_role',
            'director_appointed_date',
            'director_resigned_date'
        ])
        
        # Process each company
        total_companies = len(companies)
        for idx, company in enumerate(companies):
            company_number = company.get('company_number', '')
            company_name = company.get('company_name', '')
            company_status = company.get('company_status', '')
            company_type = company.get('company_type', '')
            company_subtype = company.get('company_subtype', '')
            dissolution_date = company.get('date_of_cessation', '') or company.get('dissolution_date', '')
            incorporation_date = company.get('date_of_creation', '') or company.get('incorporation_date', '')
            removed_date = company.get('removed_date', '')
            registered_date = company.get('registered_date', '')
            
            # Get SIC codes - can be in different formats
            sic_codes_list = company.get('sic_codes', [])
            if isinstance(sic_codes_list, list):
                nature_of_business = ' '.join([str(code) for code in sic_codes_list if code])
            else:
                nature_of_business = str(sic_codes_list) if sic_codes_list else ''
            
            registered_address = format_address(company.get('registered_office_address', {}))
            
            # Fetch officers for this company
            officers = get_company_officers(company_number)
            
            if not officers:
                # Write company row even if no officers found
                writer.writerow([
                    company_name,
                    company_number,
                    company_status,
                    company_type,
                    company_subtype,
                    dissolution_date,
                    incorporation_date,
                    removed_date,
                    registered_date,
                    nature_of_business,
                    registered_address,
                    '',  # Director Name
                    '',  # Director Address
                    '',  # Director Nationality
                    '',  # Director Occupation
                    '',  # Director Role
                    '',  # Director Appointed Date
                    ''   # Director Resigned Date
                ])
            else:
                # Write a row for each director
                for officer in officers:
                    officer_name = officer.get('name', '')
                    officer_address = format_address(officer.get('address', {}))
                    officer_nationality = officer.get('nationality', '')
                    officer_occupation = officer.get('occupation', '')
                    officer_role = officer.get('officer_role', '')
                    officer_appointed = officer.get('appointed_on', '')
                    officer_resigned = officer.get('resigned_on', '')
                    
                    writer.writerow([
                        company_name,
                        company_number,
                        company_status,
                        company_type,
                        company_subtype,
                        dissolution_date,
                        incorporation_date,
                        removed_date,
                        registered_date,
                        nature_of_business,
                        registered_address,
                        officer_name,
                        officer_address,
                        officer_nationality,
                        officer_occupation,
                        officer_role,
                        officer_appointed,
                        officer_resigned
                    ])
            
            # Log progress
            if (idx + 1) % 10 == 0:
                print(f"Processed {idx + 1}/{total_companies} companies...")
        
        # Prepare CSV for download
        output.seek(0)
        csv_content = output.getvalue()
        output.close()
        
        # Create BytesIO for file download
        csv_bytes = io.BytesIO()
        csv_bytes.write(csv_content.encode('utf-8'))
        csv_bytes.seek(0)
        
        filename = f"companies_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        return send_file(
            csv_bytes,
            mimetype='text/csv',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        print(f"Error during search: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500


@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'ok',
        'api_key_configured': bool(API_KEY)
    })


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=os.getenv('FLASK_DEBUG', 'False') == 'True')
