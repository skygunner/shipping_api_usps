##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2011 NovaPoint Group LLC (<http://www.novapointgroup.com>)
#    Copyright (C) 2004-2010 OpenERP SA (<http://www.openerp.com>)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>
#
##############################################################################

from openerp.osv import fields, osv
from openerp.tools.translate import _
from . import api

class stock_packages(osv.osv):
    _inherit = "stock.packages"

    def cancel_postage(self, cr, uid, ids, context=None):
        for package in self.browse(cr, uid, ids, context=context):
            if package.shipping_company_name.lower() != "usps":
                continue

            usps_config = api.v1.get_config(cr, uid, sale=package.pick_id.sale_id, context=context)
            test = package.pick_id.logis_company.test_mode

            if hasattr(package, "tracking_no") and package.tracking_no:
                try:
                    response = api.v1.cancel_shipping(usps_config, package, shipper=None, test=test)

                except Exception, e:
                    self.pool.get('stock.packages').write(cr, uid, package.id, {'ship_message': str(e)}, context=context)
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'action_warn',
                        'name': _('Exception'),
                        'params': {'title': _('Exception'), 'text': str(e), 'sticky': True}
                    }

                if hasattr(response, "error") or not response.refunds[0].refunded:
                    err = response.error if hasattr(response, "error") else response.refunds[0].message
                    self.pool.get('stock.packages').write(cr, uid, package.id, {'ship_message': err}, context=context)
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'action_warn',
                        'name': _('Failure'),
                        'params': {
                            'title': _('Package #%s Cancellation Failed') % package.packge_no,
                            'text': err,
                            'sticky': True
                        }
                    }

                else:
                    self.pool.get('stock.packages').write(cr, uid, package.id, {
                        'ship_message' : 'Shipment Cancelled', 'tracking_no': ''
                    }, context=context)

        return super(stock_packages, self).cancel_postage(cr, uid, ids, context=context)

stock_packages()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: