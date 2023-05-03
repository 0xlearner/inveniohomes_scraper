import httpx
import json
import math
from bs4 import BeautifulSoup

all_results = []

headers = {
    "authority": "portal.inveniohomes.com",
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "accept-language": "en,ru;q=0.9",
    "cache-control": "max-age=0",
    # 'cookie': 'cookiesession1=678A3E4ADFDAAADC3A172507D5E2CAAA; Pl.userlang=eng; DisplayDivasCookiesBanner=yes; Cookie Management={"declined":"","all":"Cookie Management,DisplayDivasCookiesBanner,DisplayDivasCookiesBanner,Pl.userlang,clientdstoffset,clienttz,cookiesession1,dl_row_count,offset,stdtimezoneoffset","accept_all":"true","last_checked":""}; _ga=GA1.1.75901916.1681572384; _iub_cs-91895404=%7B%22timestamp%22%3A%222023-04-24T22%3A06%3A32.143Z%22%2C%22version%22%3A%221.46.3%22%2C%22purposes%22%3A%7B%221%22%3Atrue%2C%223%22%3Atrue%2C%224%22%3Atrue%7D%2C%22id%22%3A%2291895404%22%7D; _ga_6ZJQ78P7LF=GS1.1.1682701599.2.0.1682702440.0.0.0; ASP.NET_SessionId=3crvykrmvyrs5fz25xpqfidc; offset=-300; stdtimezoneoffset=-300; clientdstoffset=0; clienttz=Asia%2FKarachi; _ga_NQGSYX1FS4=GS1.1.1683035089.28.0.1683035146.0.0.0; .ASPXAUTH=18F7ED219855610425D6FF8D59EDE4B270C06CA21CE51921A75005356D0B0512B8EDC7585A14B7EE6731AAE2F90F75197D9C15E361B8F3D61841EE62ABBA861C20289E5718718D21F6DDEBB21175FDCC700504E2A79888B05FA0AE18896CA3531E59264BF1B649A046F6F2A1FF05CA658876E527F5E5DF235DCB09F2D0400306',
    "referer": "https://portal.inveniohomes.com/user/account/login?ReturnUrl=%2f",
    "sec-ch-ua": '"Chromium";v="110", "Not A(Brand";v="24", "YaBrowser";v="23"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Linux"',
    "sec-fetch-dest": "document",
    "sec-fetch-mode": "navigate",
    "sec-fetch-site": "same-origin",
    "sec-fetch-user": "?1",
    "upgrade-insecure-requests": "1",
    "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 YaBrowser/23.3.1.906 (beta) Yowser/2.5 Safari/537.36",
}


