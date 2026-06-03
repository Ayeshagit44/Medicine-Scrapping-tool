from flask import Flask, jsonify, request, Response
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import json
import re

app = Flask(__name__)

@app.route('/')
def home():

    return jsonify({
        "status": True,
        "message": "Medicine API Running Successfully"
    })
# =====================================================
# 1MG API
# =====================================================
@app.route("/medicine", methods=["GET"])
def medicine():

    medicine_input = request.args.get("name")

    if not medicine_input:

        return jsonify({
            "status": False,
            "message": "Medicine names required"
        })

    # ==========================================
    # SUPPORT:
    # [dolo650,pan-d,aciloc 150]
    # ==========================================
    medicine_input = medicine_input.strip()

    if medicine_input.startswith("[") and medicine_input.endswith("]"):

        medicine_input = medicine_input[1:-1]

        medicines = [
            m.strip()
            for m in medicine_input.split(",")
            if m.strip()
        ]

    else:

        medicines = [medicine_input]

    final_result = []

    try:

        with sync_playwright() as p:

            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage"
                ]
            )

            context = browser.new_context(
                viewport={
                    "width": 1366,
                    "height": 768
                },
                user_agent=(
                    "Mozilla/5.0 "
                    "(Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 "
                    "(KHTML, like Gecko) "
                    "Chrome/137.0.0.0 "
                    "Safari/537.36"
                )
            )

            page = context.new_page()

            # ==========================================
            # LOOP MEDICINES
            # ==========================================
            for keyword in medicines:

                result = {

                    "Manufacturer": "N/A",

                    "Medicine Name": "N/A",

                    "Medicine URL": "N/A",

                    "Pack Type": "N/A",

                    "Prescription Required": "No",

                    "Quantity": "N/A",

                    "Salt Composition": "N/A",

                    "Storage": "N/A",

                    "searched_name": keyword,

                    "status": True
                }

                try:

                    # ==========================================
                    # SEARCH PAGE
                    # ==========================================
                    search_url = (
                        f"https://www.1mg.com/search/all?name={keyword}"
                    )

                    page.goto(
                        search_url,
                        timeout=60000,
                        wait_until="domcontentloaded"
                    )

                    page.wait_for_timeout(4000)

                    medicine_url = ""

                    links = page.locator("a")

                    for i in range(links.count()):

                        try:

                            href = links.nth(i).get_attribute("href")

                            if href and "/drugs/" in href:

                                if href.startswith("/"):

                                    medicine_url = (
                                        "https://www.1mg.com"
                                        + href
                                    )

                                else:

                                    medicine_url = href

                                break

                        except:
                            pass

                    # ==========================================
                    # NOT FOUND
                    # ==========================================
                    if medicine_url == "":

                        result["status"] = False

                        result["message"] = (
                            "Medicine not found"
                        )

                        final_result.append(result)

                        continue

                    result["Medicine URL"] = medicine_url

                    # ==========================================
                    # OPEN MEDICINE PAGE
                    # ==========================================
                    page.goto(
                        medicine_url,
                        timeout=60000,
                        wait_until="domcontentloaded"
                    )

                    page.wait_for_timeout(4000)

                    body = page.locator(
                        "body"
                    ).inner_text()

                    # ==========================================
                    # MEDICINE NAME
                    # ==========================================
                    try:

                        result["Medicine Name"] = (
                            page.locator("h1")
                            .first
                            .inner_text()
                            .strip()
                        )

                    except:
                        pass

                    # ==========================================
                    # MANUFACTURER
                    # ==========================================
                    try:

                        patterns = [

                            r"MARKETER\s*\n([^\n]+)",

                            r"Manufacturer\s*\n([^\n]+)"
                        ]

                        for pattern in patterns:

                            match = re.search(
                                pattern,
                                body,
                                re.IGNORECASE
                            )

                            if match:

                                result["Manufacturer"] = (
                                    match.group(1).strip()
                                )

                                break

                    except:
                        pass

                    # ==========================================
                    # SALT COMPOSITION
                    # ==========================================
                    try:

                        match = re.search(
                            r"SALT COMPOSITION\s*\n([^\n]+)",
                            body,
                            re.IGNORECASE
                        )

                        if match:

                            result[
                                "Salt Composition"
                            ] = (
                                match.group(1).strip()
                            )

                    except:
                        pass

                    # ==========================================
                    # STORAGE
                    # ==========================================
                    try:

                        match = re.search(
                            r"STORAGE\s*\n([^\n]+)",
                            body,
                            re.IGNORECASE
                        )

                        if match:

                            storage = (
                                match.group(1)
                                .strip()
                            )

                            storage = (
                                storage
                                .replace("\\u00b0", "°")
                                .replace("\u00b0", "°")
                            )

                            result["Storage"] = storage

                    except:
                        pass

                    # ==========================================
                    # QUANTITY
                    # ==========================================
                    try:

                        quantity_patterns = [

                            r"(\d+\.?\d*\s*tablets?\s*in\s*\d+\s*strip)",

                            r"(\d+\.?\d*\s*capsules?\s*in\s*\d+\s*strip)",

                            r"(\d+\.?\d*\s*tablet\s*pr\s*in\s*\d+\s*strip)",

                            r"(\d+\.?\d*\s*capsule\s*pr\s*in\s*\d+\s*strip)",

                            r"(\d+\s*ml)",

                            r"(\d+\s*bottle)"
                        ]

                        for pattern in quantity_patterns:

                            match = re.search(
                                pattern,
                                body,
                                re.IGNORECASE
                            )

                            if match:

                                result["Quantity"] = (
                                    match.group(1)
                                )

                                break

                    except:
                        pass

                    # ==========================================
                    # PACK TYPE
                    # ==========================================
                    title = (
                        result["Medicine Name"]
                        .lower()
                    )

                    if "tablet" in title:

                        result["Pack Type"] = "Tablet"

                    elif "capsule" in title:

                        result["Pack Type"] = "Capsule"

                    elif "syrup" in title:

                        result["Pack Type"] = "Syrup"

                    elif "injection" in title:

                        result["Pack Type"] = "Injection"

                    elif "cream" in title:

                        result["Pack Type"] = "Cream"

                    elif "ointment" in title:

                        result["Pack Type"] = "Ointment"

                    elif "gel" in title:

                        result["Pack Type"] = "Gel"

                    # ==========================================
                    # PRESCRIPTION
                    # ==========================================
                    if (
                        "prescription required"
                        in body.lower()
                    ):

                        result[
                            "Prescription Required"
                        ] = "Yes"

                    else:

                        result[
                            "Prescription Required"
                        ] = "No"

                    final_result.append(result)

                except Exception as e:

                    result["status"] = False

                    result["message"] = str(e)

                    final_result.append(result)

            browser.close()

            return Response(
                json.dumps(
                    final_result,
                    ensure_ascii=False,
                    indent=4
                ),
                mimetype="application/json"
            )

    except Exception as e:

        return jsonify({
            "status": False,
            "message": str(e)
        })

# =====================================================
# SUPERTAILS API
# =====================================================
@app.route("/supertails", methods=["GET"])
def supertails():

    keyword = request.args.get("name")

    if not keyword:
        return jsonify({
            "status": False,
            "message": "Product name required"
        })

    try:

        with sync_playwright() as p:

            browser = p.chromium.launch(
                headless=False,  # change to True after testing
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage"
                ]
            )

            context = browser.new_context(
                viewport={"width": 1366, "height": 768},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"
            )

            page = context.new_page()

            # SEARCH PRODUCT
            search_url = f"https://supertails.com/search?q={keyword}"

            page.goto(
                search_url,
                wait_until="domcontentloaded",
                timeout=120000
            )

            page.wait_for_timeout(8000)

            soup = BeautifulSoup(
                page.content(),
                "html.parser"
            )

            product_url = ""

            for a in soup.find_all("a", href=True):

                href = a["href"]

                if "/products/" in href:

                    if href.startswith("http"):
                        product_url = href
                    else:
                        product_url = (
                            "https://supertails.com"
                            + href
                        )

                    break

            if product_url == "":

                browser.close()

                return jsonify({
                    "status": False,
                    "message": "Product not found"
                })

            print("Product URL:", product_url)

            # OPEN PRODUCT PAGE
            page.goto(
                product_url,
                wait_until="domcontentloaded",
                timeout=120000
            )

            page.wait_for_timeout(10000)

            html = page.content()

            soup = BeautifulSoup(
                html,
                "html.parser"
            )

            # PRODUCT NAME
            product_name = "N/A"

            h1 = soup.find("h1")

            if h1:
                product_name = h1.get_text(strip=True)

            # SAVE HTML FOR DEBUGGING
            with open(
                "supertails_product.html",
                "w",
                encoding="utf-8"
            ) as f:
                f.write(html)

            # SPECIFICATIONS
            specifications = {}

            tables = soup.find_all("table")

            for table in tables:

                rows = table.find_all("tr")

                for row in rows:

                    cols = row.find_all(
                        ["td", "th"]
                    )

                    if len(cols) >= 2:

                        key = cols[0].get_text(
                            strip=True
                        )

                        value = cols[1].get_text(
                            strip=True
                        )

                        specifications[key] = value

            result = {

                "status": True,

                "searched_name": keyword,

                "Product Name": product_name,

                "Food Type":
                    specifications.get(
                        "Food type",
                        "N/A"
                    ),

                "Size/Weight":
                    specifications.get(
                        "Size/Weight",
                        "N/A"
                    ),

                "Ingredients":
                    specifications.get(
                        "Ingredients",
                        "N/A"
                    ),

                "Health Benefits":
                    specifications.get(
                        "Health Benefits",
                        "N/A"
                    ),

                "Storage":
                    specifications.get(
                        "Storage",
                        "N/A"
                    ),

                "Manufacturing Location":
                    specifications.get(
                        "Manufacturing Location",
                        "N/A"
                    ),

                "Certifications":
                    specifications.get(
                        "Certifications",
                        "N/A"
                    ),

                "Product URL":
                    product_url
            }

            browser.close()

            return jsonify(result)

    except Exception as e:

        return jsonify({
            "status": False,
            "message": str(e)
        })


# =====================================================
# MAIN
# =====================================================
if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5001,
        debug=True
    )