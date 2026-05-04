from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from random import randrange

URL = "https://www.imdb.com/search/title/?moviemeter=,10"


def scrape_top10_movies():
    with sync_playwright() as p:
        # Launch a real Chromium browser (headless = no visible window)
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            locale="en-US",
        )
        page = context.new_page()

        # Visit homepage first to acquire WAF cookies, then go to the target URL
        page.goto("https://www.imdb.com/", wait_until="domcontentloaded", timeout=30000)
        page.goto(URL, wait_until="domcontentloaded", timeout=30000)

        # Wait until at least one movie card is visible in the DOM
        page.wait_for_selector("li.ipc-metadata-list-summary-item", timeout=15000)

        html = page.content()
        browser.close()

    soup = BeautifulSoup(html, "html.parser")

    # Anchor to the exact UL container you identified
    movie_list = soup.select_one(
        "ul.ipc-metadata-list.ipc-metadata-list--dividers-between."
        "sc-4b25d7ad-0.fovuLN.detailed-list-view.base.ipc-metadata-list--base"
    )
    # Fallback: grab any matching LI if the UL class ever changes
    if movie_list:
        movie_items = movie_list.select("li.ipc-metadata-list-summary-item")[:10]
    else:
        movie_items = soup.select("li.ipc-metadata-list-summary-item")[:10]

    if not movie_items:
        print("No movies found — IMDB may have updated its HTML structure.")
        return

    print("=" * 50)
    print("        TOP 10 MOVIES ON IMDB")
    print("=" * 50)
    all_movies = []
    for rank, item in enumerate(movie_items, start=1):
        # Title — inside <h3 class="ipc-title__text">  e.g. "10. Resident Evil"
        title_tag = item.select_one("h3.ipc-title__text")
        title = title_tag.get_text(strip=True) if title_tag else "N/A"
        # Strip the leading rank number IMDB embeds (e.g. "10. Resident Evil" → "Resident Evil")
        if title and ". " in title:
            title = title.split(". ", 1)[-1].strip()

        # Link to the title page
        link_tag = item.select_one("a.ipc-title-link-wrapper")
        link = "https://www.imdb.com" + link_tag["href"] if link_tag else "N/A"

        # Release info — inside <li class="ipc-inline-list__item"> under .dli-title-metadata
        metadata_items = item.select("div.dli-title-metadata li.ipc-inline-list__item")
        release = metadata_items[0].get_text(strip=True) if metadata_items else "N/A"

        # Plot — inside <div class="ipc-html-content-inner-div">
        plot_tag = item.select_one("div.ipc-html-content-inner-div")
        plot = plot_tag.get_text(strip=True) if plot_tag else "N/A"

        # IMDb star rating — inside <div data-testid="ratingGroup--container">
        # (may be empty for unreleased titles)
        rating_tag = item.select_one("span.ipc-rating-star--rating")
        rating = rating_tag.get_text(strip=True) if rating_tag else "N/A"
        current_movie = (f"\n#{rank:>2}. {title}", f"      Release : {release}",
                          f"      IMDb ⭐  : {rating}", f"      Plot    : {plot}",
                            f"      Link    : {link}")
        all_movies.append(current_movie)
        #print(f"\n#{rank:>2}. {title}")
        #print(f"      Release : {release}")
        #print(f"      IMDb ⭐  : {rating}")
        #print(f"      Plot    : {plot}")
        #print(f"      Link    : {link}")
    n_movies = len(all_movies)

    while(True):
        idx = randrange(0, n_movies)
        print(all_movies[idx][0])
        print(all_movies[idx][1])
        print(all_movies[idx][2])
        print(all_movies[idx][3])
        print(all_movies[idx][4])
        print("\n" + "=" * 50)
        user_input = input("Do you want another movie (y/n)? ")
        if user_input !='y':
            break


if __name__ == "__main__":
    scrape_top10_movies()