def inveniohomes_fetch_data(login_url, login_creds, api_url, post_data, client):
    client.post(
        login_url,
        headers=headers,
        data=login_creds,
        timeout=40,
    )

    api_response = client.post(api_url, headers=headers, data=post_data)

    json_string = api_response.json()
    json_bloc = json.loads(json_string)
    total_listings = json_bloc[0]["result"][0]["total_count"]
    parsed_param = json.loads(post_data["parms"].replace("arg1=", ""))[0]
    listings_per_page = parsed_param["search_limit"]
    total_pages = round(math.ceil(total_listings / int(listings_per_page)))
    destinations = [
        "RGIBIZA",
        "RGMYKONOS",
        "RGSARDINIA",
        "RGFRMNTERA",
        "RGMALLORCA",
        "RGPORTUGAL",
    ]

    for destination in destinations:
        for page_no in range(1, total_pages + 1):
            print(f"Scraping {destination[2:]} ---> page # {page_no}")
            parsed_param = json.loads(post_data["parms"].replace("arg1=", ""))[0]
            parsed_param["destination"] = str(destination)
            parsed_param["page_number"] = str(page_no)
            post_data["parms"] = "arg1=[" + json.dumps(parsed_param) + "]"
            api_pagination_response = client.post(
                api_url, headers=headers, data=post_data
            )
            j_string = api_pagination_response.json()
            j_bloc = json.loads(j_string)
            results = []
            response_data = j_bloc[0]["result"]
            if response_data is not None:
                for data in response_data:
                    try:
                        loc = data["geolocation"]
                    except:
                        loc = "N/A"
                    results.append(
                        {
                            "Listing_url": "https://portal.inveniohomes.com/villa/"
                            + data["bp_uuid"],
                            "Guests": data["guests"],
                            "Rooms": data["bedrooms"],
                            "Bathrooms": data["bathrooms"],
                            "Short_Description": data["tagline"],
                            "Price": data["villa_price"],
                            "Cordinates": loc,
                            "City": data["city"],
                        }
                    )
                print(len(results))
                for idx, listing in enumerate(results):
                    print(f"Listing # {idx} ---> {listing['Listing_url']}")
                    html_listing = client.get(
                        listing["Listing_url"], headers=headers, timeout=30
                    )
                    soup = BeautifulSoup(html_listing.text, "html.parser")
                    marked_days_string = soup.select_one("#div_htmledit_224_calender")
                    loc = soup.select_one("#div_htmledit_224_villa_footer").text
                    if "License Number:" in loc:
                        loc_idx = loc.index("License Number:")
                        results[idx]["Location"] = loc[:loc_idx]
                    if marked_days_string:
                        marked_days = marked_days_string.text.replace("\n", "")
                        parsed_marked_days = json.loads(marked_days)
                        start_dates = [
                            d["s_start_date"].split("T")[0] for d in parsed_marked_days
                        ]
                        end_dates = [
                            d["s_end_date"].split("T")[0] for d in parsed_marked_days
                        ]
                        booking_days = []
                        for start, end in zip(start_dates, end_dates):
                            booking_days.append(start + " - " + end)
                        results[idx]["Booking_days"] = booking_days

                    amenities_string = soup.select_one("#div_htmledit_224_amenities")
                    if amenities_string:
                        amenities = amenities_string.text.replace("\n", "")
                        parsed_amenities = json.loads(amenities)
                        results[idx]["Amenities"] = [
                            a["model"] for a in parsed_amenities
                        ]
                    images_string = soup.select_one("#div_htmledit_224_gallery")
                    if images_string:
                        images = images_string.text.replace("\n", "")
                        parsed_images = json.loads(images)["all_images"]
                        results[idx]["Images"] = [i["path"] for i in parsed_images]

                all_results.append(results)
                to_json()


def to_json():
    flat_list = [item for sublist in all_results for item in sublist]
    data = [{k: v for k, v in d.items() if k != "Listing_url"} for d in flat_list]
    with open("invenio_homes_listings_data.json", "w") as jf:
        jf.write(json.dumps(data, indent=2))
    print("Done!")


def run_scraper(login_url, login_creds, api_url, post_data):
    with httpx.Client(timeout=40) as client:
        inveniohomes_fetch_data(login_url, login_creds, api_url, post_data, client)


if __name__ == "__main__":
    login_creds = {
        "ReturnUrl": "/",
        "referrerUrl": "https://portal.inveniohomes.com/",
        "Email": "email",
        "Password": "password",
    }

    post_data = {
        "document_no": "307",
        "attrib_code": "307_bp_tile",
        "parms": 'arg1=[{"search_limit":"52","search_id":"","on_behalf":"8193","page_number":"1","sort_order":"villa_price~DESC","destination":"RGMYKONOS","license_options":"null","min_bedrooms":"1","max_bedrooms":"10","numberof_guests":"1","availability":"100"}]',
        "er_code": "",
    }

    login_url = "https://portal.inveniohomes.com/user/account/login"

    api_url = "https://portal.inveniohomes.com/contentloader/CallDBMethod?source=actions/method_type&type=db&name=search"

    run_scraper(login_url, login_creds, api_url, post_data)
