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
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    }
    
    try:
        if method == 'POST' and json_data:
            # For POST requests, Companies House API expects all data in JSON body
            # No query parameters for advanced search endpoint
            print(f"Making POST request to: {url}")
            print(f"JSON data: {json.dumps(json_data, indent=2)[:500]}...")  # Print first 500 chars
            response = requests.post(
                url,
                auth=(API_KEY, ''),
                json=json_data,
                headers=headers,
                timeout=30
            )
            print(f"Response status: {response.status_code}")
            if response.status_code != 200:
                print(f"Response text: {response.text[:500]}")
                # If 405, the advanced search endpoint might not be available
                if response.status_code == 405:
                    print("ERROR: Advanced search endpoint returned 405. This endpoint may not be available in the public API.")
                    return None
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
    
    # Build pagination parameters (always needed)
    params = {
        'items_per_page': items_per_page,
        'start_index': start_index
    }
    
    # Companies House advanced search API ONLY accepts POST requests
    endpoint = "/advanced-search/companies"
    
    # Build search body for POST request (required format)
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
    
    # Advanced search always requires POST - if no advanced filters, use regular search endpoint
    use_advanced_search = bool(search_body and (filters.get('company_status') or filters.get('company_type') or filters.get('sic_codes') or filters.get('incorporated_from') or filters.get('incorporated_to') or filters.get('location')))
    
    while True:
        if use_advanced_search:
            # POST request for advanced search (ONLY method accepted)
            # Companies House API uses 'size' for items per page, not 'items_per_page'
            full_search_body = search_body.copy()
            full_search_body['size'] = items_per_page  # API uses 'size' not 'items_per_page'
            full_search_body['start_index'] = start_index
            
            print(f"POST request body: {json.dumps(full_search_body, indent=2)}")
            print(f"POST request URL: {API_BASE_URL}{endpoint}")
            data = make_api_request(endpoint, None, method='POST', json_data=full_search_body)
        elif filters.get('company_name'):
            # Use regular search endpoint for simple name-only searches
            endpoint = "/search/companies"
            params = {
                'q': filters['company_name'],
                'items_per_page': items_per_page,
                'start_index': start_index
            }
            data = make_api_request(endpoint, params)
        else:
            # No valid filters
            break
        
        # If advanced search fails (405 error), it means the endpoint doesn't exist or isn't available
        # The Companies House public API may not have advanced search - return error with helpful message
        if not data and use_advanced_search:
            print("\n❌ ERROR: Advanced search endpoint is not available in the Companies House public API.")
            print("The /advanced-search/companies endpoint returns 405 Method Not Allowed.")
            print("\nPossible solutions:")
            print("1. The advanced search may require a different API version or subscription")
            print("2. Try using the regular search with company name only")
            print("3. Check Companies House API documentation for the correct endpoint")
            return []  # Return empty list so user sees error message
        
        if not data or 'items' not in data:
            break
        
        # Add companies from this page
        page_items = data.get('items', [])
        companies.extend(page_items)
        
        print(f"Fetched page: {len(page_items)} companies (start_index={start_index}, total so far: {len(companies)})")
        
        # Check if there are more pages
        # Companies House API uses different field names in different endpoints
        total_results = data.get('total_results', 0) or data.get('total_count', 0) or data.get('total_items', 0)
        
        # Check if we've fetched all results
        if total_results > 0:
            print(f"Total results available: {total_results}")
            if start_index + len(page_items) >= total_results:
                print(f"All results fetched. Total: {len(companies)}")
                break
        elif len(page_items) < items_per_page:
            # If we got fewer items than requested, we're on the last page
            print(f"Last page reached (got {len(page_items)} items). Total: {len(companies)}")
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
        print(f"Searching with filters: {filters}")
        companies = search_companies(filters)
        print(f"Found {len(companies)} companies total")
        
        if not companies:
            error_msg = 'No companies found matching your criteria.'
            # Check if advanced search was attempted
            if any(filters.get(k) for k in ['sic_codes', 'incorporated_from', 'incorporated_to', 'company_status', 'company_type']):
                error_msg += '\n\n⚠️ IMPORTANT: The Companies House public API does not support advanced search.\n'
                error_msg += 'The /advanced-search/companies endpoint returns "405 Method Not Allowed".'
            return jsonify({'error': error_msg}), 404
        
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
