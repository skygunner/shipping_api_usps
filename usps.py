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

from openerp.osv import fields, osv

class usps_account_shipping(osv.osv):
    
    _name = "usps.account.shipping"

    _columns = {
        'name': fields.char('Name', size=64, required=True),
        'logistic_company_id': fields.many2one('logistic.company', 'Shipping Company', required=True),
        'company_id': fields.many2one('res.company', 'Client Company'),
        'account_id' : fields.char('Account ID', size=6, required=True),
        'partner_id' : fields.char('Partner ID', size=12, required=True),
        'passphrase' : fields.char('Passphrase', size=512, password=True, required=True),
        'active' : fields.boolean('Active'),
        'sandbox': fields.boolean('Sandbox mode'),
        #'tax_id_no': fields.char('Tax Identification Number', size=64 , select=1, help="Shipper's Tax Identification Number."),
    }
    _defaults = {
        'name': "USPS",
        'sandbox': True,
        'active': True
    }
usps_account_shipping()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
