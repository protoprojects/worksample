from httmock import response, urlmatch, remember_called
from requests.exceptions import ConnectionError, Timeout


@urlmatch(scheme='https', netloc='thirdparty.mortech-inc.com', path='/mpg/servlet/mpgThirdPartyServlet', method='post')
@remember_called
def mortech_response_success(url, request):
    response_file_path = 'support/mortech_test/tests/rate-quote.xml'
    with open(response_file_path) as response_file:
        content = response_file.read()
    return response(201, content, elapsed=0, request=request)


@urlmatch(scheme='https', netloc='thirdparty.mortech-inc.com', path='/mpg/servlet/mpgThirdPartyServlet', method='post')
@remember_called
def mortech_response_status_code_408(url, request):
    return response(408, request=request)


@urlmatch(scheme='https', netloc='thirdparty.mortech-inc.com', path='/mpg/servlet/mpgThirdPartyServlet', method='post')
@remember_called
def mortech_response_status_code_400(url, request):
    return response(400, request=request)


@urlmatch(scheme='https', netloc='thirdparty.mortech-inc.com', path='/mpg/servlet/mpgThirdPartyServlet', method='post')
@remember_called
def mortech_response_status_code_503(url, request):
    return response(503, request=request)


@urlmatch(scheme='https', netloc='thirdparty.mortech-inc.com', path='/mpg/servlet/mpgThirdPartyServlet', method='post')
@remember_called
def mortech_response_blank(url, request):
    response_file_path = 'support/mortech_test/tests/blank.xml'
    with open(response_file_path) as response_file:
        content = response_file.read()
    return response(201, content=content, request=request)


@urlmatch(scheme='https', netloc='thirdparty.mortech-inc.com', path='/mpg/servlet/mpgThirdPartyServlet', method='post')
@remember_called
def mortech_response_no_results(url, request):
    response_file_path = 'website/apps/mortgage_profiles/tests/test_cases/no_results.xml'
    with open(response_file_path) as response_file:
        content = response_file.read()
    return response(201, content=content, request=request)


@urlmatch(scheme='https', netloc='thirdparty.mortech-inc.com', path='/mpg/servlet/mpgThirdPartyServlet', method='post')
@remember_called
def mortech_response_timeout(url, request):
    raise Timeout


@urlmatch(scheme='https', netloc='thirdparty.mortech-inc.com', path='/mpg/servlet/mpgThirdPartyServlet', method='post')
@remember_called
def mortech_response_connection_error(url, request):
    raise ConnectionError
