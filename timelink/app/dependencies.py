from fastapi import Request


# Dependency to get a connection to the database
def get_db(request: Request):

    db = webapp.db.session()

    try:
        yield db
    finally:
        db.close()

# dependency to get a connection to the kleio server
def get_kleio_server(request: Request):
    """Get a connection to the kleio server

    Uses timelink.kleio.kleio_server.KleioServer to get a connection to the kleio server.
    """

    return webapp.kleio_server
