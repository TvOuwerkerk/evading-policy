import urllib.parse as parse
from tld import get_fld

import hashlib
import base64
import re


def __strip_fragment(url: str):
    """Given a url as string, return that url without the fragment."""
    return parse.urlunsplit(parse.urlsplit(url)._replace(fragment=''))


def __strip_scheme(url: str):
    """Given a url as string, return that url without the scheme."""
    return parse.urlunsplit(parse.urlsplit(url)._replace(scheme=''))


def __strip_scheme_and_fragment(url: str):
    """Given a url as string, return that url without the scheme and fragment."""
    return __strip_scheme(__strip_fragment(url))


def __process_policy_string(policy_string):
    """Take a string containing 1 or more referrer-policies and split these up, returning as a list."""
    split_string = re.split(r'[\n]', policy_string)
    for s in split_string:
        if not s:
            split_string.remove(s)
    return split_string


def __unpack_request_response_policy(request_data: dict):
    """From a request-data dict (see Tracker-Radar-Collector output), extract the referrer-policy response header."""
    try:
        return request_data['responseHeaders']['referrer-policy']
    except KeyError:
        return ''


def __is_request_url_third_party(page_url: str, alternate_page_url: str, request_url: str):
    """Given a request url, check whether it requests a resource of a third party relative to (alternate_)page_url"""
    if request_url.startswith('blob:'):
        request_url = request_url[5:]
    try:
        request_fld = get_fld(request_url, fix_protocol=True)
        if request_fld in [get_fld(page_url, fix_protocol=True), get_fld(alternate_page_url, fix_protocol=True)]:
            return False
        return True
    except Exception:
        return False


def __encode_search_dict(to_search: dict[str, str], encoding, encoding_name: str):
    """
    Encodes values and changes keys accordingly for a given dict
    :param to_search: dict containing keyed strings that need to be searched for
    :param encoding: function that encodes a given str
    :param encoding_name: encoding name that is added to keys of to_search dict
    :return: dict containing changed keys and encoded values
    """
    keys = map(lambda a: f'{a}-{encoding_name}', to_search.keys())
    values = map(encoding, to_search.values())
    return dict(zip(keys, values))


def __check_url_in_url(source: str, alternate_source: str, target: str):
    """
    Searches a target URL for occurrences of (parts of) the source URL in several encodings.
    :param source: URL that needs to be searched for
    :param alternate_source: Alternate version of URL that needs to be searched for (in case of redirect)
    :param target: URL that needs to be searched through
    :return: True if (a part of) the source or alternate URL is found, False otherwise
    """
    inp = {'source': source, 'alternate': alternate_source}
    path, path_present, schemeless, fragmentless = ({},) * 4
    for x in ['source', 'alternate']:
        path[x] = parse.urlsplit(inp[x]).path
        path_present[x] = False
        if path[x] == '/':
            path_present[x] = False
        schemeless[x] = __strip_scheme(x)
        fragmentless[x] = __strip_scheme_and_fragment(x)

    encodings = []
    search_dict = {}
    to_search_dict = {'source': source,
                      'redirected': alternate_source,
                      'source_path': path['source'],
                      'redirected_path': path['alternate'],
                      'source_schemeless': schemeless['source'],
                      'redirected_schemeless': schemeless['alternate'],
                      'source_fragmentless': fragmentless['source'],
                      'redirected_fragmentless': fragmentless['alternate']}
    search_dict.update(to_search_dict)
    encodings.append(to_search_dict)
    encodings.append(__encode_search_dict(to_search_dict, lambda a: parse.quote(a, safe=''), 'percent'))
    encodings.append(__encode_search_dict(to_search_dict, lambda a: hashlib.md5(a.encode('utf-8')), 'md5'))
    encodings.append(__encode_search_dict(to_search_dict, lambda a: hashlib.sha1(a.encode('utf-8')), 'sha1'))
    encodings.append(
        __encode_search_dict(to_search_dict, lambda a: base64.urlsafe_b64encode(bytes(a, 'utf-8')), 'base64'))

    for dictionary in encodings:
        search_dict.update(dictionary)

    for x in search_dict.keys():
        if x.startswith('source-path') and not path_present['source']:
            continue
        if x.startswith('redirected-path') and not path_present['alternate']:
            continue
        if str(search_dict[x]) in target:
            return x
    return ''


