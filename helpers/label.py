import os
import math
import pickle
import settings
from endicia import Endicia, Package
from shipping import Address

def get(stock_picking_out, pkg, service=None, config=None, test=None):
    '''Generate or retrieve the shipping label for the given package.'''

    label_dir = os.path.dirname(os.path.realpath(__file__)) + '/../labels' + '/%s' % stock_picking_out.id
    if not os.path.exists(label_dir):
        os.makedirs(label_dir)

    if config == None:
        config = settings.ENDICIA_CONFIG

    # Are we running in test mode? If so, we'll
    # need to use Endicia's sandbox servers.
    if stock_picking_out.logis_company and test == None:
        test = stock_picking_out.logis_company.test_mode

    api = Endicia(config, debug=(test if test != None else False))

    # Get the shipper and recipient addresses for this order.
    address_from = stock_picking_out.company_id.partner_id
    address_to = stock_picking_out.partner_id or ''

    # Create the Address objects that we'll later pass to our Endicia object.
    shipper = Address(address_from.name, address_from.street, address_from.city, address_from.state_id.code,
                      address_from.zip, address_from.country_id.name, address2=address_from.street2
    )
    recipient = Address(address_to.name, address_to.street, address_to.city, address_to.state_id.code,
                        address_to.zip, address_to.country_id.name, address2=address_to.street2
    )

    if service == None:
        service = stock_picking_out.usps_service_type

    weight = math.modf(pkg.weight)
    ounces = (weight[1] * 16) + round(weight[0] * 16, 2)

    package = Package(service, ounces, None, pkg.height, pkg.length, pkg.width)
    package.shape = package.calculate_container()

    label_filename = label_dir + "%s.lbl" % pkg.id

    if os.path.exists(label_filename):
        # Load the shipping label from storage.
        label_file = open(label_filename, 'r')
        label = pickle.load(label_file)
        label_file.close()

    else:
        # Get the shipping label and store it.
        label = api.label(package, shipper, recipient, image_format="EPL2")

        if hasattr(label, 'status') and label.status != 0: # Did we get an error?
            if label.status == 100002: # This is Endicia's catch-all, "our system broke" error code.
                raise Exception("Endicia server error: %s" % label.message)
            raise Exception(label.message)

        label_file = open(label_dir + "/%s.lbl" % pkg.id, 'w')
        pickle.dump(label, label_file)
        label_file.close()

    return label