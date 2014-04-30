# -*- coding: utf-8 -*-
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

import re
import base64
import os

from openerp.osv import fields, osv
from openerp.tools.translate import _
from helpers.endicia import Package
from . import api


class logistic_company(osv.osv):

    _inherit = "logistic.company"

    def _get_company_code(self, cr, user, context=None):
        res = super(logistic_company, self)._get_company_code(cr, user, context=context)
        res.append(('usps', 'USPS'))
        return res

    _columns = {
        'ship_company_code' : fields.selection(_get_company_code, 'Ship Company', method=True, required=True, size=64),
    }

logistic_company()


class stock_packages(osv.osv):
    _inherit = "stock.packages"
    _columns = {
            'usps_confirmation_number': fields.char('USPS Confirm Number', size=64, readonly=True),
     }

stock_packages()


class _base_stock_picking(object):

    def _get_company_code(self, cr, user, context=None):
        res = super(_base_stock_picking, self)._get_company_code(cr, user, context=context)
        res.append(('usps', 'USPS'))
        return res

    def _get_service_type_usps(self, cr, uid, context=None):
        return [(x, re.sub(r'((?<=[a-z])[A-Z]|(?<!\A)[A-Z](?=[a-z]))', r' \1', x)) for x in Package.shipment_types]

    def _get_first_class_mail_type_usps(self, cr, uid, context=None):
        return [
            ('Letter', 'Letter'),
            ('Flat', 'Flat'),
            ('Parcel', 'Parcel'),
            ('Postcard', 'Postcard'),
        ]

    def _get_container_usps(self, cr, uid, context=None):
        return [(x, re.sub(r'((?<=[a-z])[A-Z]|(?<!\A)[A-Z](?=[a-z]))', r' \1', x)) for x in Package.shapes]

    def _get_size_usps(self, cr, uid, context=None):
        return [
            ('REGULAR', 'Regular'),
            ('LARGE', 'Large'),
         ]

    _columns = {
            'ship_company_code': fields.selection(_get_company_code, 'Ship Company', method=True, size=64),
            'usps_confirmation_number' : fields.char('Confirmation Number', size=64, readonly=True),
            'usps_service_type' : fields.selection(_get_service_type_usps, 'Service Type', size=100),
            'usps_package_location' : fields.selection([
                    ('Front Door', 'Front Door'),
                    ('Back Door', 'Back Door'),
                    ('Side Door', 'Side Door'),
                    ('Knock on Door/Ring Bell', 'Knock on Door/Ring Bell'),
                    ('Mail Room', 'Mail Room'),
                    ('Office', 'Office'),
                    ('Reception', 'Reception'),
                    ('In/At Mailbox', 'In/At Mailbox'),
                    ('Other', 'Other'),
               ], 'Package Location'),
            'usps_first_class_mail_type' : fields.selection(_get_first_class_mail_type_usps, 'First Class Mail Type', size=50),
            'usps_container' : fields.selection(_get_container_usps, 'Container', size=100),
            'usps_size' : fields.selection(_get_size_usps, 'Size'),
            'usps_length' : fields.float('Length'),
            'usps_width' :  fields.float('Width'),
            'usps_height' :  fields.float('Height'),
            'usps_girth' :  fields.float('Girth'),
    }

    _defaults = {
        'usps_service_type'         : 'Priority',
        'usps_package_location'     : 'Front Door',
        'usps_first_class_mail_type': 'Parcel',
        'usps_size'                 : 'REGULAR',
        'usps_container'            : 'Variable',
    }

    def print_labels(self, cr, uid, ids, context=None):
        order = self.browse(cr, uid, type(ids) == type([]) and ids[0] or ids, context=context)

        # Pass on up this function call if the shipping company specified was not USPS.
        if (order.ship_company_code != 'usps'
        or not (order.logis_company and order.logis_company.ship_company_code == 'usps')):
            return super(_base_stock_picking, self).print_labels(cr, uid, ids, context=context)

        # TODO: Let admin choose printer name.
        res = {
            'type': 'ir.actions.client',
            'tag': 'printer_proxy.print',
            'name': _('Print Shipping Label'),
            'params': {'printer_name': 'zebra', 'data': [], 'format': 'epl2'}
        }

        label_dir = os.path.dirname(os.path.realpath(__file__)) + '/labels' + '/%s' % order.id

        for package in order.packages_ids:
            label = open(label_dir + "/%s.epl" % package.id)
            res['params']['data'].append(base64.b64encode(label.read()))
            label.close()

        return res

    def process_ship(self, cr, uid, ids, context=None):
        # TODO: Let admin choose printer name.
        res = {
            'type': 'ir.actions.client',
            'tag': 'printer_proxy.print',
            'name': _('Print Shipping Label'),
            'params': {'printer_name': 'zebra', 'data': [], 'format': 'epl2'}
        }
        data = self.browse(cr, uid, type(ids) == type([]) and ids[0] or ids, context=context)

        # Pass on up this function call if the shipping company specified was not USPS.
        if data.ship_company_code != 'usps':
            return super(_base_stock_picking, self).process_ship(cr, uid, ids, context=context)

        if not (data.logis_company or data.shipper or data.usps_service):
            raise osv.except_osv("Warning", "Please select a Logistics Company, Shipper and Shipping Service.")

        if not (data.logis_company and data.logis_company.ship_company_code == 'usps'):
            return super(_base_stock_picking, self).process_ship(cr, uid, ids, context=context)

        if not data.packages_ids or len(data.packages_ids) == 0:
            raise osv.except_osv("Warning", "Please define your packages.")

        error = False
        usps_config = api.v1.get_config(cr, uid, sale=data.sale_id, context=context)

        for pkg in data.packages_ids:
            try:
                # Get the shipping label, store it, and return it.
                label = api.v1.get_label(usps_config, data, pkg)
                res['params']['data'].append(base64.b64encode(label.label))
                self.pool.get('stock.packages').write(cr, uid, [pkg.id], {
                    'logo':label.label, 'tracking_no': label.tracking,
                    'usps_confirmation_number': label.tracking, 'ship_message': 'Shipment has processed'
                })

            except Exception, e:
                if not error:
                    error = []
                error_str = str(e)
                error.append(error_str)

            cr.commit()
            if error:
                self.pool.get('stock.packages').write(cr, uid, pkg.id, {'ship_message': error_str}, context=context)

        if not error:
            self.write(cr, uid, data.id, {
                'ship_state':'ready_pick', 'ship_message': 'Shipment has been processed.'
            }, context=context)

            return res
        else:
            self.write(cr, uid, data.id, {
                'ship_message': 'Error occured on processing some of packages, ' +
                                'for details please see the status packages.'
            }, context=context)

            # @todo: raise appropriate error msg
            raise osv.except_osv(_('Errors encountered while processing packages'), _(str(error)))

        return res

    def process_void(self, cr, uid, ids, context=None):
        do = self.browse(cr, uid, type(ids) == type([]) and ids[0] or ids, context=context)
        if do.ship_company_code != 'usps':
            return super(_base_stock_picking, self).process_void(cr, uid, ids, context=context)

        if not (do.logis_company and do.logis_company.ship_company_code == 'usps'):
            return super(_base_stock_picking, self).process_void(cr, uid, ids, context=context)

        test = do.logis_company.test_mode
        error = False

        for pack in do.packages_ids:
            if hasattr(pack, "tracking_no") and pack.tracking_no:
                try:
                    response = api.v1.cancel_shipping(pack, test=test)
                except Exception, e:
                    self.pool.get('stock.packages').write(cr, uid, pack.id, {'ship_message': str(e)}, context=context)

                    print "Shipment Cancel response :", str(e)

                if  response.error:
                    error = True
                    self.pool.get('stock.packages').write(cr, uid, pack.id, {
                        'ship_message': response.error.description + (" (%s)" % response.error.Number)
                    }, context=context
                    )
                else:
                    self.pool.get('stock.packages').write(cr, uid, pack.id, {
                        'negotiated_rates' : 0.00, 'shipment_identific_no' :'', 'tracking_no': '',
                        'tracking_url': '', 'logo' : '', 'ship_message' : 'Shipment Cancelled'
                    }, context=context)

        if not error:
            self.write(cr, uid, do.id, {'ship_state':'draft', 'ship_message' : 'Shipment has been cancelled.'}, context=context)
        else:
            self.write(cr, uid, do.id, {'ship_message': 'Cancellation of some of shipment has failed, please check the status of packages.'}, context=context)

        return True


