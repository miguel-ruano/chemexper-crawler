import scrapy
import json
import re


class ChemexperProducts(scrapy.Spider):
    name = "chemexper-products"
    start_urls = ["http://www.chemexper.com/chemicals/"]

    def parse(self, response):
        items = self.__chemical_catalog_links(response, True)

    def __chemical_catalog_links(
        self, response, save: bool = False, cache: bool = False
    ) -> list:
        items_cache = (
            ChemexperProducts._read_json_data("cache/chemical-catalog.json")
            if cache
            else []
        )
        if items_cache != None and len(items_cache) > 0:
            return items_cache

        items = []
        for table in response.css("table"):
            for chemical_catalog in response.css("tr > td"):
                chemical_catalog_link = chemical_catalog.css("a")
                items.append(
                    {
                        "title": chemical_catalog_link.css("::text").get(),
                        "simple-key": re.search(
                            r"\d+", chemical_catalog_link.attrib["href"], re.DOTALL
                        ),
                        "link": response.urljoin(chemical_catalog_link.attrib["href"]),
                    }
                )
        if save:
            ChemexperProducts._save_json_data("cache/chemical-catalog.json", items)
        return items

    def __chemical_links_of_catalog(
        self, response, key: str = "", save: bool = False
    ) -> list:
        file = "cache/catalog-" + key + "}/chemicals.json"
        items_cache = ChemexperProducts._read_json_data(file)
        if items_cache != None and len(items_cache) > 0:
            return items_cache

        items = []
        for table in response.css("table"):
            for chemical in response.css("tbody tr:not(:first-child) > td"):
                chemical_link = chemical.css("a")
                items.append(
                    {
                        "title": chemical_link.css("::text").get(),
                        "link": response.urljoin(chemical_link.attrib["href"]),
                        "rn-cas": chemical[1].css("::text").get(),
                    }
                )
        if save:
            ChemexperProducts._save_json_data(file, items)
        return items

    def _extract_chemical_data(self, response, key: str, save: bool = False):
        file = "cache/chemicals/key.json"
        chemical = {}
        tables = response.css("table")
        # data info
        columns = tables[1].css("tbody tr td")
        chemical["label"] = columns[0].css("::text").get()
        chemical["molecule_img_url"] = response.urljoin(
            columns[1].css("span img").attrib["src"]
        )
        chemical["predict_nmr_spectrum_url"] = response.urljoin(
            columns[1].css(">a")[1].attrib["href"]
        )
        chemical["props"] = (
            self.__table_map_props_extractor(columns[2])
            + self.__table_map_props_extractor(columns[3])
            + self.__table_map_props_extractor(columns[4])
            + self.__table_map_props_extractor(columns[5])
        )
        chemical["permanent_link"] = response.urljoin(
            columns[6].css("a").attrib["href"]
        )

        # supliers
        suppliers_pages = list(
            map(
                lambda link: response.urljoin(link),
                tables[4]
                .css("tbody tr")[1]
                .css("td")[1]
                .css("a")
                .attrib["href"]
                .getAll(),
            )
        )
        suppliers_data = self.__supplier_extract_and_next(tables[3], suppliers_pages, 0) 
        chemical['suppliers'] = suppliers_data
        return chemical

    def __supplier_extract_and_next(self, response, next: list, index: int = 0):
        suppliers = []
        for supplier_row in response.css("tbody tr:not(:first-child)"):
            suppliers.append(self.__extract_supplier_data(supplier_row))
        # cant not check next for url !!HERE ERROR
        return suppliers

    def __table_map_props_extractor(self, response):
        props = []
        for row in response.css("table tr"):
            label = row.css("th::text").get().replace(":", "")
            value = row.css("td::text").get()
            link = response.urljoin(row.css("td a").attrib["href"])
            props.append({"label": label, "value": value, "link": link})
        return props

    def __extract_supplier_data(self, response):
        supplier = {}
        columns = response.css("td")
        supplier["label"] = columns[0].css("::text").get()
        supplier["description"] = {"label": "", "url": ""}
        supplier["description"]["label"] = columns[1].css("::text").get()
        supplier["description"]["url"] = response.urljoin(
            columns[1].css("a").attrib["href"]
        )
        supplier["reference"] = columns[2].css("::text").get()
        return supplier

    @staticmethod
    def _read_json_data(file: str):
        with open(file) as json_file:
            data = json.load(json_file)
            return data["data"]

    @staticmethod
    def _save_json_data(file: str, data):
        data_json = {}
        data_json["data"] = data
        with open(file, "w") as outfile:
            json.dump(data_json, outfile)