def __check_url_leakage(leaked_url: str, alternate_leaked_url: str, target_url: str):
    """
    Check whether (part of) a given URL is leaked in the target URL
    :param leaked_url: URL which is potentially (partially) leaked
    :param alternate_leaked_url: Alternate URL which is potentially (partially) leaked
    :param target_url: URL in which (part of) leaked_url could be found
    :return: None if no leakage is found. Dict containing target url, part found and encoding used if leakage is found
    """
    crawled_domain = parse.urlsplit(leaked_url).netloc
    redirected_domain = parse.urlsplit(alternate_leaked_url).netloc

    # If the current request is to a 1st party domain, skip it
    if not __is_request_url_third_party(crawled_domain, redirected_domain, target_url):
        return None

    # Check if (parts of) the crawled url appear in the request url
    check = __check_url_in_url(leaked_url, alternate_leaked_url, target_url)
    if check != '':
        try:
            encoding = check.split('-')[1]
        except IndexError:
            encoding = 'none'
        request_result = {'request-url': target_url,
                          'part-found': check.split('-')[0],
                          'encoding': encoding}
        return request_result
    return None


def __check_unsafe_policy(page_url: str, alternate_page_url: str, request_data: dict):
    # If the current request is to a 1st party domain, skip it
    if not __is_request_url_third_party(page_url, alternate_page_url, request_data['url']):
        return None
    request_result = {'request-url': request_data['url'],
                      'request-referrer-policy': ''}
    request_policy = request_data['referrerPolicy']
    if (request_policy == 'no-referrer-when-downgrade' and parse.urlparse(request_data['url']).scheme == 'http') \
            or request_policy == 'unsafe-url':
        request_result['referrer-policy'] = request_policy
        if 'responseHeaders' in request_data and 'referrer-policy' in request_data['responseHeaders']:
            response_policy = request_data['responseHeaders']['referrer-policy']
            if response_policy == request_policy:
                request_result['equal-to-response'] = True
            else:
                request_result['equal-to-response'] = False
        return request_result
    return None


def get_leakage_domains(leakage_list):
    """
    Given a list of leakages that have occurred, return a set of the domains that has been leaked to
    :param leakage_list: list of leakages inferred from gathered data.
    :return: set containing the domains being leaked to, stripped of scheme, fragment, and query, but including path
    """
    return_set = set()
    for i in leakage_list:
        stripped_leakage = parse.urlunsplit(
            parse.urlsplit(i['request-url'])._replace(scheme='', fragment='', query=''))
        if stripped_leakage.startswith('//'):
            stripped_leakage = stripped_leakage[2:]
        return_set.add(stripped_leakage)
    return return_set


def set_file_output_redirected_url(file_output, crawled_url, final_url):
    """Given the requested url and the actually visited url, set the file_output record's 'redirected' value"""
    if crawled_url != final_url:
        file_output['redirected-url'] = final_url
    return file_output


def get_request_info(request_data: dict, file_results: dict, request_source: str, alt_request_source: str):
    """
    Takes a captured HTTP request as dictionary and adds inferred data to the file_results dictionary.
    Sets 'referrer-policy' and 'referrer-policy-set' fields if this request is made to (alt_)request_source
    Adds request to 'request-leakage' list if this request leaked info on the (alt_)request_source
    Adds request to 'unsafe-outbound' list of request was made to third party using an unsafe referrer-policy
    :param request_data: dictionary containing the data of the request
    :param file_results: dictionary to which data about the request must be saved
    :param request_source: url from which the request was made
    :param alt_request_source: alternate (possibly redirected) url from which the request was made
    :return:
    """
    request_url = request_data['url'].strip('/')
    request_source = request_source.strip('/')
    alt_request_source = alt_request_source.strip('/')

    request_ref_policy = request_data['referrerPolicy']
    response_ref_policy = __unpack_request_response_policy(request_data)

    # Get the referrer policy and whether this was set through http on this page
    if request_url in [request_source, __strip_fragment(request_source), alt_request_source,
                       __strip_fragment(alt_request_source)]:
        if response_ref_policy:
            file_results['referrer-policy'] = response_ref_policy
            file_results['referrer-policy-set'] = True
        else:
            file_results['referrer-policy'] = request_ref_policy

    leakage_result = __check_url_leakage(request_source, alt_request_source, request_data['url'])
    if 'referer' in request_data:
        if leakage_result is not None and request_data['referer'] not in [request_source, alt_request_source]:
            file_results['request-leakage'].append(leakage_result)

    unsafe_result = __check_unsafe_policy(request_source, alt_request_source, request_data)
    if unsafe_result is not None:
        file_results['unsafe-outbound'].append(unsafe_result)

    policies_used = __process_policy_string(response_ref_policy) if response_ref_policy \
        else __process_policy_string(request_ref_policy)
    for p in policies_used:
        file_results['policies-used'][p] += 1

    return file_results
