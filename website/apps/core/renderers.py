from rest_framework.renderers import JSONRenderer


def underscore_to_camelcase(word, lower_first=True):
    '''Camelcase by capitalizing at each underscore in word.

    The result defaults to starting with a lowercase.

    '''
    result = ''.join(char.capitalize() for char in word.split('_'))
    retval = (result[0].lower() + result[1:]) if lower_first else result
    return retval


def camelize(data):
    '''Recursively camelcase all dictionary keys.

    Assumes all dictionary keys are strings.
    No side-effects on the data parameter.

    '''
    if isinstance(data, dict):
        retval = {underscore_to_camelcase(key): camelize(value)
                  for key, value in data.items()}
    elif isinstance(data, list):
        retval = [camelize(item) for item in data]
    elif isinstance(data, tuple):
        retval = tuple([camelize(item) for item in data])
    else:
        retval = data
    return retval


class CamelCaseJSONRenderer(JSONRenderer):
    def render(self, data, *args, **kwargs):
        return super(CamelCaseJSONRenderer, self).render(camelize(data), *args, **kwargs)
