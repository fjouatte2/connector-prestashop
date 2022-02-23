# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)


from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping

import mimetypes
import logging

from odoo import _

_logger = logging.getLogger(__name__)
try:
    from prestapyt import PrestaShopWebServiceError
except:
    _logger.debug('Cannot import from `prestapyt`')


class ProductImageMapper(Component):
    _name = 'prestashop.product.image.import.mapper'
    _inherit = 'prestashop.import.mapper'
    _apply_on = 'prestashop.product.image'

    _model_name = 'prestashop.product.image'

    direct = [
        # ('content', 'file_db_store'),
    ]

    @mapping
    def from_template(self, record):
        binder = self.binder_for('prestashop.product.template')
        template = binder.to_internal(record['id_product'], unwrap=True)
        name = '%s_%s' % (template.name, record['id_image'])
        return {'owner_id': template.id, 'name': name}

    @mapping
    def backend_id(self, record):
        return {'backend_id': self.backend_record.id}

    @mapping
    def extension(self, record):
        return {'extension': mimetypes.guess_extension(record['type'])}

    @mapping
    def image_url(self, record):
        return {'url': record['full_public_url']}

    @mapping
    def filename(self, record):
        return {'filename': '%s.jpg' % record['id_image']}

    @mapping
    def storage(self, record):
        return {'storage': 'url'}
        # return {'storage': 'db'}

    @mapping
    def owner_model(self, record):
        return {'owner_model': 'product.template'}


class ProductImageImporter(Component):
    _name = 'prestashop.product.image.importer'
    _inherit = 'prestashop.importer'
    _apply_on = 'prestashop.product.image'

    def _get_prestashop_data(self):
        """ Return the raw PrestaShop data for ``self.prestashop_id`` """
        adapter = self.component(
            usage='backend.adapter', model_name=self.model._name)
        return adapter.read(self.template_id, self.image_id)

    def run(self, template_id, image_id, **kwargs):
        add_new_image = True
        presta_product_template_model = self.env['prestashop.product.template']
        product_template_model = self.env['product.template']
        self.template_id = template_id
        self.image_id = image_id
        try:
            image_data = self._get_prestashop_data()
            image_content, image_id = image_data['content'], image_data['id_image']
            image_name = f'image_{image_id}'
            presta_template = presta_product_template_model.search([('prestashop_id', '=', int(template_id))])
            if presta_template and presta_template.odoo_id:
                if kwargs and kwargs.get('extra_image', False):
                    values = {}
                    for extra_image in presta_template.odoo_id.product_template_image_ids:
                        if extra_image.name == image_name:
                            add_new_image = False
                            break
                    if add_new_image:
                        if not values.get('product_template_image_ids', False):
                            values['product_template_image_ids'] = []
                        values['product_template_image_ids'].append(
                            (
                                0, 0, {
                                    'image_1920': image_content,
                                    'name': image_name
                                }
                            )
                        )
                        presta_template.odoo_id.write(values)
                else:
                    presta_template.odoo_id.write({'image_1920': image_content})

            # super(ProductImageImporter, self).run(image_id, **kwargs)
        except PrestaShopWebServiceError as error:
            binder = self.binder_for('prestashop.product.template')
            template = binder.to_internal(template_id, unwrap=True)
            if template:
                msg = _(
                    'Import of image id `%s` failed. '
                    'Error: `%s`'
                ) % (image_id, error.msg)
                """
                self.backend_record.add_checkpoint(
                    template,
                    message=msg)
                """
            else:
                msg = _(
                    'Import of image id `%s` of PrestaShop product '
                    'with id `%s` failed. '
                    'Error: `%s`'
                ) % (image_id, template_id, error.msg)
                # self.backend_record.add_checkpoint()
