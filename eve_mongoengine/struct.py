"""
    eve_mongoengine.struct
    ~~~~~~~~~~~~~~~~~~~~~~

    Datastructures for eve-mongoengine.

    :copyright: (c) 2014 by Stanislav Heller.
    :license: BSD, see LICENSE for more details.
"""


def _merge_dicts(d1, d2):
    """
    Helper function for merging dicts. This functino is called in
    :func:`Settings.update`.
    """
    for key, value in d2.items():
        if key in d1:
            if isinstance(d1[key], dict) and isinstance(value, dict):
                _merge_dicts(d1[key], value)
                continue
        d1[key] = value


class Settings(dict):
    """
    Special mergable dictionary for eve settings. Used as config keeper
    returned by method :func:`EveMongoengine.create_settings`.

    The difference between Settings object and default dict is that update()
    method in Settings does not overwrite the key when value is dictionary,
    but tries to merge inner dicts in an intelligent way.
    """

    def update(self, other):
        """Update method, which respects dictionaries recursively."""
        _merge_dicts(self, other)


__all__ = [Settings]
