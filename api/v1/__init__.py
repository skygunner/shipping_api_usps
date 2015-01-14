"""
Defines public methods and classes for other modules to use.
Breaking changes are never introduced within a version.

"""
import math
from openerp import pooler
from ...helpers import label, endicia, shipping, settings
from ...helpers.customs import Customs, CustomsItem

def get_config(cr, uid, sale=None, logistic_company_id=None, context=None):
    """Returns the USPS configuration relevant to the given object."""
    config = None

    if sale and sale.usps_shipper_id:
        config = sale.usps_shipper_id

    if not config and logistic_company_id:
        log_comp = pooler.get_pool('logistic.company').browse(cr, uid, logistic_company_id, context=context)
        config = log_comp.usps_account_shipping_id if log_comp else None

    if not config and sale:
        config = sale.company_id.usps_account_shipping_id

    if not config:
        # Just go by uid.
        user_pool = pooler.get_pool(cr.dbname).get("res.users")
        user = user_pool.browse(cr, uid, uid, context=context)
        config = user.company_id.usps_account_shipping_id

    return config if config else settings.ENDICIA_CONFIG


def get_quotes(config, package, sale=None, from_address=None, to_address=None, test=None):
    """Calculates the cost of shipping for all USPS's services."""

    # Get the shipper and recipient addresses for this order.
    if sale:
        from_address = sale.company_id.partner_id
        to_address = sale.partner_shipping_id or ''
        from_address.state = from_address.state_id.code
        from_address.country = from_address.country_id.name
        to_address.state = to_address.state_id.code
        to_address.country = to_address.country_id.name

    # Create the Address objects that we'll later pass to our Endicia object.
    shipper = shipping.Address(
        from_address.name, from_address.street, from_address.city, from_address.state,
        from_address.zip, from_address.country, address2=from_address.street2
    )
    recipient = shipping.Address(
        to_address.name, to_address.street, to_address.city, to_address.state,
        to_address.zip, to_address.country, address2=to_address.street2
    )

    # Get the package's weight in ounces.
    weight = math.modf(float(package.weight))
    ounces = (weight[1] * 16) + round(weight[0] * 16, 2)

    endicia_package = endicia.Package(
        None, str(ounces), None, package.height,
        package.length, package.width
    )
    endicia_package.shape = endicia_package.calculate_container()

    if test == None:
        test = config["sandbox"]

    # Connect to the Endicia API.
    api = endicia.Endicia(config, debug=test)

    # Ask Endicia what the cost of shipping for this package is.
    response = api.rate(endicia_package, shipper, recipient)

    return [
        {"company": "USPS", "container": endicia_package.shape, "service": item['service'], "price": item["cost"]}
        for item in response['info']
    ]

def get_label(config, package, service, picking=None, from_address=None, to_address=None, customs=None, test=None,
              image_format="EPL2"):
    if test == None:
        test = config["sandbox"]

    try:
        return label.Label(package, picking=picking, from_address=from_address, to_address=to_address,
                           customs=customs, config=config, test=test
        ).get(service, image_format=image_format)
    except Exception as e:
        return {"success": False, "error": str(e)}

def get_account_status(config, test=None):
    if test == None:
        test = config["sandbox"]

    api = endicia.Endicia(config, debug=test)
    return api.account_status(debug=test)

def cancel_shipping(config, package, shipper=None, test=None):
    if test == None:
        test = config["sandbox"]

    return endicia.Endicia(config, debug=test).cancel(package.tracking_no, debug=test)