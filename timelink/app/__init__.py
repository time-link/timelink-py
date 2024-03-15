""" Structure of the app inspired by
https://levelup.gitconnected.com/structuring-fastapi-project-using-3-tier-design-pattern-4d2e88a55757


.. code-block:: bash

    .
    └── app/
        ├── backend/            # Backend functionality and configs
        |   ├── config.py           # Configuration settings
        │   └── session.py          # Database session manager
        ├── models/             # SQLAlchemy models
        │   ├── auth.py             # Authentication models
        |   ├── base.py             # Base classes, mixins
        |   └── ...                 # Other service models
        ├── routers/            # API routes
        |   ├── auth.py             # Authentication routers
        │   └── ...                 # Other service routers
        ├── schemas/            # Pydantic models
        |   ├── auth.py
        │   └── ...
        ├── services/           # Business logic
        |   ├── auth.py             # Generate and verify tokens
        |   ├── base.py             # Base classes, mixins
        │   └── ...
        ├── static/             # static files
        ├── templates/          # Jinja2 templates
        ├── cli.py              # Command-line utilities
        ├── const.py            # Constants
        ├── exc.py              # Exception handlers
        └── main.py             # Application runner

More good ideias in: https://medium.com/@ketansomvanshi007/structuring-a-fastapi-app-an-in-depth-guide-cdec3b8f4710
Official info: https://fastapi.tiangolo.com/tutorial/bigger-applications/

 """
