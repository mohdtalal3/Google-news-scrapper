import urllib.parse
import requests
from bs4 import BeautifulSoup
from math import ceil
from requests_html import HTMLSession

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
        "num": 100
    }
    if time_range:
        params["tbs"] = time_range
    
    url = f"{base_url}?{urllib.parse.urlencode(params)}"
    print(url)
    try:
        session = HTMLSession()
        r = session.get(url)
        r.html.render(sleep=4)
        soup = BeautifulSoup(r.html.raw_html, "html.parser")
        result_stats = soup.find('div', {'id': 'result-stats'})
        if result_stats:
            print(result_stats)
            total_results = int(''.join(filter(str.isdigit, result_stats.text)))
            print(f"Total results found: {total_results}")
            return min(total_results, 1000)  # Google typically limits to 1000 results
        else:
            print("Couldn't find total results. Defaulting to 1000.")
            return 1000
    except Exception as e:
        print(f"Error fetching total results: {e}")
        return 1000

def generate_urls(query, time_range, limit):
    total_results = get_total_results(query, time_range)
    limit = min(limit, total_results)
    
    base_url = "https://www.google.com/search"
    urls = []
    results_per_page = 100
    num_pages = ceil(limit / results_per_page)
    
    for page in range(num_pages):
        remaining = limit - page * results_per_page
        params = {
            "q": query,
            "tbm": "nws",
            "num": min(results_per_page, remaining),
            "start": page * results_per_page
        }
        
        if time_range:
            params["tbs"] = time_range
        
        url = f"{base_url}?{urllib.parse.urlencode(params)}"
        urls.append(url)
    
    return urls, limit

def main():
    query = input("Enter your search query: ")
    time_range = get_time_range()
    limit = int(input("Enter the number of news titles to scrape: "))
    
    urls, actual_limit = generate_urls(query, time_range, limit)
    
    print(f"\nURLs to scrape {actual_limit} news titles (or all available if less):")
    for i, url in enumerate(urls, 1):
        print(f"\nURL {i}:")
        print(url)

if __name__ == "__main__":
    main()