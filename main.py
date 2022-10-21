import os
import json
import csv
import logging
import smtplib
import ssl
from datetime import datetime
from email.message import EmailMessage
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By


logging.basicConfig(filename="log.txt", level=logging.INFO, format="%(levelname)s %(asctime)s %(message)s")
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))

sender = "sender-emailaddress"
receiver = "receiver-emailaddress"
password = ""

msg = EmailMessage()
msg["from"] = sender
msg["to"] = receiver
msg["subject"] = "PS5 available"

context = ssl.create_default_context()

negative_phrases = ["out of stock", "currently unavailable"]
request_phrases = ["available by invitation"]
preorder_phrases = ["pre-order now"]

headers = ["Product Name", "URL", "Availability Status", "Product Check Timestamp", "Email Sent"]

all_products = []


def main():
    currys_url = "https://www.currys.co.uk/gaming/consoles/consoles/sony/ps5"
    amazon_url = "https://www.amazon.co.uk/s?k=playstation+5+console&i=videogames&crid=3MTP2XNDB5AIL&sprefix=playstation+5+console%2Cvideogames%2C65&ref=nb_sb_noss_1"

    with open("all_products.csv") as products_infile:
        reader = csv.DictReader(products_infile)
        for line in reader:
            all_products.append(dict(line))
    
    amazon_availability(amazon_url)
    currys_availability(currys_url)

    with open("all_products.csv", "w", newline="") as products_outfile:
        writer = csv.DictWriter(products_outfile, fieldnames=headers)
        writer.writeheader()
        writer.writerows(all_products)

    driver.close()


def amazon_availability(url):
    """Get products info and availability status from Amazon online store"""
    driver.get(url)

    try:
        products = driver.find_elements('xpath', '//*[@data-csa-c-item-id]')
    except NoSuchElementException:
        logging.error(f"{url} Unable to find any relevant products on this url")
        return
    else:
        product_info = [product.text.split("\n") for product in products]
        product_urls = []
        # get url for each product and add it to list - the site sometimes includes product indexes for items that aren't there, therefore although 16 products are shown on the first page,
        # the sample used to loop is greater to account for these extra index elements
        for x in range(3, 20):
            try:
                product_url = driver.find_element('xpath', f'//*[@id="search"]/div[1]/div[1]/div/span[3]/div[2]/div[{x}]/div/div/div/div/div/div[1]/div/div[2]/div/span/a')
                product_urls.append(product_url.get_attribute("href"))
            except NoSuchElementException:
                logging.error(f"{url} Unable to retrieve url for the product no.{x-2}")
        # add each found url to the end of its corresponding item_info list
        for y in range(len(product_info)):
            product_info[y].append(product_urls[y])

        for item_info in product_info:
            product_dict = {}
            product_name = item_info[0]
            product_url = item_info[-1]

            if "PlayStation 5 Console" not in product_name:
                continue

            product_dict["Product Name"] = product_name
            product_dict["URL"] = f"{product_url}"
            product_dict["Product Check Timestamp"] = datetime.now()

            stock_status = item_info[-2]
            check_phrases(stock_status, product_dict)
            if product_dict["Availability Status"] in ["Not Available", "Available by request", "Available for pre-order"]:
                update_all_products(product_dict)
                continue

            if "FREE Delivery" or "FREE Delivery by Amazon" in item_info:
                product_dict["Availability Status"] = "Available"
                logging.info(f"{product_url} item is available as identified by the 'FREE delivery' text")
            else:
                product_dict["Availability Status"] = "Not Available"
                logging.info(f"{product_url} item is likely not available as there is no sign of the 'FREE delivery' text")
            
            update_all_products(product_dict)
    return


