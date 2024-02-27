"""
Pandas related utilities for Timelink
In progress. Originally developped for the FAUC1537-1919 project.
Now being integrated in the timelink-py package
"""
# Utilities for interacting with pandas
#
# IDEAS:
#    baptisms=function_to_df( function='n',
#                               act_tpe='bap',
#                               column_name='child', # instead of function
#                               person_info=True, # adds function_name, function_sex,
#                                                 #  columns
#                               dates_in=(after,before),
#                               name_like = name of person with function
#                               more_funcs=['pn','mn','ppn','mpn','pmn','mmn'],....)

from .name_to_df import pname_to_df  # noqa: F401
from .entities_with_attribute import entities_with_attribute  # noqa: F401
from .attribute_values import attribute_values  # noqa: F401
from .group_attributes import group_attributes  # noqa: F401
from .group_attributes import display_group_attributes  # noqa: F401
from .styles import category_palette, styler_row_colors  # noqa: F401
