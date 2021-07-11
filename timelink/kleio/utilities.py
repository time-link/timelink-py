from dataclasses import dataclass, fields
import textwrap
from os import linesep as nl

print('__file__={0:<35} | __name__={1:<20} | __package__={2:<20}'.format(
    __file__, __name__, str(__package__)))


def get_metadata_key(*args):
    """
    get_metada_key(o,f,m,d)

    Get the value of metadata kley in a dataclass field.
    If f does not exist in o throws an error

    Parameters
    ----------

    o: dataclasses.dataclass
       A dataclass instance of class
    f: dataclasses.field
        A field in a dataclass
    m: str
        A key of the metadata dictionnary of a dataclass field.
    d: Any
        A default value if metadata key is absent or no metadata on the field


    """
    assert len(args) == 3 or len(args) == 4, \
        f'Expected 3 or 4 arguments, got {len(args)} '
    o = args[0]
    assert issubclass(type(o), dataclass), \
        f'First argument must be subclass of dataclass'

    f = args[1]
    assert f in o.__dataclass_fields__.keys(), f'No field {f} in {o}'

    k = args[2]
    if len(args) > 3:
        d = args[3]
    else:
        d = None

    dcf = o.__dataclass_fields__.get(f)
    md = dcf.get('metadata', None)
    if md is None:
        return d
    else:
        return md.get(k, d)


def kleio_escape(v):
    """
    Checks for Kleio special characterss and quotes string if needed.
    Convert argument to str as needed.

    """
    s = str(v)
    if any(i in s for i in '/;=$#%\n'):
        return '"' + s + '"'
    else:
        return s


def make_element(element, value, original=None, comment=None):
    if element == None:
        s = ''
    else:
        s = element + '='
    if value != None:
        s = s + kleio_escape(value)
        if original != None:
            s = s + '%' + kleio_escape(original)
        if comment != None:
            s = s + '%' + kleio_escape(comment)
    else:
        s = s + ''
    return s


def make_kgroup(group_name, Entity):
    s = ''
    return s


def quote_long_text(txt, initial_indent=' ' * 4, indent=' ' * 2):
    if len(txt) > 127 or len(txt.splitlines()) > 1:
        s = '"""' + nl
        for line in txt.splitlines():
            w = textwrap.fill(line, width=80, initial_indent=initial_indent)
            s = s + textwrap.indent(w, indent) + nl
        s = s + indent + '"""'
    else:
        s = kleio_escape(txt)
    return s


def format_obs(obs, initial_indent=' ' * 4, indent=' ' * 2):
    o = quote_long_text(obs)
    if len(o) > 127:
        s = nl + '   /obs=' + o
    else:
        s = '/obs=' + o + nl
    return s


def entity_to_kleio(entity):
    s = f'{entity.kgroup}$'
    positional = [f for f in fields(entity) if
                  f.metadata.get('positional', False) == True]
    optional = [f for f in fields(entity) if
                f.metadata.get('positional', False) == False]
    slash_needed = False
    for f in positional:
        # print(f'testing posicional {f.name}')
        if hasattr(entity, f.name):
            if f.name not in ['obs', 'kgroup', 'attributes', 'relations_in',
                              'relations_out', 'contains'] and getattr(entity,
                                                                       f.name) != None:
                if slash_needed:
                    s = s + '/'
                s = s + make_element(None, getattr(entity, f.name))
                slash_needed = True
    for f in optional:
        if hasattr(entity, f.name):
            # print(f'testing optional {f.name}')
            if f.name not in ['obs', 'kgroup', 'attributes', 'relations_in',
                              'relations_out', 'contains'] and getattr(entity,
                                                                       f.name) != None:
                if slash_needed:
                    s = s + '/'
                slash_needed = True
                n = f.metadata.get('kleio_name', f.name)
                s = s + make_element(n, getattr(entity, f.name))
    if entity.obs != None and entity.obs > ' ':
        s = s + format_obs(entity.obs)
    for a in entity.attributes:
        s = s + nl + '  ' + str(a)
    for r in entity.relations_out:
        s = s + nl + '  ' + str(r)
    return s + nl