def currys_availability(url):
    """Get products info and availability status from Currys online store"""
    driver.get(url)

    try:
        products = driver.find_elements(By.CLASS_NAME, 'product-item-element')
    except NoSuchElementException:
        logging.error(f"{url} Unable to find any relevant products on this url")
        return
    else:
        product_ids = [product.get_attribute("id") for product in products]
        for id in product_ids:
            product_dict = {}

            try: 
                product_info = driver.find_element('xpath', f'//*[@id="{id}"]/div[1]/div/div[1]/div[1]/div[2]/div[2]/div[1]/span[1]/div/a').get_attribute("data-datalayer-config")
            except NoSuchElementException:
                # log error: product info couldn't be obtained
                logging.error(f"{url} Unable to retrieve any product info for the product id: {id}")
                return
            else:
                product_info = json.loads(product_info)
                product_name = product_info["name"]
                product_url = "https://www.currys.co.uk" + product_info["destination"]["url"]
                product_dict["Product Name"] = product_name
                product_dict["URL"] = f'"{product_url}"'
                product_dict["Product Check Timestamp"] = datetime.now()
                try:
                    stock_status = driver.find_element('xpath', f'//*[@id="{id}"]/div[1]/div/div[1]/div[1]/div[2]/div[2]/div[2]/div[3]/div/div/p')
                except NoSuchElementException:
                    product_dict["Availability Status"] = "Available"
                    update_all_products(product_dict)
                    logging.info(f"{product_url} AVAILABLE item assumed to be available as no out of stock message is present")
                    continue
                else:
                    status_text = stock_status.get_attribute("innerHTML")
                    check_phrases(status_text, product_dict)
                    update_all_products(product_dict)
    return


def check_phrases(text, product_dict):
    """Check what type of availability the product is so that the correct action can be taken"""
    in_phrases = False
    for phrase in negative_phrases:
        if phrase in text.lower():
            product_dict["Availability Status"] = "Not Available"
            logging.info(f'{product_dict["URL"]} NOT AVAILABLE out of stock message found')
            in_phrases = True
    for phrase in request_phrases:
        if phrase in text.lower():
            product_dict["Availability Status"] = "Available by request"
            logging.info(f'{product_dict["URL"]} AVAILABLE BY REQUEST available by request message found')
            in_phrases = True
    for phrase in preorder_phrases:        
        if phrase in text.lower():
            product_dict["Availability Status"] = "Available for pre-order"
            logging.info(f'{product_dict["URL"]} PRE-ORDER available for pre-order message found')
            in_phrases = True
    if not in_phrases:
        product_dict["Availability Status"] = "Available"
        logging.info(f'{product_dict["URL"]} AVAILABLE nothing found in message to suggest product is not available')
    
    return product_dict


def update_all_products(product_dict):
    """Update records of all products stored in csv file, either updating existing products, or adding newly found products"""
    for x in range(len(all_products)):
        if product_dict["Product Name"] == all_products[x]["Product Name"]:
            product_dict["Email Sent"] = all_products[x]["Email Sent"]
            # reset email sent status if the products availability status changes so that a new email can be sent out when the product is back in stock again
            if product_dict["Availability Status"] != all_products[x]["Availability Status"]:
                product_dict["Email Sent"] = False
            all_products[x] = product_dict
            send_email(product_dict)
            return
    
    product_dict["Email Sent"] = False
    send_email(product_dict)
    all_products.append(product_dict)
    return


def send_email(product_dict):
    """Find the correct email template to send out depending on what type of availability the product has - only send if an email hasn't already gone out before since the products most recent change in availability status"""
    # find a way to update that tweet has been sent for available products so that no more tweets are sent until it becomes unavailable then available again
    if product_dict["Email Sent"] == False:
        if product_dict["Availability Status"] == "Available":
            # send available email template
            product_available_email(product_dict)
            product_dict["Email Sent"] = True
        elif product_dict["Availability Status"] == "Available by request":
            # send available by request email template
            product_dict["Email Sent"] = True
        elif product_dict["Availability Status"] == "Available for pre-order":
            # send pre-order email template
            product_dict["Email Sent"] = True
    return product_dict


def product_available_email(product_dict):
    """Send email if product is available"""
    msg_body = f"""
    {product_dict["Product Name"]} is currently available at {product_dict["URL"]}
    """
    msg.set_content(msg_body)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as smtp:
        try:
            smtp.login(sender, password)
            smtp.sendmail(sender, receiver, msg.as_string())
        except (smtplib.SMTPAuthenticationError, smtplib.SMTPResponseException):
            logging.warning("The gmail username and/or password you entered is incorrect")
            return

        
if __name__ == "__main__":
    main()