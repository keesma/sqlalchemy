# Copyright (C) 2005-2020 the SQLAlchemy authors and contributors
# <see AUTHORS file>
#
# This module is part of SQLAlchemy and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

from ... import util
from ...sql import coercions
from ...sql import roles
from ...sql.base import _generative
from ...sql.dml import Insert as StandardInsert
from ...sql.elements import ClauseElement
from ...sql.expression import alias
from ...util.langhelpers import public_factory


__all__ = ("Insert", "insert")


class Insert(StandardInsert):
    """SQLite-specific implementation of INSERT.

    Adds methods for SQLite-specific syntaxes such as ON CONFLICT.

    The :class:`_sqlite.Insert` object is created using the
    :func:`sqlalchemy.dialects.sqlite.insert` function.

    .. versionadded:: 1.4

    .. seealso::

        :ref:`sqlite_on_conflict_insert`

    """

    stringify_dialect = "sqlite"

    @util.memoized_property
    def excluded(self):
        """Provide the ``excluded`` namespace for an ON CONFLICT statement

        SQLite's ON CONFLICT clause allows reference to the row that would
        be inserted, known as ``excluded``.  This attribute provides
        all columns in this row to be referenceable.

        """
        return alias(self.table, name="excluded").columns

    @_generative
    def on_conflict_do_update(
        self,
        index_elements=None,
        index_where=None,
        set_=None,
        where=None,
    ):
        r"""
        Specifies a DO UPDATE SET action for ON CONFLICT clause.

        :param index_elements:
         A sequence consisting of string column names, :class:`_schema.Column`
         objects, or other column expression objects that will be used
         to infer a target index or unique constraint.

        :param index_where:
         Additional WHERE criterion that can be used to infer a
         conditional target index.

        :param set\_:
         A dictionary or other mapping object
         where the keys are either names of columns in the target table,
         or :class:`_schema.Column` objects or other ORM-mapped columns
         matching that of the target table, and expressions or literals
         as values, specifying the ``SET`` actions to take.

         .. versionadded:: 1.4 The
            :paramref:`_sqlite.Insert.on_conflict_do_update.set_`
            parameter supports :class:`_schema.Column` objects from the target
            :class:`_schema.Table` as keys.

         .. warning:: This dictionary does **not** take into account
            Python-specified default UPDATE values or generation functions,
            e.g. those specified using :paramref:`_schema.Column.onupdate`.
            These values will not be exercised for an ON CONFLICT style of
            UPDATE, unless they are manually specified in the
            :paramref:`.Insert.on_conflict_do_update.set_` dictionary.

        :param where:
         Optional argument. If present, can be a literal SQL
         string or an acceptable expression for a ``WHERE`` clause
         that restricts the rows affected by ``DO UPDATE SET``. Rows
         not meeting the ``WHERE`` condition will not be updated
         (effectively a ``DO NOTHING`` for those rows).

        """

        self._post_values_clause = OnConflictDoUpdate(
            index_elements, index_where, set_, where
        )

    @_generative
    def on_conflict_do_nothing(self, index_elements=None, index_where=None):
        """
        Specifies a DO NOTHING action for ON CONFLICT clause.

        :param index_elements:
         A sequence consisting of string column names, :class:`_schema.Column`
         objects, or other column expression objects that will be used
         to infer a target index or unique constraint.

        :param index_where:
         Additional WHERE criterion that can be used to infer a
         conditional target index.

        """

        self._post_values_clause = OnConflictDoNothing(
            index_elements, index_where
        )


insert = public_factory(
    Insert, ".dialects.sqlite.insert", ".dialects.sqlite.Insert"
)


class OnConflictClause(ClauseElement):
    stringify_dialect = "sqlite"

    def __init__(self, index_elements=None, index_where=None):

        if index_elements is not None:
            self.constraint_target = None
            self.inferred_target_elements = index_elements
            self.inferred_target_whereclause = index_where
        else:
            self.constraint_target = (
                self.inferred_target_elements
            ) = self.inferred_target_whereclause = None


class OnConflictDoNothing(OnConflictClause):
    __visit_name__ = "on_conflict_do_nothing"


class OnConflictDoUpdate(OnConflictClause):
    __visit_name__ = "on_conflict_do_update"

    def __init__(
        self,
        index_elements=None,
        index_where=None,
        set_=None,
        where=None,
    ):
        super(OnConflictDoUpdate, self).__init__(
            index_elements=index_elements,
            index_where=index_where,
        )

        if not isinstance(set_, dict) or not set_:
            raise ValueError("set parameter must be a non-empty dictionary")
        self.update_values_to_set = [
            (coercions.expect(roles.DMLColumnRole, key), value)
            for key, value in set_.items()
        ]
        self.update_whereclause = where
