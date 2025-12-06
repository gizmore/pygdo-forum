import os

from gdo.base.Application import Application
from gdo.base.ModuleLoader import ModuleLoader
from gdotest.TestUtil import GDOTestCase, reinstall_module


class ForumTest(GDOTestCase):

    async def asyncSetUp(self):
        await super().asyncSetUp()
        Application.init(os.path.dirname(__file__ + "/../../../../"))
        loader = ModuleLoader.instance()
        loader.load_modules_db(True)
        reinstall_module('forum')
        Application.init_cli()
        loader.init_modules(True, True)
        loader.init_cli()

    async def test_install(self):
        pass
