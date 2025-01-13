# Extensions to Alembic's migration environment
# To support handling of views
# JRC: Currently unused. This is the receipt for handling views in the database
#      allowing to downgrade to previous versions of views. Also applies to
#      database procedures and functions.
#      Currently we just recreate the views at each opening of database after migration
#      so we dont need to downgrade views.
# https://alembic.sqlalchemy.org/en/latest/cookbook.html#supporting-views
from alembic.operations import MigrateOperation, Operations


class ReplaceableObject:
    """A class for creating replaceable database objects.

    "We first need to create a simple object that represents the
    “CREATE View” / “DROP View” aspect of what it is we’re building.
    We can just as well put strings inside dictionaries,
    which would also work. Nevertheless, I will illustrate how
    this object helps organize the code below."

    """

    def __init__(self, name, sqltext):
        self.name = name
        self.sqltext = sqltext


class ReversibleOp(MigrateOperation):
    def __init__(self, target):
        self.target = target

    @classmethod
    def invoke_for_target(cls, operations, target):
        op = cls(target)
        return operations.invoke(op)

    def reverse(self):
        raise NotImplementedError()

    @classmethod
    def _get_object_from_version(cls, operations, ident):
        version, objname = ident.split(".")
        # operations.get_context() method locates the version of file
        # which helps in updating the view
        module = operations.get_context().script.get_revision(version).module
        obj = getattr(module, objname)
        return obj

    # The replace operation below will always run a DROP then a CREATE.
    # The arguments replaces and replace_with accept a dot-separated string,
    # which refers to a revision number and an object name, such as "abc.popular_author"
    @classmethod
    def replace(cls, operations, target, replaces=None, replace_with=None):
        if replaces:
            old_obj = cls._get_object_from_version(operations, replaces)
            drop_old = cls(old_obj).reverse()
            create_new = cls(target)
        elif replace_with:
            old_obj = cls._get_object_from_version(operations, replace_with)
            drop_old = cls(target).reverse()
            create_new = cls(old_obj)
        else:
            raise TypeError("replaces or replace_with is required")

        operations.invoke(drop_old)
        operations.invoke(create_new)


@Operations.register_operation("create_view", "invoke_for_target")
@Operations.register_operation("replace_view", "replace")
class CreateViewOp(ReversibleOp):
    def reverse(self):
        return DropViewOp(self.target)


@Operations.register_operation("drop_view", "invoke_for_target")
class DropViewOp(ReversibleOp):
    def reverse(self):
        return CreateViewOp(self.target)


@Operations.implementation_for(CreateViewOp)
def create_view(operations, operation):
    operations.execute(
        "CREATE VIEW %s AS %s" % (operation.target.name, operation.target.sqltext)
    )


@Operations.implementation_for(DropViewOp)
def drop_view(operations, operation):
    operations.execute("DROP VIEW %s" % operation.target.name)
