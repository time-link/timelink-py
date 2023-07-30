from timelink.kleio.groups.kgroup import KGroup


class KKleio(KGroup):
    """KKleio(structure,prefix=,obs=,translations=,translator=)

    Kleio notation document. Represents a file in Kleio notation.

    Elements:
        structure: The path to a Kleio structure file (default gacto2.str)
        prefix: Prefix to be added to all ids generated from this file
        translations: number of times this file was translated
        translator: name of the translator to be used (currently not used)
        obs: observations

    TODO: Could keep a list of the name of the groups included, at all levels
    """

    _name = "kleio"
    _position = ["structure"]
    _also = ["prefix", "translations", "translator", "obs"]
    _part = ["source", "aregister"]
    _pom_class_id: str = "entity"

    def __init__(self, *args, **kwargs):
        KGroup._global_line = 1
        KGroup._global_sequence = 1
        super().__init__(*args, **kwargs)
