# coding: utf-8

from __future__ import unicode_literals
from __future__ import print_function
from __future__ import absolute_import

import sys

try:
    import __builtin__ as builtins
except ImportError:
    import builtins

__all__ = ['Importceptor', 'Bunch']


class Bunch(object):
    """
    Class to generate objects on-the-fly from kwargs.

    """
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class Importceptor(object):
    """
    Context manager to intercept

    """
    def __init__(self, replacements, strict=False, verbose=False):
        """
        :param dict replacements: mapping module to object
        :param bool unload_modules: whether the imported module should be deleted from sys.modules. If deleted,
                                     next time imported it will be re-imported.
        :param bool strict: If True, if an import is not provided in replacements, an exception will be raised
                            if False, if not provided, the real module will be loaded instead.

        """
        self._replacements = replacements
        self._strict = strict
        self._verbose = verbose

        self._import_stack = []
        self._real_import = None
        self._pre_modules = None

    def __enter__(self):
        self._pre_modules = self._get_current_loaded_modules()

        self._real_import = builtins.__import__
        builtins.__import__ = self._import_handler

    def __exit__(self, exc_type, exc_val, exc_tb):
        builtins.__import__ = self._real_import

        # "Unload" modules.
        for mod in self._get_current_loaded_modules() - self._pre_modules:
            self._unload_module(mod)

    def _import_handler(self, mod_name, globals, locals, fromlist, level=-1):
        # Respect __future__ imports
        if mod_name == '__future__':
            return self._real_import(mod_name, globals, locals, fromlist, level)

        if self._verbose:
            print('..' * len(self._import_stack) + mod_name)

        # Imports directly under context manager
        if not self._import_stack:
            return self._process_first_level_import(mod_name, globals, locals, fromlist, level)

        return self._process_import_with_replacements(mod_name, globals, locals, fromlist, level)

    def _process_first_level_import(self, mod_name, globals, locals, fromlist, level):
        """
        Process import directly under the context manager.

        """
        # with self._create_depth_manager():
        self._import_stack.append(mod_name)

        try:
            return self._real_import(mod_name, globals, locals, fromlist, level)

        finally:
            self._import_stack.pop()

    def _process_import_with_replacements(self, mod_name, globals, locals, fromlist, level):
        self._import_stack.append(mod_name)

        try:

            if fromlist:
                return self._process_import_with_from_list(mod_name, globals, locals, fromlist, level)

            return self._get_replacement_for_module(mod_name, globals, locals, fromlist, level)

        finally:
            self._import_stack.pop()

    def _process_import_with_from_list(self, mod_name, globals, locals, fromlist, level):
        # If relative, make it absolute
        if level > 0:
            segments = self._import_stack[-1].split('.')
            mod_name = '.'.join(segments[:-level])

        # When there are "from mod_name import var_name[, var_name2]" statements, let's check if the
        # user passed each full names like: `mod_name.var_name`. Otherwise default to `mod_name` and fetch
        # the `var_name` attribute from there.
        names = [(var_name, mod_name + '.' + var_name) for var_name in fromlist]

        # Generate an object that has the attributes that are in fromlist
        # First those that were explicitly passed in the replacements
        available = [(name, full_name) for (name, full_name) in names if full_name in self._replacements]
        fake_mod = self._create_bunch(**{name: self._replacements[full_name] for name, full_name in available})

        # Then the not explicit. Delegate to the module to extract the attribute
        not_available = [name for (name, full_name) in names if full_name not in self._replacements]

        if not_available:
            # Pass level=-1, because if it was relative, we converted it into absolute.
            # NOTE [ik45 19.07.2015]: maybe pass level 0?
            module = self._get_replacement_for_module(mod_name, globals, locals, [], level=-1)
            fake_mod.__dict__.update((name, getattr(module, name)) for name in not_available)

        return fake_mod

    def _get_replacement_for_module(self, mod_name, globals, locals, fromlist, level):
        """
        Look up a replacement for the module.

        If on strict mode, and mod not found, KeyError will be raised. If not on strict mode, the real module
        will be sought.

        """
        try:
            return self._replacements[mod_name]

        except KeyError:
            if self._strict:
                raise

            return self._real_import(mod_name, globals, locals, fromlist, level)

    _create_bunch = Bunch

    @staticmethod
    def _unload_module(mod_name):
        """
        Removes the module from sys.modules. This does not guarantee at all that the tree
        of imported modules gets unloaded, but at least next time the module is imported,
        it will be reloaded, avoiding possible strange side effects due to the replacements.

        If the module is not loaded, no error will be raised

        """
        sys.modules.pop(mod_name, None)

    @staticmethod
    def _get_current_loaded_modules():
        return set(sys.modules.keys())
