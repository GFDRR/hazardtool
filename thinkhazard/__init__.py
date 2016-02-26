import os
import ConfigParser

from pyramid.config import Configurator
from sqlalchemy import engine_from_config
from papyrus.renderers import GeoJSON

from .models import (
    DBSession,
    Base,
    )

from apscheduler.schedulers.background import BackgroundScheduler

# background scheduler to run print jobs asynchronously. by default a thread
# pool with 10 threads is used. to change the number of parallel print jobs,
# see https://apscheduler.readthedocs.org/en/latest/userguide.html#configuring-the-scheduler  # noqa
scheduler = BackgroundScheduler()
scheduler.start()


def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """

    load_local_settings(settings)

    engine = engine_from_config(settings, 'sqlalchemy.')
    DBSession.configure(bind=engine)
    Base.metadata.bind = engine

    config = Configurator(settings=settings)

    config.include('pyramid_jinja2')
    config.include('papyrus')

    config.add_static_view('static', 'static', cache_max_age=3600,
                           cachebust=True)
    config.add_static_view('lib', settings.get('node_modules'),
                           cache_max_age=86000, cachebust=True)

    config.add_route('index', '/')
    config.add_route('about', '/about')
    config.add_route('faq', '/faq')
    config.add_route('report',
                     '/report/{divisioncode:\d+}/{hazardtype:([A-Z]{2})}')
    config.add_route(
        'report_print',
        '/report/print/{divisioncode:\d+}/{hazardtype:([A-Z]{2})}')
    config.add_route('report_json',
                     '/report/{divisioncode:\d+}/{hazardtype:([A-Z]{2})}.json')
    config.add_route('create_pdf_report', '/report/create/{divisioncode:\d+}')
    config.add_route(
        'get_report_status', '/report/status/{divisioncode:\d+}/{id}.json')
    config.add_route('get_pdf_report', '/report/{divisioncode:\d+}/{id}.pdf')
    config.add_route('report_overview', '/report/{divisioncode:\d+}')
    config.add_route('report_overview_slash', '/report/{divisioncode:\d+}/')
    config.add_route('report_overview_json', '/report/{divisioncode:\d+}.json')
    config.add_route('administrativedivision', '/administrativedivision')
    config.add_route('pdf_cover', '/pdf_cover/{divisioncode:\d+}')

    config.add_route('admin_index', '/admin')

    config.add_route('admin_technical_rec', '/admin/technical_rec')
    config.add_route('admin_technical_rec_new', '/admin/technical_rec/new')
    config.add_route('admin_technical_rec_edit',
                     '/admin/technical_rec/{id:\d+}')

    config.add_route('admin_admindiv_hazardsets', '/admin/admindiv_hazardsets')
    config.add_route('admin_admindiv_hazardsets_hazardtype',
                     '/admin/admindiv_hazardsets/{hazardtype:([A-Z]{2})}')

    config.add_route('admin_climate_rec', '/admin/climate_rec')
    config.add_route('admin_climate_rec_hazardtype',
                     '/admin/climate_rec/{hazard_type:([A-Z]{2})}')
    config.add_route('admin_climate_rec_new',
                     '/admin/climate_rec/{hazard_type:([A-Z]{2})}/new')
    config.add_route('admin_climate_rec_edit', '/admin/climate_rec/{id:\d+}')

    config.add_route('admin_hazardcategory',
                     '/admin/{hazard_type:([A-Z]{2})}/'
                     '{hazard_level:([A-Z]{3})}')

    config.add_route('admin_hazardsets', '/admin/hazardsets')

    config.add_renderer('geojson', GeoJSON())

    init_pdf_archive_directory(settings.get('pdf_archive_path'))

    config.scan(ignore=['thinkhazard.tests'])
    return config.make_wsgi_app()


def load_local_settings(settings):
    """ Load local/user-specific settings.
    """
    local_settings_path = os.environ.get(
        'LOCAL_SETTINGS_PATH', settings.get('local_settings_path'))
    if local_settings_path and os.path.exists(local_settings_path):
        config = ConfigParser.ConfigParser()
        config.read(local_settings_path)
        settings.update(config.items('app:main'))


def init_pdf_archive_directory(pdf_archive_path):
    """Make sure that the directory used as report archive exists.
    """
    if not os.path.exists(pdf_archive_path):
        os.makedirs(pdf_archive_path)
