# How to Use Companies House CSV Export

## Quick Start Guide

### Step 1: Start the Application

Open a terminal in the project directory and run:

```bash
python app.py
```

You should see output like:
```
 * Running on http://0.0.0.0:5000
```

### Step 2: Open in Your Browser

Open your web browser and navigate to:

**http://localhost:5000**

This is a **browser-based interface** - you don't need any other tools!

## Using the Search Filters

The interface provides the same search criteria as the Companies House website:

### 1. **Company Name** (optional)
   - Enter part or all of a company name
   - Example: `"Tech Solutions"`
   - Supports partial matching

### 2. **Company Status**
   - Select from dropdown: Active, Dissolved, Liquidation, etc.
   - Leave as "All Statuses" to include everything

### 3. **Company Type** (new!)
   - Select: Private Limited (Ltd), Public Limited (PLC), LLP, CIC
   - Matches the "Company type" filter on Companies House

### 4. **Incorporation Date Range**
   - **Incorporated From**: Start date (YYYY-MM-DD format)
   - **Incorporated To**: End date (YYYY-MM-DD format)
   - Example: From `2024-01-01` To `2024-12-31`
   - **This is the same date range filter as Companies House website!**

### 5. **SIC Codes**
   - Enter comma-separated SIC codes
   - Example: `43220, 43210, 62012`
   - Leave empty to search all industries

### 6. **Location** (optional)
   - Enter city or region name
   - Example: `London`, `Manchester`, `Scotland`

## Performing a Search

1. **Fill in your filters** (at least one is required)
   - For example: Set Company Status to "Active" and a date range

2. **Click " Search & Download CSV"**

3. **Wait for processing** - A loading spinner will show progress
   - The app searches companies matching your criteria
   - Then fetches director information for each company
   - This may take a moment for large result sets

4. **CSV downloads automatically** - Your browser will download the file
   - Filename format: `companies_export_YYYYMMDD_HHMMSS.csv`

## What You Get in the CSV

The CSV includes **all the same fields** as the Companies House export, **PLUS director information**:

### Company Fields (same as Companies House):
- `company_name`
- `company_number`
- `company_status`
- `company_type`
- `company_subtype`
- `dissolution_date`
- `incorporation_date`
- `removed_date`
- `registered_date`
- `nature_of_business` (SIC codes)
- `registered_office_address`

### Director Fields (NEW - not in Companies House export):
- `director_name`
- `director_address`
- `director_nationality`
- `director_occupation`
- `director_role`
- `director_appointed_date`
- `director_resigned_date`

### Important Notes:

- **Multiple Directors = Multiple Rows**: If a company has 3 directors, you'll get 3 rows (one per director) with the same company information
- **Companies Without Directors**: Will still appear with empty director fields
- **All Company Fields Match**: The CSV format matches your existing Companies House exports, making it easy to merge or compare

## Example Usage

### Example 1: Active Companies in Date Range
- Company Status: `Active`
- Incorporated From: `2024-01-01`
- Incorporated To: `2024-12-31`
- Click "Search & Download CSV"

Result: CSV with all active companies incorporated in 2024, with their directors listed.

### Example 2: Specific SIC Code + Location
- SIC Codes: `43220` (Plumbing)
- Location: `London`
- Click "Search & Download CSV"

Result: Plumbing companies in London with director information.

### Example 3: Company Type + Date Range
- Company Type: `Private Limited Company (Ltd)`
- Incorporated From: `2025-01-01`
- Incorporated To: `2025-10-10`
- Click "Search & Download CSV"

Result: All private limited companies incorporated in 2025 (so far) with directors.

## Troubleshooting

**No results found?**
- Try removing some filters to broaden the search
- Check date format is YYYY-MM-DD
- Verify your API key is set correctly

**Search taking a long time?**
- Large date ranges or broad filters return many results
- The app fetches director info for each company (one API call per company)
- Progress is logged in the terminal

**CSV missing directors?**
- Some companies may not have directors listed
- Directors who resigned won't appear if filtered
- Check the director fields - they'll be empty if none found

## API Rate Limits

The application automatically handles Companies House rate limits (600 requests per 5 minutes). Very large searches may take time due to:
- Multiple companies in results
- Each company requires an additional API call for directors
- Automatic rate limit detection and waiting

## Need Help?

- Check the main README.md for setup instructions
- Ensure your API key is set: `COMPANIES_HOUSE_API_KEY` in `.env` file
- Verify you're accessing `http://localhost:5000` (not https)
