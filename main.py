import urllib.parse
import requests
from bs4 import BeautifulSoup
from math import ceil
import time
from requests_html import HTMLSession
import pandas as pd
from datetime import datetime, timedelta

def get_time_range():
    print("\nSelect a time range:")
    print("0. Most recent (no time filter)")
    print("1. Recent past hours")
    print("2. Last 24 hours")
    print("3. Past week")
    print("4. Last month")
    print("5. Last year")
    print("6. Custom date range")
    
    choice = input("Enter your choice (0-6): ")
    
    if choice == '0':
        return ""
    elif choice == '1':
        hours = int(input("Enter the number of past hours: "))
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
        start_date = input("Enter start date (MM/DD/YYYY): ")
        end_date = input("Enter end date (MM/DD/YYYY): ")
        return f"cdr:1,cd_min:{start_date},cd_max:{end_date}"
    else:
        print("Invalid choice. Using default (no time range).")
        return ""

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
        soup = BeautifulSoup(r.html.raw_html, "html.parser")
        result_stats = soup.find('div', {'id': 'result-stats'})
        if result_stats:
            total_results = int(''.join(filter(str.isdigit, result_stats.text)))
            print(f"Total results found: {total_results}, but Google typically shows a maximum of 300 results.")
            return min(total_results, 300)  # Limit to 300 results
        else:
            print("Couldn't find total results. Defaulting to 300.")
            return 300
    except Exception as e:
        print(f"Error fetching total results: {e}")
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
        "month": "days",  # Approximate month as 30 days
        "months": "days",
        "year": "days",   # Approximate year as 365 days
        "years": "days"
    }

    number, unit = relative_time.split()[:2]
    number = int(number)
    if "month" in unit:
        number *= 30
    elif "year" in unit:
        number *= 365

    delta = timedelta(**{time_units.get(unit, "days"): number})
    timestamp = current_time - delta
    return timestamp.strftime("%Y-%m-%d %H:%M:%S")

def extract_news_data(url):
    session = HTMLSession()
    r = session.get(url)
    r.html.render(sleep=4) 
    soup = BeautifulSoup(r.html.raw_html, "html.parser")
    news_results = []
    for item in soup.find_all('div', class_='SoaBEf'):
        title = item.find('div', class_='MBeuO').text if item.find('div', class_='MBeuO') else 'N/A'
        link = item.find('a', class_='WlydOe')['href'] if item.find('a', class_='WlydOe') else 'N/A'
        description = item.find('div', class_='GI74Re').text if item.find('div', class_='GI74Re') else 'N/A'
        source_time = item.find('div', class_='OSrXXb').text if item.find('div', class_='OSrXXb') else 'N/A'
        
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

def main():
    query = input("Enter your search query: ")
    time_range = get_time_range()
    limit = int(input("Enter the number of news titles to scrape (max 300): "))
    
    total_results = get_total_results(query, time_range)
    limit = min(limit, total_results, 300)
    
    all_news_data = []
    for start in range(0, limit, 100):
        url = generate_url(query, time_range, start)
        print(url)
        print(f"\nFetching results {start+1} to {min(start+100, limit)}...")
        news_data = extract_news_data(url)
        all_news_data.extend(news_data)
        
        if len(all_news_data) >= limit:
            break
        
        time.sleep(2)  # Add a delay to avoid overwhelming the server
    
    all_news_data = all_news_data[:limit]
    
    print(f"\nExtracted {len(all_news_data)} news items.")
    
    # Create a DataFrame from the extracted data
    df = pd.DataFrame(all_news_data)
    
    # Generate a filename based on the query and current timestamp
    filename = f"google_news_{query.replace(' ', '_')}_{int(time.time())}.csv"
    
    # Save the DataFrame to a CSV file
    df.to_csv(filename, index=False, encoding='utf-8-sig')
    
    print(f"\nData saved to {filename}")

if __name__ == "__main__":
    main()
