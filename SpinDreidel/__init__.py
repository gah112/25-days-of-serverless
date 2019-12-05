import logging
import random
import azure.functions as func

random.seed(1)
def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python SpinDreidel() function processed a request')
    values = ['ג','ה','ש','נ']
    result = values[random.randint(a=0,b=3)]
    return func.HttpResponse(f"{result}")