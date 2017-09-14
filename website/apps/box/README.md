Box Application
---------------

This application is for handling files and folders on [Box.com](https://www.box.com/) cloud storage.
We are using [python sdk](https://github.com/box/box-python-sdk) interface for interacting with the Box API. Official [API documentation](https://docs.box.com/docs).


----------


**Possible errors and exceptions**

Box.com provides list of possible [error messages & solutions](https://docs.box.com/docs/detailed-error-messages).

List of possible *box-python-sdk* exceptions (hierarchy):

1. Actual requests (python lib) exceptions:
- IOError
- RequestException
- ConnectionError
- SSLError
- HTTPError
- Timeout
- ConnectTimeout
- ReadTimeout
2. Actual box SDK exceptions :
- Exception
- BoxException
- BoxAPIException
- BoxOAuthException
