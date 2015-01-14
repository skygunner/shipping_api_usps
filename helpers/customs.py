from collections import namedtuple

Customs = namedtuple("Customs", (
    'signature', 'contents_type', 'contents_explanation', 'commodity_code',
    'restriction', 'restriction_comments', 'undeliverable', 'eel_pfc', 'senders_copy', 'items'
))
CustomsItem = namedtuple("CustomsItem", ('description', 'quantity', 'weight', 'value', 'country_of_origin'))