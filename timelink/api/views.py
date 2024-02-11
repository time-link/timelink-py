""" Handling views from sql Alchemy

    View utilities from https://github.com/sqlalchemy/sqlalchemy/wiki/Views
"""

import sqlalchemy as sa
from sqlalchemy.ext import compiler
from sqlalchemy.schema import DDLElement
from sqlalchemy.sql import table


class CreateView(DDLElement):
    """Create a View"""

    def __init__(self, name, selectable):
        self.name = name
        self.selectable = selectable


class DropView(DDLElement):
    """Drop a View"""

    def __init__(self, name):
        self.name = name


@compiler.compiles(CreateView)
def _create_view(element, compiler, **kw):
    return "CREATE VIEW %s AS %s" % (
        element.name,
        compiler.sql_compiler.process(element.selectable, literal_binds=True),
    )


@compiler.compiles(DropView)
def _drop_view(element, compiler, **kw):
    return "DROP VIEW %s" % (element.name)


def view_exists(ddl, target, connection, **kw):
    return ddl.name in sa.inspect(connection).get_view_names()


def view_doesnt_exist(ddl, target, connection, **kw):
    return not view_exists(ddl, target, connection, **kw)


def view(name, metadata, selectable):
    """Create a view with the given name from the given selectable.

    The view is created when the metadata is first bound to an engine.

    Example:

    .. code-block:: python

       stuff_view
            = view("stuff_view", metadata, sa.select(
                stuff.c.id.label("id"),
                stuff.c.data.label("data"),
                more_stuff.c.data.label("moredata"),
            )
                .select_from(stuff.join(more_stuff))
                .where(stuff.c.data.like(("%orange%"))),
            )

        with engine.connect() as conn:
        conn.execute(
            sa.select(stuff_view.c.data, stuff_view.c.moredata)
        ).all()

    """

    t = table(name)

    t._columns._populate_separate_keys(
        col._make_proxy(t) for col in selectable.selected_columns
    )

    sa.event.listen(
        metadata,
        "after_create",
        CreateView(name, selectable).execute_if(callable_=view_doesnt_exist),
    )
    sa.event.listen(
        metadata, "before_drop", DropView(name).execute_if(callable_=view_exists)
    )
    return t
