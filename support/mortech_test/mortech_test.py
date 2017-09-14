import logging
from logging.handlers import RotatingFileHandler

from flask import Flask, send_from_directory

app = Flask(__name__)
# app.debug = True


@app.route('/mortech_test', methods=['POST'])
def simple():
    path = 'tests'
    response = 'rate-quote.xml'
    return send_from_directory(path, response)


if __name__ == '__main__':
    handler = RotatingFileHandler('mortech.log', maxBytes=10000, backupCount=1)
    handler.setLevel(logging.INFO)
    app.logger.addHandler(handler)
    app.run(port=5555)
