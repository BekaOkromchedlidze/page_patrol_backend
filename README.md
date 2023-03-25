
# Web-Scraper

Web-Scraper is a REST API service developed with Python FastAPI framework. It can be used to query a web element for a particular string. Some possible use cases include checking if a out of stock product has been marked as in stock on online retailers website or to check if a product with a specified text has been added to an adverts website. The API is passed the URL of the website, XPATH of the web element, and string to look out for. The html content of the web element is returned if the string is found within the web element.




## Installation

If deploying locally, checkout project and run the following from the root directory

```bash
  pip install --upgrade -r requirements.txt | uvicorn src.main:app --host 0.0.0.0 --port 80
```
Alternatively, you may deploy using Docker by running the following:

```bash
  docker run -p 80:80 --name web-scraper okromcb2/web-scraper:latest
```
## Usage

You may access the API documentation by going to 
```bash
  localhost:80/docs
```
