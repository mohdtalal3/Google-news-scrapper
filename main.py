import argparse
import urllib.parse
import requests
from bs4 import BeautifulSoup
from math import ceil
import time
from requests_html import HTMLSession
import pandas as pd
from datetime import datetime, timedelta
import logging

# Configure logging
logging.basicConfig(filename='google_news_scraper.log', level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')

def get_time_range(choice, hours=None, start_date=None, end_date=None):
    if choice == '0':
        return ""
    elif choice == '1':
        if not hours:
            raise ValueError("Number of hours must be provided for choice 1.")
        return f"qdr:h{hours}"
    elif choice == '2':
        return "qdr:d"
    elif choice == '3':
        return "qdr:w"
    elif choice == '4':
        return "qdr:m"
    elif choice == '5':
        return "qdr:y"
    elif choice == '6':
        if not start_date or not end_date:
            raise ValueError("Start date and end date must be provided for choice 6.")
        return f"cdr:1,cd_min:{start_date},cd_max:{end_date}"
    else:
        raise ValueError("Invalid choice.")


def get_total_results(query, time_range):
    base_url = "https://www.google.com/search"
    params = {
        "q": query,
        "tbm": "nws",
        "num": 1
    }
    if time_range:
        params["tbs"] = time_range
    
    url = f"{base_url}?{urllib.parse.urlencode(params)}"
    try:
        session = HTMLSession()
        r = session.get(url)
        r.html.render(sleep=4)
        r.raise_for_status()  # Raise HTTPError for bad responses
        soup = BeautifulSoup(r.html.raw_html, "html.parser")
        result_stats = soup.find('div', {'id': 'result-stats'})
        if result_stats:
            total_results = int(''.join(filter(str.isdigit, result_stats.text)))
            logging.info(f"Total results found: {total_results}, but Google typically shows a maximum of 300 results.")
            return min(total_results, 300)  
        else:
            logging.warning("Couldn't find total results. Defaulting to 300.")
            return 300
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching total results: {e}")
        return 300
    except Exception as e:
        logging.error(f"Unexpected error fetching total results: {e}")
        return 300


def generate_url(query, time_range, start):
    base_url = "https://www.google.com/search"
    params = {
        "q": query,
        "tbm": "nws",
        "num": 100,
        "start": start
    }
    if time_range:
        params["tbs"] = time_range
    
    return f"{base_url}?{urllib.parse.urlencode(params)}"


def convert_to_timestamp(relative_time):
    current_time = datetime.now()
    time_units = {
        "minute": "minutes",
        "minutes": "minutes",
        "hour": "hours",
        "hours": "hours",
        "day": "days",
        "days": "days",
        "week": "weeks",
        "weeks": "weeks",
        "month": "days",
        "months": "days",
        "year": "days",
        "years": "days"
    }

    try:
        number, unit = relative_time.split()[:2]
        number = int(number)
    except ValueError:
        logging.warning("Can't change time")
        # Handle cases where number cannot be converted to int (e.g., 'LIVE31', 'Just now', 'Now', etc.)
        return current_time.strftime("%Y-%m-%d %H:%M:%S")

    if "month" in unit:
        number *= 30
    elif "year" in unit:
        number *= 365

    delta = timedelta(**{time_units.get(unit, "days"): number})
    timestamp = current_time - delta
    return timestamp.strftime("%Y-%m-%d %H:%M:%S")


def extract_news_data(url):
    try:
        session = HTMLSession()
        r = session.get(url)
        r.html.render(sleep=4)
        r.raise_for_status()  # Raise HTTPError for bad responses
        soup = BeautifulSoup(r.html.raw_html, "html.parser")
        news_results = []
        for item in soup.find_all('div', class_='SoaBEf'):
            title = item.find('div', class_='MBeuO').text if item.find('div', class_='MBeuO') else 'N/A'
            link = item.find('a', class_='WlydOe')['href'] if item.find('a', class_='WlydOe') else 'N/A'
            description = item.find('div', class_='GI74Re').text if item.find('div', class_='GI74Re') else 'N/A'
            source_time = item.find('div', class_='OSrXXb rbYSKb LfVVr').text if item.find('div', class_='OSrXXb rbYSKb LfVVr') else 'N/A'
            
            if 'ago' in source_time:
                timestamp = convert_to_timestamp(source_time)
            else:
                timestamp = source_time

            news_results.append({
                'title': title,
                'link': link,
                'description': description,
                'source_time': source_time,
                'timestamp': timestamp
            })
        
        return news_results
    
    except requests.exceptions.RequestException as e:
        logging.error(f"Error extracting news data from {url}: {e}")
        return []
    except Exception as e:
        logging.error(f"Unexpected error extracting news data from {url}: {e}")
        return []


def main():
    parser = argparse.ArgumentParser(description='Google News Scraper')
    parser.add_argument('query', type=str, help='Search query')
    parser.add_argument('--time_range', type=str, help='Time range filter (0-6)')
    parser.add_argument('--hours', type=int, help='Number of hours for time filter (choice 1)')
    parser.add_argument('--start_date', type=str, help='Start date for custom range (MM/DD/YYYY, choice 6)')
    parser.add_argument('--end_date', type=str, help='End date for custom range (MM/DD/YYYY, choice 6)')
    parser.add_argument('--limit', type=int, default=300, help='Limit number of news items (default: 300)')
    args = parser.parse_args()

    if args.time_range:
        try:
            time_range = get_time_range(args.time_range, args.hours, args.start_date, args.end_date)
        except ValueError as e:
            logging.error(f"Error in time range parameters: {e}")
            return
    else:
        time_range = ""

    total_results = get_total_results(args.query, time_range)
    limit = min(args.limit, total_results, 300)

    all_news_data = []
    for start in range(0, limit, 100):
        url = generate_url(args.query, time_range, start)
        logging.info(f"Fetching results {start+1} to {min(start+100, limit)} from {url}...")
        news_data = extract_news_data(url)
        all_news_data.extend(news_data)
        
        if len(all_news_data) >= limit:
            break
        
        time.sleep(5)  
    
    all_news_data = all_news_data[:limit]
    
    logging.info(f"Extracted {len(all_news_data)} news items.")

    try:
        df = pd.DataFrame(all_news_data)
        
        # Format current time
        current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        # Append selected time range option
        if args.time_range:
            time_range_suffix = f"_option_{args.time_range}"
        else:
            time_range_suffix = "_option_None"

        filename = f"google_news_{args.query.replace(' ', '_')}{time_range_suffix}_{current_time}.csv"
        
        #df.to_csv(filename, index=False, encoding='utf-8-sig')
        df.to_csv(filename, index=False)
        logging.info(f"Data saved to {filename}")
    except Exception as e:
        logging.error(f"Error saving data to CSV: {e}")



if __name__ == "__main__":
    main()
