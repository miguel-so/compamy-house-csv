# Companies House Advanced Search with Director Export

## Quick Setup

1. **Clone or download this repository**

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up your API key:**
   
   ```bash
   cp env.example .env
   # Then edit .env and add your API key
   ```

4. **Run the application:**
   ```bash
   python app.py
   ```

5. **Open your browser:**
   Navigate to `http://localhost:5000`

## Usage

1. Fill in one or more search filters:
   - **Company Name**: Partial name matching
   - **Company Status**: Active, Dissolved, etc.
   - **Incorporation Date Range**: From/To dates
   - **SIC Codes**: Comma-separated industry codes
   - **Location**: City or region

2. Click "Search & Download CSV"

3. The CSV file will download automatically with:
   - Company information (name, number, status, dates, SIC codes, address)
   - Director information (name, address, nationality, occupation, role, dates)

## CSV Export Format

Each row contains:
- Company Name
- Company Number
- Company Status
- Incorporation Date
- SIC Codes
- Registered Office Address
- Director Name
- Director Address
- Director Nationality
- Director Occupation
- Director Role
- Director Appointed Date
- Director Resigned Date

## API Rate Limits

The application automatically handles Companies House API rate limits:
- Maximum 600 requests per 5-minute window
- Automatic rate limit detection and retry
- Progress logging for large result sets

## Configuration

Environment variables:
- `COMPANIES_HOUSE_API_KEY` (required): Your Companies House API key
- `PORT` (optional): Server port (default: 5000)
- `FLASK_DEBUG` (optional): Enable debug mode (default: False)

## Support

For Companies House API documentation: https://developer.company-information.service.gov.uk/
