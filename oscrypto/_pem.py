# coding: utf-8

"""
Encoding DER to PEM and decoding PEM to DER
"""

from __future__ import unicode_literals, division, absolute_import, print_function

import sys
import base64
import re

if sys.version_info < (3,):
    str_cls = unicode  #pylint: disable=E0602
    byte_cls = str
    from cStringIO import StringIO as BytesIO  #pylint: disable=F0401
else:
    str_cls = str
    byte_cls = bytes
    from io import BytesIO



def armor(type_name, der_bytes, headers=None):
    """
    Armors a DER-encoded byte string in PEM

    :param der_bytes:
        A byte string to be armored

    :param type_name:
        A unicode string that will be capitalized and placed in the header
        and footer of the block. E.g. "CERTIFICATE", "PRIVATE KEY", etc. This
        will appear as "-----BEGIN CERTIFICATE-----" and
        "-----END CERTIFICATE-----".

    :param headers:
        An OrderedDict of the header lines to write after the BEGIN line

    :return:
        A byte string of the PEM block
    """

    if not isinstance(der_bytes, byte_cls):
        raise ValueError('der_bytes must be a byte string, not %s' % der_bytes.__class__.__name__)

    if not isinstance(type_name, str_cls):
        raise ValueError('type_name must be a unicode string, not %s' % type_name.__class__.__name__)

    type_name = type_name.upper().encode('ascii')

    output = BytesIO()
    output.write(b'-----BEGIN %s-----\n' % type_name)
    if headers:
        for key in headers:
            output.write(b'%s: %s\n' % (key.encode('ascii'), headers[key].encode('ascii')))
    b64_bytes = base64.b64encode(der_bytes)
    b64_len = len(b64_bytes)
    i = 0
    while i < b64_len:
        output.write(b64_bytes[i:i+64])
        output.write(b'\n')
        i += 64
    output.write(b'-----END %s-----\n' % type_name)

    return output.getvalue()


def _unarmor(pem_bytes):
    """
    Convert a PEM-encoded byte string into one or more DER-encoded byte strings

    :param pem_bytes:
        A byte string of the PEM-encoded data

    :raises:
        ValueError - when the pem_bytes do not appear to be PEM-encoded bytes

    :return:
        A generator of 3-element tuples in the format: (type_name, headers,
        der_bytes). The type_name is a unicode string of what is between
        "-----BEGIN " and "-----". Examples include: "CERTIFICATE",
        "PUBLIC KEY", "PRIVATE KEY". The headers is a dict containing any lines
        in the form "Name: Value" that are right after the header.
    """

    if not isinstance(pem_bytes, byte_cls):
        raise ValueError('pem_bytes must be a byte string, not %s' % pem_bytes.__class__.__name__)

    beginning = pem_bytes[0:10].lstrip()

    if beginning[0:5] != b'-----':
        raise ValueError('pem_bytes does not begin with -----')

    # Valid states include: None, "headers", "body"
    state = None
    headers = {}
    base64_data = b''
    type_name = None

    line_num = 0
    for line in pem_bytes.splitlines(False):
        line_num += 1

        if line == b'':
            continue

        if state is None:
            if line[0:5] != b'-----':
                raise ValueError('pem_bytes does not being with -----')

            type_name_match = re.match(b'^----- ?BEGIN ([A-Z0-9 ]+) ?-----', line)
            if not type_name_match:
                raise ValueError('Line %s of pem_bytes does not contain a header in the format "-----BEGIN (TYPE_NAME)-----"' % line_num)
            type_name = type_name_match.group(1).decode('ascii')

            state = 'headers'
            continue

        if state == 'headers':
            if line.find(b':') == -1:
                state = 'body'
            else:
                decoded_line = line.decode('ascii')
                name, value = decoded_line.split(':', 1)
                headers[name] = value
                continue

        if state == 'body':
            if line[0:5] == b'-----':
                der_bytes = base64.b64decode(base64_data)

                yield (type_name, headers, der_bytes)

                state = None
                headers = {}
                base64_data = b''
                type_name = None
                continue

            base64_data += line


def unarmor(pem_bytes, multiple=False):
    """
    Convert a PEM-encoded byte string into a DER-encoded byte string

    :param pem_bytes:
        A byte string of the PEM-encoded data

    :param multiple:
        If True, function will return a generator

    :raises:
        ValueError - when the pem_bytes do not appear to be PEM-encoded bytes

    :return:
        A 3-element tuple (type_name, headers, der_bytes). The type_name is a
        unicode string of what is between "-----BEGIN " and "-----". Examples
        include: "CERTIFICATE", "PUBLIC KEY", "PRIVATE KEY". The headers is a
        dict containing any lines in the form "Name: Value" that are right
        after the header.
    """

    generator = _unarmor(pem_bytes)

    if not multiple:
        return next(generator)

    return generator