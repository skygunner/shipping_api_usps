"""
Defines public methods and classes for other modules to use.
Breaking changes are never introduced within a version.

"""
from openerp import pooler
from ...helpers import label, endicia

def get_config(cr, uid, sale=None, logistic_company_id=None, context=None):
    """Returns the USPS configuration relevant to the given object."""

    config = None
    criteria = []

    if sale and sale.usps_shipper_id:
        return sale.usps_shipper_id

    # Search by logistic company specified at sale, if one *was* specified.
    if logistic_company_id:
        criteria += [('logistic_company_id','=',logistic_company_id)]

    if sale:
        # Search for accounts either belonging to the company that the sale belongs to,
        # or that have no company specified.
        criteria += ['|',('company_id','=',sale.company_id.id),('company_id','=',None)]

        config_pool = pooler.get_pool(cr.dbname).get("usps.account.shipping")
        config = config_pool.browse(cr, uid,
            config_pool.search(cr, uid, criteria, limit=1, order='company_id DESC', context=context),
            context=context
        )

        if isinstance(config, (list, tuple)) and len(config) > 0:
            config = config[0]

    return config if config else None

def get_label(config, pick_id, package, service=None):
    return label.get(pick_id, package, service=service, config=config)

def cancel_shipping(config, package, shipper, test=None):
    api = endicia.Endicia(config, debug=(test if test != None else False))
    return api.cancel(package,shipper, debug=test)