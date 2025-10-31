# Companies House Advanced Search with Director Export

A lightweight web application that mirrors Companies House "Advanced Search" functionality and exports results to CSV with director names and addresses included.

## Features

- Advanced search filters matching the Companies House website
- Exports CSV with company AND director information
- Includes: Company Name, Status, Director Names, Addresses, Nationality, Occupation, Role, Dates
- Respects Companies House API rate limits (600 requests per 5 minutes)
- Clean, modern web interface
- No login required - just enter your API key

## Prerequisites

- Python 3.8 or higher
- A free Companies House API key ([Get one here](https://developer.company-information.service.gov.uk/get-started))

## Quick Setup

1. **Clone or download this repository**

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up your API key:**
   
   Option A - Using .env file (recommended):
   ```bash
   cp env.example .env
   # Then edit .env and add your API key
   ```
   
   Option B - Export directly:
   ```bash
   export COMPANIES_HOUSE_API_KEY=your_api_key_here
   ```
   
   Or use the setup script:
   ```bash
   ./setup.sh
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

*Note: If a company has multiple directors, there will be one row per director.*

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

## Deployment

### Local Development
```bash
python app.py
```

### Production (using gunicorn)
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### Docker
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
ENV PORT=5000
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]
```

## Troubleshooting

**Error: "COMPANIES_HOUSE_API_KEY environment variable not set"**
- Make sure you've set the API key in `.env` or exported it as an environment variable

**Rate limit errors**
- The app handles rate limits automatically, but very large searches may take time
- Try narrowing your search filters to reduce the number of results

**No results found**
- Verify your search filters are correct
- Check that your API key is valid
- Some filters may require specific formats (e.g., dates as YYYY-MM-DD)

## License

This is a utility tool for personal/business use. Companies House data is subject to their terms of service.

## Support

For Companies House API documentation: https://developer.company-information.service.gov.uk/
