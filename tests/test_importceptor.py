# coding: utf-8

"""
test_importceptor
----------------------------------

Tests for `importceptor` module.
"""

from __future__ import unicode_literals

import unittest
import sys
from types import ModuleType

from importceptor import importceptor as ic


class TestImportceptor(unittest.TestCase):

    marker = object()

    def setUp(self):
        # Note: this is most probably not necessary, but let's make sure
        mods = ['mod1', 'mod2', 'mod3', 'mod4', 'textwrap']

        for mod in mods:
            sys.modules.pop(mod, None)

    def test_1(self):
        """
        Imports inside a simple module are intercepted properly

        """
        with ic.Importceptor({'os': self.marker}):
            import mod1

        assert mod1.os is self.marker

    def test_2(self):
        """
        If an import is not defined in the replacements, it will be imported in the normal way

        """
        with ic.Importceptor({}):
            import mod1

        import os
        assert mod1.os is os

    def test_3(self):
        """
        Modules directly under the decorator are actually imported and not intercepted.
        It would be a non-sense to intercept the very first imports

        """
        with ic.Importceptor({'mod2': self.marker}):
            import mod2

        assert mod2 is not self.marker
        assert isinstance(mod2, ModuleType)

    def test_4(self):
        """
        All the modules directly imported under the context manager are imported and not intercepted

        """
        with ic.Importceptor({'mod1': None, 'mod2': None, 'mod3': None}):
            import mod1
            import mod2
            import mod3

        for mod in [mod1, mod2, mod3]:
            assert isinstance(mod, ModuleType)

    def test_5(self):
        """
        from ... import ... syntax also works

        """
        with ic.Importceptor({'os': self.marker}):
            from mod1 import os

        assert os is self.marker

    def test_6(self):
        """
        If a module has "from mod import obj" statements, if the replacement has the attributes,
        those are properly returned

        """
        mock = ic.Bunch(path=object(), defpath=object())

        with ic.Importceptor({'os': mock}):
            import mod4

        assert mod4.path is mock.path
        assert mod4.defpath is mock.defpath

    def test_7(self):
        """
        If a module has "from mod import obj" statements, and the fully qualified python name of **all** the objects
        from `mod` to import is defined in the replacements mapping, then the object passed in the replacements
        will be used.

        """
        path = object()
        defpath = object()

        with ic.Importceptor({'os.path': path, 'os.defpath': defpath}):
            import mod4

        assert mod4.path is path
        assert mod4.defpath is defpath

    def test_8(self):
        """
        If a module has "from mod import obj" statements, and the FQPN is provided for some object, but not
        for some others, then the explicitly defined objects will be imported, and the rest will be
        read from the module (may or may not be real module depending on strict mode).

        """
        fake_os = ic.Bunch(path=object(), defpath=object())

        with ic.Importceptor({'os.path': self.marker, 'os': fake_os}):
            import mod4

        assert mod4.path is self.marker
        assert mod4.defpath is fake_os.defpath

    def test_9(self):
        """
        On strict mode, if a module is not passed, an exception will be raised

        """
        with self.assertRaises(KeyError):
            with ic.Importceptor({}, strict=True):
                import mod1

    def test_10(self):
        """
        If unload_modules is True, sys.modules is cleaned up before exiting the context manager

        """
        assert 'mod3' not in sys.modules
        assert 'textwrap' not in sys.modules

        with ic.Importceptor({'textwrap': None}):
            import mod3

            assert 'mod3' in sys.modules
            # Notice how completely intercepted modules are registered in sys.modules while in context manager
            assert 'textwrap' in sys.modules
            assert sys.modules['textwrap'] is None

        assert 'mod3' not in sys.modules
        assert 'textwrap' not in sys.modules

    def test_11(self):
        """
        If unload_modules is False, changes in sys.modules are persistent after exiting the context manager.
        This can actually lead to very messy results, but under certain conditions and used with care,
        it may be interesting.

        """
        assert 'mod3' not in sys.modules
        assert 'textwrap' not in sys.modules

        with ic.Importceptor({'textwrap': None}, unload_modules=False):
            import mod3

            assert 'mod3' in sys.modules
            assert 'textwrap' in sys.modules

        assert 'mod3' in sys.modules
        assert 'textwrap' in sys.modules

        # Let's clean up, just in case
        del sys.modules['mod3']
        del sys.modules['textwrap']

    def test_12(self):
        """
        Import statements "from ... import *" work the expected way

        """
        # __builtins__.__import__
        pass


if __name__ == '__main__':
    unittest.main()