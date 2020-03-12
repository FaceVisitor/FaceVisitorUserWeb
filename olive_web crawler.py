import requests
import urllib.request
from bs4 import BeautifulSoup


def get_product_info(prd_info):
    name_div = prd_info.find("div", {"class": "prd_name"})

    brand_spans = name_div.find("span", {"class": "tx_brand"})

    name_ptags = name_div.find("p", {"class": "tx_name"})

    price_ptag = prd_info.find("p", {"class": "prd_price"})
    price_spans = price_ptag.find("span", {"class": "tx_cur"})
    price_spans2 = price_spans.find("span")

    brand = brand_spans.text
    name = name_ptags.text
    price = price_spans2.text

    imgURL = prd_info.find("img")["src"]

    return {'brand': brand, 'name': name, 'price': price, 'img': imgURL}


def get_page_products(url):
    result = requests.get(url)
    bs_obj = BeautifulSoup(result.content, "html.parser")
    ul = bs_obj.findAll("ul", {"class": "cate_prd_list"})

    for list_num in range(0, len(ul)):
        boxes = ul[list_num].findAll("div", {"class": "prd_info"})
        product_info_list = [get_product_info(prd_info) for prd_info in boxes]
        print(product_info_list)


for page_number in range(1, 23):
    url = "https://www.oliveyoung.co.kr/store/display/getMCategoryList.do?dispCatNo=100000100010006&fltDispCatNo=&prdSort=01&pageIdx={}".format(page_number)
    get_page_products(url)