class stock_picking(_base_stock_picking, osv.osv):
    _inherit = "stock.picking"
    _columns = _base_stock_picking._columns
    _defaults = _base_stock_picking._defaults

stock_picking()


class stock_picking_out(_base_stock_picking, osv.osv):
    _inherit = "stock.picking.out"
    _columns = _base_stock_picking._columns
    _defaults = _base_stock_picking._defaults

stock_picking_out()


class stock_move(osv.osv):

    _inherit = "stock.move"

    def created(self, cr, uid, vals, context=None):
        if not context: context = {}
        package_obj = self.pool.get('stock.packages')
        pack_id = None
        package_ids = package_obj.search(cr, uid, [('pick_id', "=", vals.get('picking_id'))])
        if vals.get('picking_id'):
            rec = self.pool.get('stock.picking').browse(cr, uid, vals.get('picking_id'), context)
            if not context.get('copy'):
                if not package_ids:
                    pack_id = package_obj.create(cr, uid , {'package_type': rec.sale_id.usps_packaging_type.id, 'pick_id': vals.get('picking_id')})
        res = super(stock_move, self).create(cr, uid, vals, context)
        if not context.get('copy'):
            context.update({'copy': 1})
            default_vals = {}
            if pack_id:
                default_vals = {'package_id':pack_id, 'picking_id':[]}
            elif package_ids:
                default_vals = {'package_id':package_ids[0], 'picking_id':[]}
            self.copy(cr, uid, res, default_vals , context)
        return res

stock_move()


class stock(osv.osv_memory):

    _inherit = "stock.invoice.onshipping"

    def create_invoice(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        invoice_ids = []
        res = super(stock, self).create_invoice(cr, uid, ids, context=context)
        invoice_ids += res.values()
        picking_pool = self.pool.get('stock.picking.out')
        invoice_pool = self.pool.get('account.invoice')
        active_picking = picking_pool.browse(cr, uid, context.get('active_id', False), context=context)
        if active_picking:
            invoice_pool.write(cr, uid, invoice_ids, {'shipcharge':active_picking.shipcharge }, context=context)
        return res

stock()
