#!/usr/bin/env python

'''convert a mortech xml results file to csv'''

import csv

from lxml import etree


def header_names(fee_descriptions):
    return [
        'lender_name',
        'amortization_type',
        'program_category',
        'program_name',
        'points',
        'rate',
        'monthly_premium',
        'piti',
        'upfront_fee',
        'origination_fee',
        'apr'] + fee_descriptions


def parse(string):
    xml = etree.fromstring(string)
    fee_descriptions = sorted(set(xml.xpath('//quote/quote_detail/fees/fee_list/fee/@description')))
    headers = header_names(fee_descriptions)
    quotes = [quote_row(quote, fee_descriptions)
              for quote in xml.xpath('/mortech/results/quote')]
    return [headers] + quotes


def quote_row(quote, fee_descriptions):
    # pylint: disable=too-many-locals
    lender_name = quote.get('vendor_name')
    amortization_type = quote.getparent().get('termType')
    program_category = quote.getparent().get('product_name')
    program_name = quote.get('vendor_product_name')
    points = quote.xpath('quote_detail/@price')[0]
    rate = quote.xpath('quote_detail/@rate')[0]
    monthly_premium = quote.xpath('quote_detail')[0].get('monthly_premium')
    piti = quote.xpath('quote_detail/@piti')[0]
    upfront_fee = quote.xpath('quote_detail')[0].get('upfront_fee')
    origination_fee = quote.xpath('quote_detail/@originationFee')[0]
    apr = quote.xpath('quote_detail/@apr')[0]
    fees = {fee.get('description'): fee.get('feeamount')
            for fee in quote.xpath('quote_detail/fees/fee_list/fee')}
    row = [
        lender_name,
        amortization_type,
        program_category,
        program_name,
        points,
        rate,
        monthly_premium,
        piti,
        upfront_fee,
        origination_fee,
        apr]
    row.extend([fees.get(desc, '') for desc in fee_descriptions])
    return row


def main():
    import sys
    with open(sys.argv[1], 'r') as stream_in:
        rows = parse(stream_in.read())

    with open(sys.argv[2], 'wb') as stream_out:
        writer = csv.writer(stream_out, dialect='excel')
        writer.writerows(rows)


if '__main__' == __name__:
    main()
