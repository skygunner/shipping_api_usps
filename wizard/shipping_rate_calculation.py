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
from openerp.osv import orm, fields, osv
from tools.translate import _
import math
from ..helpers.endicia import Endicia, Package
from ..helpers.shipping import Address
from ..helpers import settings

class shipping_rate_wizard(orm.TransientModel):
    _inherit = 'shipping.rate.wizard'

    def _get_company_code(self, cr, user, context=None):
        res =  super(shipping_rate_wizard, self)._get_company_code(cr, user, context=context)
        res.append(('usps', 'USPS'))
        return list(set(res))

    def default_get(self, cr, uid, fields, context={}):
        res = super(shipping_rate_wizard, self).default_get(cr, uid, fields, context=context)
        if context.get('active_model',False) == 'sale.order':
            sale_id = context.get('active_id',False)
            if sale_id:
                sale = self.pool.get('sale.order').browse(cr, uid, sale_id, context=context)
                if 'usps_service_type' in fields and  sale.usps_service_type:
                    res['usps_service_type'] = sale.usps_service_type
                
                if 'usps_first_class_mail_type' in fields and  sale.usps_first_class_mail_type:
                    res['usps_first_class_mail_type'] = sale.usps_first_class_mail_type
                    
                if 'usps_container' in fields and  sale.usps_container:
                    res['usps_container'] = sale.usps_container
                    
                if 'usps_package_location' in fields and  sale.usps_package_location:
                    res['usps_package_location'] = sale.usps_package_location
                    
                if 'usps_size' in fields and  sale.usps_size:
                    res['usps_size'] = sale.usps_size
                    
                if 'usps_length' in fields and  sale.usps_length:
                    res['usps_length'] = sale.usps_length
                    
                if 'usps_width' in fields and  sale.usps_width:
                    res['usps_width'] = sale.usps_width
                    
                if 'usps_height' in fields and  sale.usps_height:
                    res['usps_height'] = sale.usps_height
                    
                if 'usps_girth' in fields and  sale.usps_girth:
                    res['usps_girth'] = sale.usps_girth
        return res

    def update_sale_order(self, cr, uid, ids, context={}):
        data = self.browse(cr, uid, ids[0], context=context)
        if not (data['rate_selection'] == 'rate_request' and data['ship_company_code']=='usps'):
            return super(shipping_rate_wizard, self).update_sale_order(cr, uid, ids, context)
        if context.get('active_model',False) == 'sale.order':
            ship_method_ids = self.pool.get('shipping.rate.config').search(
                cr, uid, [('name','=',data.usps_service_type)], context=context
            )
            ship_method_id = (ship_method_ids and ship_method_ids[0]) or None
            sale_id = context.get('active_id',False)
            sale_id and self.pool.get('sale.order').write(cr,uid,[sale_id],{'shipcharge':data.shipping_cost,
                                                                            'ship_method_id':ship_method_id,
                                                                            'sale_account_id':data.logis_company and data.logis_company.ship_account_id and data.logis_company.ship_account_id.id or False,
                                                                            'ship_company_code' :data.ship_company_code,
                                                                            'logis_company' : data.logis_company and data.logis_company.id or False,
                                                                            'usps_service_type' : data.usps_service_type,
                                                                            'usps_package_location' : data.usps_package_location,
                                                                            'usps_first_class_mail_type' : data.usps_first_class_mail_type ,
                                                                            'usps_container' : data.usps_container ,
                                                                            'usps_size' : data.usps_size ,
                                                                            'usps_length' : data.usps_length ,
                                                                            'usps_width' : data.usps_width ,
                                                                            'usps_height' : data.usps_height ,
                                                                            'usps_girth' : data.usps_girth ,
                                                                            'rate_selection' : data.rate_selection
                                                                            })
            self.pool.get('sale.order').button_dummy(cr, uid, [sale_id], context=context)
            return {'nodestroy':False,'type': 'ir.actions.act_window_close'}
        
        return True

    def get_rate(self, cr, uid, ids, context={}):
        """Calculates the cost of shipping for USPS."""

        data = self.browse(cr, uid, ids[0], context=context)

        if not ( data['rate_selection'] == 'rate_request' and data['ship_company_code']=='usps'):
            return super(shipping_rate_wizard, self).get_rate(cr, uid, ids, context)

        if context.get('active_model',False) == 'sale.order':
            # Are we running in test mode? If so, we'll
            # need to use Endicia's sandbox servers.
            test = data.logis_company.test_mode or False

            # Find the order we're calculating shipping costs on.
            sale_id = context.get('active_id',False)
            sale = self.pool.get('sale.order').browse(cr, uid, sale_id, context=context)

            # Get the shipper and recipient addresses for this order.
            address_from = sale.company_id.partner_id
            address_to = sale.partner_shipping_id or ''

            # Create the Address objects that we'll later pass to our Endicia object.
            shipper = Address(address_from.name, address_from.street, address_from.city, address_from.state_id.code,
                              address_from.zip, address_from.country_id.name, address2=address_from.street2
            )
            recipient = Address(address_to.name, address_to.street, address_to.city, address_to.state_id.code,
                                address_to.zip, address_to.country_id.name, address2=address_to.street2
            )

            # Get the package's weight in ounces.
            weight = math.modf(sale.total_weight_net)
            ounces = (weight[1] * 16) + round(weight[0] * 16, 2)

            # Create the Package we are going to send.
            package = Package(data.usps_service_type, str(ounces), data.usps_container, data.usps_length,
                              data.usps_width, data.usps_height
            )

            # Connect to the Endicia API.
            api = Endicia(settings.ENDICIA_CONFIG, debug=test)

            # Ask Endicia what the cost of shipping for this package is.
            response = {'status': -1}
            try:
                response = api.rate([package], shipper, recipient)
            except Exception, e:
                self.write(cr, uid, [data.id], {'status_message': str(e)}, context=context)

            # Extract the shipping cost from the response, if successful.
            if response['status'] == 0:
                ship_method_ids = self.pool.get('shipping.rate.config').search(
                cr, uid, [('name','=',data.usps_service_type)], context=context
                )
                ship_method_id = (ship_method_ids and ship_method_ids[0]) or None
                for item in response['info']:
                    if 'cost' in item:
                        self.write(cr, uid, [data.id], {
                                'status_message': '',
                                'shipping_cost': item['cost']
                        }, context=context)
                        sale.write({
                            'shipcharge': float(item['cost']) or 0.00,
                            'ship_method_id':ship_method_id,
                            'status_message': ''
                        })
                        return True

        # Get the view for this particular function.
        mod, modid = self.pool.get('ir.model.data').get_object_reference(
            cr, uid, 'shipping_api_usps', 'view_for_shipping_rate_wizard_usps'
        )

        return {
            'name':_("Get Rate"),
            'view_mode': 'form',
            'view_id': modid,
            'view_type': 'form',
            'res_model': 'shipping.rate.wizard',
            'type': 'ir.actions.act_window',
            'target':'new',
            'nodestroy': True,
            'domain': '[]',
            'res_id': ids[0],
            'context':context,
        }
    

    def _get_service_type_usps(self, cr, uid, context=None):
        return [(service, service) for service in Package.shipment_types]

    def _get_first_class_mail_type_usps(self, cr, uid, context=None):
        return [
            ('Letter', 'Letter'),
            ('Flat', 'Flat'),
            ('Parcel', 'Parcel'),
            ('Postcard', 'Postcard'),
        ]

    def _get_container_usps(self, cr, uid, context=None):
        return [(shape, shape) for shape in Package.shapes]

    def _get_size_usps(self, cr, uid, context=None):
        return [
            ('REGULAR', 'Regular'),
            ('LARGE', 'Large'),
         ]
    _columns= {
                    'ship_company_code': fields.selection(_get_company_code, 'Ship Company', method=True, size=64),
                    'usps_service_type' : fields.selection(_get_service_type_usps, 'Service Type', size=100),
                    'usps_package_location' : fields.selection([
                            ('Front Door','Front Door'),
                            ('Back Door','Back Door'),
                            ('Side Door','Side Door'),
                            ('Knock on Door/Ring Bell','Knock on Door/Ring Bell'),
                            ('Mail Room','Mail Room'),
                            ('Office','Office'),
                            ('Reception','Reception'),
                            ('In/At Mailbox','In/At Mailbox'),
                            ('Other','Other'),
                       ],'Package Location'),
                    'usps_first_class_mail_type' : fields.selection(_get_first_class_mail_type_usps, 'First Class Mail Type', size=50),
                    'usps_container' : fields.selection(_get_container_usps,'Container', size=100),
                    'usps_size' : fields.selection(_get_size_usps,'Size'),
                    'usps_length' : fields.float('Length'),
                    'usps_width' :  fields.float('Width'),
                    'usps_height' :  fields.float('Height'),
                    'usps_girth' :  fields.float('Girth'),
            }
shipping_rate_wizard()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: